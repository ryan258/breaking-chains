"""Thin loopback-only Streamlit adapter over the shared application core."""

from pathlib import Path
from uuid import uuid4

import streamlit as st

from forge.application.budgets import live_run_confirmation_prompt
from forge.application.decisions import (
    ChoiceLetter,
    DecisionKind,
    DecisionPrompt,
    depth_mode_prompt,
    pause_resume_prompt,
    submit_decision,
)
from forge.application.runtime import budget_policy, repository
from forge.application.source_ingestion import SourceImportError
from forge.config import ConfigurationError, ForgeSettings, load_settings
from forge.domain.investigation import DepthMode
from forge.persistence.metadata import InvestigationRecord
from forge.ui.services import (
    cache_uploaded_source,
    confirm_and_resume_live,
    load_quarantined_model_response,
    resume_investigation,
    run,
    start_investigation,
    submit_record_decision,
)
from forge.ui.view_models import completed_stage_labels, review_sections

st.set_page_config(page_title="First-Principles Forge", page_icon="⚒", layout="wide")
st.html(Path(__file__).parent / "assets/style.css")


def _settings() -> ForgeSettings:
    try:
        return load_settings()
    except ConfigurationError as error:
        st.error(str(error))
        st.stop()


def _render_start(settings: ForgeSettings) -> None:
    st.header("Start an investigation")
    saved_records = repository(settings).list_records()
    prior_labels = {"No prior investigation": None}
    prior_labels.update({f"{record.seed} — {record.id}": record for record in saved_records})
    with st.form("start_form"):
        seed = st.text_area(
            "Investigation seed",
            key="seed",
            help="A short question, observation, or problem to investigate.",
        )
        source = st.file_uploader(
            "Optional local text or Markdown source",
            type=["txt", "md", "markdown"],
            help=(
                "Up to 1 MB. The file remains local unless a later A-E consent question "
                "is approved."
            ),
        )
        prior_label = st.selectbox(
            "Optional prior investigation seed",
            prior_labels,
            help="Start a traceable follow-up from a saved canonical record.",
        )
        prepared = st.form_submit_button("Prepare investigation", key="prepare_start")
    if not prepared:
        return
    if not seed.strip():
        st.error("Enter an investigation seed before continuing.")
        return
    try:
        source_reference = cache_uploaded_source(settings, source)
    except SourceImportError as error:
        st.error(str(error))
        return
    investigation_id = f"inv_{uuid4().hex}"
    prior_record = prior_labels[prior_label]
    if prior_record is not None:
        seed = f"{seed.strip()}\n\nPrior investigation {prior_record.id}: {prior_record.seed}" + (
            f"\nPrior focus: {prior_record.selected_focus}" if prior_record.selected_focus else ""
        )
    st.session_state.pending_start = {
        "id": investigation_id,
        "seed": seed.strip(),
        "prior_investigation_ids": (prior_record.id,) if prior_record is not None else (),
        "depth": None,
        "source_reference": source_reference,
        "prompt": depth_mode_prompt(default_depth=settings.default_depth.value),
    }
    st.rerun()


def _decision_buttons(prompt: DecisionPrompt) -> tuple[ChoiceLetter | None, str | None]:
    st.markdown(prompt.question)
    columns = st.columns(5)
    selected = None
    for column, option in zip(columns, prompt.options, strict=True):
        label = f"{option.letter.value} — {option.label}"
        if column.button(
            label,
            key=f"decision_{option.letter.value}",
            help=option.description,
            use_container_width=True,
        ):
            selected = option.letter
    if selected is ChoiceLetter.E:
        st.session_state.custom_prompt_id = prompt.id
        st.rerun()
    custom = None
    if st.session_state.get("custom_prompt_id") == prompt.id:
        custom = st.text_area("Custom answer", key="custom_answer")
        if not st.button("Submit custom answer", key="submit_custom"):
            return None, None
        selected = ChoiceLetter.E
    return selected, custom


def _handle_pending_start(settings: ForgeSettings) -> None:
    pending = st.session_state.pending_start
    prompt = pending["prompt"]
    choice, custom = _decision_buttons(prompt)
    if choice is None:
        return
    if prompt.kind is DecisionKind.MODE:
        selected_depth = {
            ChoiceLetter.A: DepthMode.QUICK,
            ChoiceLetter.B: DepthMode.STANDARD,
            ChoiceLetter.C: DepthMode.DEEP,
        }.get(choice)
        if choice is ChoiceLetter.E and custom is not None:
            try:
                selected_depth = DepthMode(custom.split(maxsplit=1)[0].lower())
            except ValueError:
                st.session_state.notice = (
                    "Custom mode must begin with Quick, Standard, or Deep; nothing started."
                )
        if selected_depth is None:
            st.session_state.setdefault("notice", "No investigation was started.")
            del st.session_state.pending_start
            st.session_state.pop("custom_prompt_id", None)
            st.rerun()
        pending["depth"] = selected_depth
        pending["mode_attempt"] = submit_decision(prompt, choice, custom_answer=custom)
        pending["prompt"] = live_run_confirmation_prompt(
            investigation_id=pending["id"],
            depth=selected_depth,
            budget=budget_policy(settings).for_depth(selected_depth),
            source_attached=pending["source_reference"] is not None,
        )
        st.session_state.pop("custom_prompt_id", None)
        st.rerun()
    if choice in {ChoiceLetter.B, ChoiceLetter.C, ChoiceLetter.E}:
        message = custom or "No investigation was started and no provider call was made."
        st.session_state.notice = message
        del st.session_state.pending_start
        st.session_state.pop("custom_prompt_id", None)
        st.rerun()
    view = run(
        start_investigation(
            settings,
            investigation_id=pending["id"],
            seed=pending["seed"],
            depth=pending["depth"],
            source_reference=pending["source_reference"],
            prior_investigation_ids=pending["prior_investigation_ids"],
            preflight_decisions=(pending["mode_attempt"],),
            prompt=prompt,
            choice=choice,
        )
    )
    st.session_state.active_investigation_id = view.record.id
    if choice is ChoiceLetter.A:
        st.session_state.live_run_approved_id = view.record.id
    del st.session_state.pending_start
    st.session_state.pop("custom_prompt_id", None)
    st.rerun()


def _render_saved_records(settings: ForgeSettings) -> None:
    records = repository(settings).list_records()
    st.header("Saved investigations")
    if not records:
        st.caption("No saved investigations yet.")
        return
    labels = {f"{record.seed} — {record.id}": record for record in records}
    selected_label = st.selectbox("Saved record", labels, key="saved_record")
    if st.button("Resume selected investigation", key="resume_saved"):
        record = labels[selected_label]
        st.session_state.pending_resume_id = record.id
        st.rerun()


def _handle_pending_resume(settings: ForgeSettings) -> None:
    record = repository(settings).load(st.session_state.pending_resume_id)
    prompt = (
        live_run_confirmation_prompt(
            investigation_id=record.id,
            depth=record.workflow.depth,
            budget=budget_policy(settings).for_depth(record.workflow.depth),
            source_attached=bool(record.source_references),
            resuming=True,
        )
        if record.live_execution_approved
        else pause_resume_prompt(investigation_id=record.id)
    )
    choice, custom = _decision_buttons(prompt)
    if choice is None:
        return
    if choice is not ChoiceLetter.A:
        st.session_state.notice = (
            custom or "The investigation remains saved and no provider call was made."
        )
        del st.session_state.pending_resume_id
        st.session_state.pop("custom_prompt_id", None)
        st.rerun()
    view = run(
        confirm_and_resume_live(settings, record, prompt)
        if record.live_execution_approved
        else resume_investigation(settings, record)
    )
    st.session_state.active_investigation_id = view.record.id
    st.session_state.live_run_approved_id = view.record.id
    del st.session_state.pending_resume_id
    st.session_state.pop("custom_prompt_id", None)
    st.rerun()


def _render_record(settings: ForgeSettings, record: InvestigationRecord) -> None:
    st.header("Current investigation")
    st.markdown(
        f"**Stage:** `{record.workflow.stage.value}` · **Status:** "
        f"`{record.workflow.status.value}` · **Mode:** `{record.workflow.depth.value}`"
    )
    completed = completed_stage_labels(record)
    st.caption("Completed stages: " + " → ".join(completed))
    with st.status(
        "Completed" if record.workflow.stage.value == "completed" else "Investigation saved",
        state="complete" if record.workflow.stage.value == "completed" else "running",
    ):
        st.write("Every finished stage is stored in the canonical Markdown record.")

    for section in review_sections(record):
        with st.expander(f"{section.title} ({len(section.lines)})"):
            if section.lines:
                for line in section.lines:
                    st.markdown(f"- {line}")
            else:
                st.caption("Nothing recorded yet.")

    record_path = repository(settings).root / f"{record.id}.md"
    if record_path.is_file():
        st.download_button(
            "Open saved Markdown record",
            data=record_path.read_bytes(),
            file_name=record_path.name,
            mime="text/markdown",
        )

    if record.pending_decision is None:
        return
    if (
        record.pending_decision.kind is DecisionKind.RECOVERY
        and record.model_receipts
        and (
            quarantined := load_quarantined_model_response(
                output_dir=settings.output_dir,
                investigation_id=record.id,
                receipt=record.model_receipts[-1],
            )
        )
    ):
        st.subheader("Quarantined model response")
        st.markdown(
            "This is exactly what the model returned. Forge did **not** add it to the "
            "canonical record because it failed the role contract. It remains visible here "
            "so you can inspect it and decide what to do."
        )
        st.code(quarantined, language="json", wrap_lines=True)
    choice, custom = _decision_buttons(record.pending_decision)
    if choice is None:
        return
    view = run(submit_record_decision(settings, record, choice, custom))
    if view.error:
        st.session_state.notice = view.error
    st.session_state.pop("custom_prompt_id", None)
    st.rerun()


def main() -> None:
    settings = _settings()
    st.title("First-Principles Forge")
    st.caption("A local, traceable workspace for questions that deserve careful reasoning.")
    if notice := st.session_state.pop("notice", None):
        st.info(notice)

    if "pending_start" in st.session_state:
        _handle_pending_start(settings)
        return
    if "pending_resume_id" in st.session_state:
        _handle_pending_resume(settings)
        return

    active_id = st.session_state.get("active_investigation_id")
    if active_id and repository(settings).exists(active_id):
        _render_record(settings, repository(settings).load(active_id))
        if st.button("Return to start and saved records", key="return_home"):
            st.session_state.pop("active_investigation_id", None)
            st.rerun()
        return

    left, right = st.columns([3, 2])
    with left:
        _render_start(settings)
    with right:
        _render_saved_records(settings)


main()
