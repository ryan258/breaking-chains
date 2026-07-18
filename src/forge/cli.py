"""Typer command adapter over the shared application core."""

import asyncio
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from rich.console import Console
from rich.markdown import Markdown

from forge.application.budgets import live_run_confirmation_prompt
from forge.application.decisions import (
    ChoiceLetter,
    DecisionAttempt,
    DecisionPrompt,
    depth_mode_prompt,
    pause_resume_prompt,
    submit_decision,
)
from forge.application.orchestrator import InvestigationOrchestrator, OrchestrationView
from forge.application.runtime import (
    budget_policy,
    filter_records,
    orchestrator_context,
    projection,
    repository,
)
from forge.application.source_ingestion import SourceImportError, import_local_source
from forge.config import ConfigurationError, ForgeSettings, load_settings
from forge.domain.investigation import DepthMode, WorkflowStatus
from forge.persistence.markdown import RecordFormatError, render_record

app = typer.Typer(add_completion=False, help="First-principles discovery forge.")


def _settings() -> ForgeSettings:
    try:
        return load_settings()
    except ConfigurationError as error:
        typer.echo(str(error))
        raise typer.Exit(1) from None


def _present_decision(prompt: DecisionPrompt) -> DecisionAttempt:
    while True:
        typer.echo(f"\n{prompt.question}")
        for option in prompt.options:
            marker = " (recommended)" if option.is_recommended else ""
            typer.echo(f"  {option.letter.value}. {option.label}{marker}")
        raw_choice = typer.prompt("Choose A-E")
        custom_answer = None
        if raw_choice.strip().upper() == ChoiceLetter.E:
            custom_answer = typer.prompt("Custom answer")
        attempt = submit_decision(prompt, raw_choice, custom_answer=custom_answer)
        if attempt.error is None:
            return attempt
        typer.echo(attempt.error)


async def _drive(orchestrator: InvestigationOrchestrator, view: OrchestrationView) -> None:
    """Present each pending A-E question until the investigation stops."""

    while view.prompt is not None:
        if view.error is not None:
            typer.echo(view.error)
        prompt = view.prompt
        attempt = _present_decision(prompt)
        assert attempt.selection is not None
        view = await orchestrator.submit_decision(
            view.record.id,
            prompt_id=prompt.id,
            raw_choice=attempt.selection.letter,
            custom_answer=attempt.custom_answer,
        )

    if view.error is not None:
        typer.echo(view.error)

    record = view.record
    typer.echo(f"\n{record.id}: {record.workflow.stage.value} ({record.workflow.status.value})")
    if record.workflow.status is WorkflowStatus.PAUSED:
        typer.echo(f"Resume later with: forge resume {record.id}")


async def _start_and_drive(
    settings: ForgeSettings,
    *,
    live: bool,
    investigation_id: str,
    seed: str,
    depth: DepthMode,
    source_reference,
    prior_investigation_ids: tuple[str, ...],
    preflight_decisions: tuple[DecisionAttempt, ...],
    live_confirmation: DecisionAttempt,
) -> None:
    async with orchestrator_context(settings, live=live) as orchestrator:
        view = await orchestrator.start(
            investigation_id=investigation_id,
            seed=seed,
            depth=depth,
            at=datetime.now(UTC),
            source_reference=source_reference,
            prior_investigation_ids=prior_investigation_ids,
            preflight_decisions=preflight_decisions,
            live_confirmation=live_confirmation,
        )
        await _drive(orchestrator, view)


async def _resume_and_drive(
    settings: ForgeSettings,
    *,
    live: bool,
    investigation_id: str,
    live_confirmation: DecisionAttempt | None = None,
) -> None:
    async with orchestrator_context(settings, live=live) as orchestrator:
        if live_confirmation is not None:
            await orchestrator.record_live_confirmation(investigation_id, live_confirmation)
        view = await orchestrator.resume(investigation_id)
        await _drive(orchestrator, view)


@app.command()
def investigate(
    seed: Annotated[str, typer.Option("--seed", prompt="Investigation seed")],
    mode: Annotated[DepthMode | None, typer.Option("--mode")] = None,
    source: Annotated[Path | None, typer.Option("--source")] = None,
    prior: Annotated[str | None, typer.Option("--prior")] = None,
) -> None:
    """Start a new investigation from a short seed."""

    settings = _settings()
    prior_ids: tuple[str, ...] = ()
    if prior is not None:
        prior_record = repository(settings).load(prior)
        prior_ids = (prior_record.id,)
        seed = f"{seed}\n\nPrior investigation {prior_record.id}: {prior_record.seed}" + (
            f"\nPrior focus: {prior_record.selected_focus}" if prior_record.selected_focus else ""
        )
    imported_source = None
    if source is not None:
        try:
            imported_source = import_local_source(source)
        except SourceImportError as error:
            typer.echo(str(error))
            raise typer.Exit(2) from None
        typer.echo(
            f"Local source: {imported_source.reference.path} "
            f"({len(imported_source.content)} characters)."
        )
        typer.echo("Its UTF-8 text will leave this machine only after explicit approval.")
    depth = mode
    mode_attempt = None
    if depth is None:
        mode_attempt = _present_decision(
            depth_mode_prompt(default_depth=settings.default_depth.value)
        )
        assert mode_attempt.selection is not None
        if mode_attempt.selection.letter is ChoiceLetter.D:
            typer.echo("No investigation was started.")
            return
        selected_mode = {
            ChoiceLetter.A: DepthMode.QUICK,
            ChoiceLetter.B: DepthMode.STANDARD,
            ChoiceLetter.C: DepthMode.DEEP,
        }.get(mode_attempt.selection.letter)
        if selected_mode is None and mode_attempt.custom_answer is not None:
            requested = mode_attempt.custom_answer.split(maxsplit=1)[0].lower()
            try:
                selected_mode = DepthMode(requested)
            except ValueError:
                typer.echo("Custom mode must begin with Quick, Standard, or Deep; nothing started.")
                return
        depth = selected_mode
    assert depth is not None
    investigation_id = f"inv_{uuid4().hex}"
    budget = budget_policy(settings).for_depth(depth)
    confirmation_prompt = live_run_confirmation_prompt(
        investigation_id=investigation_id,
        depth=depth,
        budget=budget,
        source_attached=imported_source is not None,
    )
    confirmation = _present_decision(confirmation_prompt)
    assert confirmation.selection is not None
    if confirmation.selection.letter in {ChoiceLetter.B, ChoiceLetter.C, ChoiceLetter.E}:
        typer.echo("No investigation was started and no provider call was made.")
        return
    live = confirmation.selection.letter is ChoiceLetter.A
    typer.echo(f"Starting {investigation_id} in {depth.value} mode.")
    asyncio.run(
        _start_and_drive(
            settings,
            live=live,
            investigation_id=investigation_id,
            seed=seed,
            depth=depth,
            source_reference=(imported_source.reference if imported_source is not None else None),
            prior_investigation_ids=prior_ids,
            preflight_decisions=(mode_attempt,) if mode_attempt is not None else (),
            live_confirmation=confirmation,
        )
    )


@app.command()
def resume(investigation_id: str) -> None:
    """Resume a paused investigation from its last saved state."""

    settings = _settings()
    record = repository(settings).load(investigation_id)
    confirmation = None
    if record.live_execution_approved:
        confirmation_prompt = live_run_confirmation_prompt(
            investigation_id=record.id,
            depth=record.workflow.depth,
            budget=budget_policy(settings).for_depth(record.workflow.depth),
            source_attached=bool(record.source_references),
            resuming=True,
        )
        confirmation = _present_decision(confirmation_prompt)
        assert confirmation.selection is not None
        if confirmation.selection.letter is not ChoiceLetter.A:
            typer.echo("The investigation remains saved and no provider call was made.")
            return
    else:
        resume_attempt = _present_decision(pause_resume_prompt(investigation_id=record.id))
        assert resume_attempt.selection is not None
        if resume_attempt.selection.letter is not ChoiceLetter.A:
            typer.echo("The investigation remains saved.")
            return
    asyncio.run(
        _resume_and_drive(
            settings,
            live=record.live_execution_approved,
            investigation_id=investigation_id,
            live_confirmation=confirmation,
        )
    )


@app.command("list")
def list_investigations(
    status: Annotated[WorkflowStatus | None, typer.Option("--status")] = None,
) -> None:
    """List saved investigations from the canonical Markdown records."""

    settings = _settings()
    records = repository(settings).list_records()
    shown = 0
    for record in records:
        workflow = record.workflow
        if status is not None and workflow.status is not status:
            continue
        shown += 1
        typer.echo(
            f"{record.id}  {workflow.depth.value}  {workflow.stage.value}  "
            f"{workflow.status.value}  {record.seed[:60]}"
        )
    if shown == 0:
        typer.echo("No investigations found.")


@app.command()
def search(
    query: str,
    category: Annotated[str | None, typer.Option("--category")] = None,
) -> None:
    """Find saved investigations by seed, focus, or indexed statement text."""

    settings = _settings()
    if not query.strip():
        typer.echo("Enter a search phrase.")
        raise typer.Exit(2)
    records = filter_records(settings, repository(settings).list_records(), query)
    for record in records:
        workflow = record.workflow
        typer.echo(
            f"{record.id}  {workflow.depth.value}  {workflow.stage.value}  "
            f"{workflow.status.value}  {record.seed[:60]}"
        )
    try:
        hits = projection(settings).search(query.strip(), category=category)
    except ValueError as error:
        typer.echo(str(error))
        raise typer.Exit(2) from None
    except sqlite3.OperationalError:
        hits = ()
    for hit in hits:
        subtype = f"/{hit.subtype}" if hit.subtype else ""
        typer.echo(f"{hit.investigation_id}  {hit.category}{subtype}  {hit.statement[:70]}")
    if not records and not hits:
        typer.echo("No matches. If indexed content seems missing, run: forge rebuild-index")


@app.command()
def show(investigation_id: str) -> None:
    """Render a saved investigation's report in the terminal."""

    settings = _settings()
    try:
        record = repository(settings).load(investigation_id)
    except (FileNotFoundError, RecordFormatError):
        typer.echo(f"No saved investigation named {investigation_id}.")
        raise typer.Exit(1) from None
    text = render_record(record)
    report = text[: text.index("## Machine-readable record")].rstrip()
    Console().print(Markdown(report))


@app.command("rebuild-index")
def rebuild_index() -> None:
    """Rebuild the disposable SQLite projection from canonical Markdown."""

    settings = _settings()
    records = repository(settings).list_records()
    projection(settings).rebuild(records)
    typer.echo(f"Rebuilt the SQLite index from {len(records)} canonical record(s).")


@app.command("config-check")
def config_check() -> None:
    """Validate configuration without revealing secrets."""

    _settings()
    typer.echo("Configuration OK.")


if __name__ == "__main__":
    app()
