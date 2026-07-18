import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from forge.cli import app
from forge.persistence.markdown import MarkdownInvestigationRepository

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
        input="D\na\nA\n A \n",
    )

    assert result.exit_code == 0, result.output
    assert "completed (active)" in result.output
    assert "at most 8 model calls" in result.output
    match = re.search(r"inv_[a-z0-9]+", result.output)
    assert match is not None
    record_path = cli_environment / "outputs" / "investigations" / f"{match.group()}.md"
    assert record_path.is_file()
    record = MarkdownInvestigationRepository(record_path.parent).load(match.group())
    assert record.decisions[0].prompt.kind.value == "live_confirmation"
    assert record.decisions[0].selection.letter.value == "D"
    assert record.live_execution_approved is False

    listed = runner.invoke(app, ["list"])
    assert match.group() in listed.output
    assert "completed" in listed.output


def test_declining_live_confirmation_starts_nothing(cli_environment: Path) -> None:
    result = runner.invoke(
        app,
        ["investigate", "--seed", "Do not spend anything.", "--mode", "quick"],
        input="B\n",
    )

    assert result.exit_code == 0, result.output
    assert "no provider call was made" in result.output
    repository = MarkdownInvestigationRepository(cli_environment / "outputs" / "investigations")
    assert repository.list_records() == ()


def test_prior_investigation_can_seed_a_traceable_follow_up(cli_environment: Path) -> None:
    first = runner.invoke(
        app,
        ["investigate", "--seed", "Why does the kettle whistle?", "--mode", "quick"],
        input="D\nA\nA\nA\n",
    )
    assert first.exit_code == 0, first.output
    first_match = re.search(r"inv_[a-z0-9]+", first.output)
    assert first_match is not None
    first_id = first_match.group()

    follow_up = runner.invoke(
        app,
        [
            "investigate",
            "--seed",
            "What should we test next?",
            "--mode",
            "quick",
            "--prior",
            first_id,
        ],
        input="D\nA\nA\nA\n",
    )

    assert follow_up.exit_code == 0, follow_up.output
    follow_up_match = re.search(r"inv_[a-z0-9]+", follow_up.output)
    assert follow_up_match is not None
    follow_up_id = follow_up_match.group()
    record = MarkdownInvestigationRepository(cli_environment / "outputs" / "investigations").load(
        follow_up_id
    )
    assert record.prior_investigation_ids == (first_id,)
    assert f"Prior investigation {first_id}" in record.seed


def test_interactive_mode_selection_uses_ae_when_flag_is_omitted(
    cli_environment: Path,
) -> None:
    result = runner.invoke(
        app,
        ["investigate", "--seed", "Choose a bounded mode with one letter."],
        input="A\nD\nA\nA\nA\n",
    )

    assert result.exit_code == 0, result.output
    assert "How deep should this investigation go?" in result.output
    assert "Starting" in result.output and "in quick mode" in result.output


def test_rebuild_index_command_restores_projection_from_markdown(
    cli_environment: Path,
) -> None:
    started = runner.invoke(
        app,
        ["investigate", "--seed", "Rebuild this canonical record.", "--mode", "quick"],
        input="D\nA\nA\nA\n",
    )
    assert started.exit_code == 0, started.output
    index_path = cli_environment / "data" / "forge.sqlite3"
    index_path.unlink()

    rebuilt = runner.invoke(app, ["rebuild-index"])

    assert rebuilt.exit_code == 0, rebuilt.output
    assert "from 1 canonical record" in rebuilt.output
    assert index_path.is_file()


def test_invalid_choice_repeats_the_same_question_before_continuing(
    cli_environment: Path,
) -> None:
    result = runner.invoke(
        app,
        ["investigate", "--seed", "What survives a bad input?", "--mode", "quick"],
        input="D\nnot-a-choice\nA\nA\nA\n",
    )

    assert result.exit_code == 0, result.output
    assert "Choose A, B, C, D, or E." in result.output
    assert result.output.count("Which focus should guide this investigation?") == 2
    assert "completed (active)" in result.output


def test_deferred_action_pauses_and_resume_reasks_the_question(
    cli_environment: Path,
) -> None:
    started = runner.invoke(
        app,
        ["investigate", "--seed", "Can I decide later?", "--mode", "quick"],
        input="D\nA\nA\nB\n",
    )

    assert started.exit_code == 0, started.output
    assert "action_checkpoint (paused)" in started.output
    match = re.search(r"Resume later with: forge resume (inv_[a-z0-9]+)", started.output)
    assert match is not None

    resumed = runner.invoke(app, ["resume", match.group(1)], input="A\nA\n")

    assert resumed.exit_code == 0, resumed.output
    assert "What should we do with the proposed test or action?" in resumed.output
    assert "completed (active)" in resumed.output


def test_local_source_requires_consent_and_can_stay_local(
    cli_environment: Path,
) -> None:
    source = cli_environment / "private-observation.md"
    source.write_text("This should remain local.", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "investigate",
            "--seed",
            "What follows from the private observation?",
            "--mode",
            "quick",
            "--source",
            str(source),
        ],
        input="D\nC\nA\nA\nA\n",
    )

    assert result.exit_code == 0, result.output
    assert "will leave this machine only after explicit approval" in result.output
    assert "May this local source be sent" in result.output
    match = re.search(r"inv_[a-z0-9]+", result.output)
    assert match is not None
    repository = MarkdownInvestigationRepository(cli_environment / "outputs" / "investigations")
    record = repository.load(match.group())
    assert record.source_transmission_approved is False
    assert record.source_references[0].path == str(source)


def test_unsupported_local_source_fails_before_investigation_creation(
    cli_environment: Path,
) -> None:
    source = cli_environment / "unsupported.pdf"
    source.write_bytes(b"%PDF-1.7")

    result = runner.invoke(
        app,
        ["investigate", "--seed", "Do not start.", "--source", str(source)],
    )

    assert result.exit_code == 2
    assert "Only UTF-8 .txt and .md sources are supported." in result.output
    repository = MarkdownInvestigationRepository(cli_environment / "outputs" / "investigations")
    assert repository.list_records() == ()


def test_config_check_reports_missing_settings_without_secrets(
    cli_environment: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FORGE_MODEL_SKEPTIC")

    result = runner.invoke(app, ["config-check"])

    assert result.exit_code == 1
    assert "FORGE_MODEL_SKEPTIC" in result.output
    assert "test-key-never-used" not in result.output
