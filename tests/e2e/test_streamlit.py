from datetime import UTC, datetime
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from forge.application.budgets import DepthBudget, live_run_confirmation_prompt
from forge.application.decisions import submit_decision
from forge.application.orchestrator import _recovery_prompt
from forge.domain.investigation import DepthMode, InvestigationWorkflow, WorkflowStage
from forge.gateways.model import FailureKind, ModelReceipt, ModelRole, ModelUsage
from forge.persistence.markdown import MarkdownInvestigationRepository
from forge.persistence.metadata import InvestigationRecord


@pytest.fixture
def streamlit_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-never-used")
    for role in (
        "LEAD",
        "RESEARCHER",
        "CONNECTION_FINDER",
        "SYNTHESIZER",
        "SKEPTIC",
        "EXPERIMENT_DESIGNER",
    ):
        monkeypatch.setenv(f"FORGE_MODEL_{role}", "test/model")
    monkeypatch.setenv("FORGE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FORGE_OUTPUT_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("FORGE_LOG_DIR", str(tmp_path / "logs"))
    return tmp_path


def app_test() -> AppTest:
    app_path = Path(__file__).parents[2] / "src/forge/ui/streamlit_app.py"
    return AppTest.from_file(app_path, default_timeout=5)


def test_streamlit_completes_deterministic_investigation_with_ae_controls(
    streamlit_environment: Path,
) -> None:
    at = app_test().run()

    assert not at.exception
    at.text_area(key="seed").input("Why does the kettle whistle?")
    at.button(key="prepare_start").click().run()
    at.button(key="decision_A").click().run()

    assert "at most 6 model calls" in at.markdown[-1].value
    assert [button.label[0] for button in at.button if button.key.startswith("decision_")] == [
        "A",
        "B",
        "C",
        "D",
        "E",
    ]

    at.button(key="decision_D").click().run()
    for _ in range(3):
        at.button(key="decision_A").click().run()

    assert not at.exception
    assert "Completed" in [status.label for status in at.status]
    records = MarkdownInvestigationRepository(
        streamlit_environment / "outputs" / "investigations"
    ).list_records()
    assert len(records) == 1
    assert records[0].workflow.stage.value == "completed"
    assert records[0].decisions[0].prompt.kind.value == "mode"
    assert records[0].decisions[0].selection.letter.value == "A"
    assert records[0].decisions[1].selection.letter.value == "D"


def test_custom_answer_field_is_hidden_until_e_is_selected(
    streamlit_environment: Path,
) -> None:
    at = app_test().run()
    at.text_area(key="seed").input("Let me add detail with minimal typing.")
    at.button(key="prepare_start").click().run()

    assert not any(field.key == "custom_answer" for field in at.text_area)
    at.button(key="decision_E").click().run()

    assert at.text_area(key="custom_answer").label == "Custom answer"
    assert at.button(key="submit_custom").label == "Submit custom answer"


def test_saved_cli_record_is_available_to_resume_in_streamlit(
    streamlit_environment: Path,
) -> None:
    from typer.testing import CliRunner

    from forge.cli import app

    started = CliRunner().invoke(
        app,
        ["investigate", "--seed", "Move between interfaces.", "--mode", "quick"],
        input="D\nA\nD\n",
    )
    assert started.exit_code == 0, started.output

    at = app_test().run()
    saved_option = next(
        option
        for option in at.selectbox(key="saved_record").options
        if option.startswith("Move between interfaces.")
    )
    at.selectbox(key="saved_record").select(saved_option)
    at.button(key="resume_saved").click().run()

    assert at.button(key="decision_A").label == "A — Resume from saved work"
    at.button(key="decision_A").click().run()
    resumed = MarkdownInvestigationRepository(
        streamlit_environment / "outputs" / "investigations"
    ).list_records()[0]
    assert resumed.workflow.stage.value == "action_checkpoint"
    assert resumed.workflow.status.value == "active"


def test_streamlit_record_is_available_to_resume_in_cli(
    streamlit_environment: Path,
) -> None:
    from typer.testing import CliRunner

    from forge.cli import app

    at = app_test().run()
    at.text_area(key="seed").input("Start here and finish in the terminal.")
    at.button(key="prepare_start").click().run()
    at.button(key="decision_A").click().run()
    at.button(key="decision_D").click().run()
    at.button(key="decision_A").click().run()
    at.button(key="decision_D").click().run()

    repository = MarkdownInvestigationRepository(
        streamlit_environment / "outputs" / "investigations"
    )
    paused = repository.list_records()[0]
    assert paused.workflow.status.value == "paused"

    resumed = CliRunner().invoke(app, ["resume", paused.id], input="A\nA\n")

    assert resumed.exit_code == 0, resumed.output
    assert repository.load(paused.id).workflow.stage.value == "completed"


def test_live_saved_record_requires_fresh_ae_confirmation_without_exposing_secret(
    streamlit_environment: Path,
) -> None:
    investigation_id = "inv_live_streamlit_resume"
    prompt = live_run_confirmation_prompt(
        investigation_id=investigation_id,
        depth=DepthMode.QUICK,
        budget=DepthBudget(max_calls=6, max_output_tokens_per_call=1200),
        source_attached=False,
    )
    record = InvestigationRecord(
        id=investigation_id,
        seed="Resume paid work only after another confirmation.",
        workflow=InvestigationWorkflow.start(
            depth=DepthMode.QUICK,
            at=datetime(2026, 7, 17, tzinfo=UTC),
        ),
        decisions=(submit_decision(prompt, "A"),),
        live_execution_approved=True,
    )
    MarkdownInvestigationRepository(streamlit_environment / "outputs" / "investigations").save(
        record
    )

    at = app_test().run()
    saved_option = next(
        option
        for option in at.selectbox(key="saved_record").options
        if option.startswith("Resume paid work")
    )
    at.selectbox(key="saved_record").select(saved_option)
    at.button(key="resume_saved").click().run()

    assert "Continue a live Quick investigation" in at.markdown[-1].value
    assert at.button(key="decision_A").label == "A — Approve live execution"
    assert "test-key-never-used" not in str(at.session_state)


def test_recovery_screen_shows_quarantined_model_output_without_trusting_it(
    streamlit_environment: Path,
) -> None:
    investigation_id = "inv_quarantined_response"
    at_time = datetime(2026, 7, 18, tzinfo=UTC)
    workflow = InvestigationWorkflow.start(depth=DepthMode.QUICK, at=at_time)
    for stage in (
        WorkflowStage.FOCUS_CHECKPOINT,
        WorkflowStage.PREMISES_EXTRACTED,
        WorkflowStage.EVIDENCE_CHECKPOINT,
    ):
        workflow = workflow.advance(stage, at=at_time)
    approval_prompt = live_run_confirmation_prompt(
        investigation_id=investigation_id,
        depth=DepthMode.QUICK,
        budget=DepthBudget(max_calls=6, max_output_tokens_per_call=1200),
        source_attached=False,
    )
    artifact_path = (
        streamlit_environment / "outputs/model-calls" / investigation_id / "call_invalid.json"
    )
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text(
        '{"response":{"choices":[{"message":{"content":"<b>model output, not HTML</b>"}}]}}',
        encoding="utf-8",
    )
    receipt = ModelReceipt(
        role=ModelRole.CONNECTION_FINDER,
        model="test/model",
        started_at=at_time,
        finished_at=at_time,
        duration_ms=0,
        attempts=1,
        usage=ModelUsage(),
        prompt_contract_version="connection-finder-v1",
        artifact_path=artifact_path,
    )
    record = InvestigationRecord(
        id=investigation_id,
        seed="Let me inspect rejected output.",
        workflow=workflow,
        decisions=(submit_decision(approval_prompt, "A"),),
        pending_decision=_recovery_prompt(
            investigation_id,
            workflow.stage,
            failure_kind=FailureKind.MALFORMED_OUTPUT,
        ),
        live_execution_approved=True,
        model_receipts=(receipt,),
    )
    MarkdownInvestigationRepository(streamlit_environment / "outputs/investigations").save(record)

    at = app_test().run()
    saved_option = next(
        option
        for option in at.selectbox(key="saved_record").options
        if option.startswith("Let me inspect")
    )
    at.selectbox(key="saved_record").select(saved_option)
    at.button(key="resume_saved").click().run()
    at.button(key="decision_A").click().run()

    assert any("quarantined" in item.value.lower() for item in at.markdown)
    assert "quarantined" in at.markdown[-1].value.lower()
    assert any(item.value == "<b>model output, not HTML</b>" for item in at.code)
    assert not at.exception


def test_streamlit_defaults_to_loopback_binding() -> None:
    config = (Path(__file__).parents[2] / ".streamlit/config.toml").read_text(encoding="utf-8")

    assert 'address = "127.0.0.1"' in config
