import re
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from forge.application.decisions import DecisionKind
from forge.cli import app
from forge.domain.investigation import WorkflowStage
from forge.persistence.markdown import MarkdownInvestigationRepository
from forge.persistence.sqlite import SQLiteProjection


@pytest.fixture
def acceptance_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "deterministic-placeholder-not-a-live-key")
    for role in (
        "LEAD",
        "RESEARCHER",
        "CONNECTION_FINDER",
        "SYNTHESIZER",
        "SKEPTIC",
        "EXPERIMENT_DESIGNER",
    ):
        monkeypatch.setenv(f"FORGE_MODEL_{role}", "not-a-live/model")
    monkeypatch.setenv("FORGE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("FORGE_OUTPUT_DIR", str(tmp_path / "outputs"))
    monkeypatch.setenv("FORGE_LOG_DIR", str(tmp_path / "logs"))
    return tmp_path


def test_no_credential_acceptance_run_reaches_canonical_markdown_and_sqlite(
    acceptance_environment: Path,
) -> None:
    result = CliRunner().invoke(
        app,
        ["investigate", "--seed", "Where is the strongest leverage point?"],
        input="A\nD\nA\nA\nA\n",
    )

    assert result.exit_code == 0, result.output
    match = re.search(r"inv_[a-z0-9]+", result.output)
    assert match is not None
    investigation_id = match.group()
    markdown = MarkdownInvestigationRepository(
        acceptance_environment / "outputs" / "investigations"
    )
    record = markdown.load(investigation_id)
    projection = SQLiteProjection(acceptance_environment / "data" / "forge.sqlite3")

    assert record.workflow.stage is WorkflowStage.COMPLETED
    assert projection.load_record(investigation_id) == record
    assert {attempt.prompt.kind for attempt in record.decisions} >= {
        DecisionKind.MODE,
        DecisionKind.LIVE_CONFIRMATION,
        DecisionKind.FOCUS_CHECKPOINT,
        DecisionKind.EVIDENCE_CHECKPOINT,
        DecisionKind.ACTION_CHECKPOINT,
    }
    assert record.skeptical_challenges
    assert all(
        challenge.disposition.value in {"retain", "revise", "reject"}
        for challenge in record.skeptical_challenges
    )
    assert record.selected_action is not None
    assert record.selected_action.expected_observation
    assert record.selected_action.disconfirming_observation
    assert projection.search("constraint")
    rendered = (markdown.root / f"{investigation_id}.md").read_text(encoding="utf-8")
    assert "## Premises" in rendered
    assert "## Evidence" in rendered
    assert "## Skeptical challenges" in rendered
    assert "## Selected action" in rendered


def test_acceptance_report_covers_all_eighteen_criteria() -> None:
    project_root = Path(__file__).parents[2]
    result = subprocess.run(
        [sys.executable, "scripts/verify_acceptance.py", "--check-only"],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.count("PASS —") == 18


def test_optional_smoke_requires_ae_approval_before_loading_live_configuration(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).parents[2]
    result = subprocess.run(
        [sys.executable, str(project_root / "scripts/smoke_openrouter.py")],
        cwd=tmp_path,
        input="B\n",
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "at most 1 model calls and 500 output tokens per call" in result.stdout
    assert "No provider call was made." in result.stdout
