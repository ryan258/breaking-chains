import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from forge.cli import app

runner = CliRunner()


@pytest.fixture
def cli_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
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
    return tmp_path


def test_quick_investigation_completes_with_single_letter_choices(
    cli_environment: Path,
) -> None:
    result = runner.invoke(
        app,
        ["investigate", "--seed", "Why does the kettle whistle?", "--mode", "quick"],
        input="a\nA\n A \n",
    )

    assert result.exit_code == 0, result.output
    assert "completed (active)" in result.output
    match = re.search(r"inv_[a-z0-9]+", result.output)
    assert match is not None
    record_path = cli_environment / "outputs" / "investigations" / f"{match.group()}.md"
    assert record_path.is_file()

    listed = runner.invoke(app, ["list"])
    assert match.group() in listed.output
    assert "completed" in listed.output


def test_deferred_action_pauses_and_resume_reasks_the_question(
    cli_environment: Path,
) -> None:
    started = runner.invoke(
        app,
        ["investigate", "--seed", "Can I decide later?", "--mode", "quick"],
        input="A\nA\nB\n",
    )

    assert started.exit_code == 0, started.output
    assert "action_checkpoint (paused)" in started.output
    match = re.search(r"Resume later with: forge resume (inv_[a-z0-9]+)", started.output)
    assert match is not None

    resumed = runner.invoke(app, ["resume", match.group(1)], input="A\n")

    assert resumed.exit_code == 0, resumed.output
    assert "What should we do with the proposed test or action?" in resumed.output
    assert "completed (active)" in resumed.output


def test_config_check_reports_missing_settings_without_secrets(
    cli_environment: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FORGE_MODEL_SKEPTIC")

    result = runner.invoke(app, ["config-check"])

    assert result.exit_code == 1
    assert "FORGE_MODEL_SKEPTIC" in result.output
    assert "test-key-never-used" not in result.output
