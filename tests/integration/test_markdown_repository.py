from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from forge.application.decisions import (
    ChoiceLetter,
    DecisionAttempt,
    DecisionKind,
    DecisionOption,
    DecisionPrompt,
)
from forge.domain.epistemics import (
    Confidence,
    ConfidenceLevel,
    DerivedClaim,
    EpistemicLink,
    Evidence,
    ExploratoryItem,
    ExploratoryType,
    LinkKind,
    MeasurementDetails,
    Premise,
    Provenance,
)
from forge.domain.investigation import DepthMode, InvestigationWorkflow, WorkflowStage
from forge.persistence.markdown import (
    MarkdownInvestigationRepository,
    RecordFormatError,
    render_record,
)
from forge.persistence.metadata import (
    ActionProposal,
    ChallengeDisposition,
    InvestigationRecord,
    LocalSourceReference,
    SkepticalChallenge,
)

STARTED = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)


def confidence() -> Confidence:
    return Confidence(level=ConfidenceLevel.MEDIUM, rationale="Supported but not fully tested.")


def mode_decision() -> DecisionAttempt:
    prompt = DecisionPrompt(
        id="depth-mode",
        kind=DecisionKind.MODE,
        question="How deeply should we investigate?",
        options=(
            DecisionOption(
                letter=ChoiceLetter.A,
                label="Standard",
                description="Balanced depth and speed.",
                is_recommended=True,
            ),
            DecisionOption(letter=ChoiceLetter.B, label="Quick", description="Fast triage."),
            DecisionOption(letter=ChoiceLetter.C, label="Deep", description="Broader analysis."),
            DecisionOption(letter=ChoiceLetter.D, label="Pause", description="Decide later."),
            DecisionOption(
                letter=ChoiceLetter.E,
                label="Custom answer",
                description="Add only as much detail as desired.",
                accepts_custom_input=True,
            ),
        ),
    )
    return DecisionAttempt(prompt=prompt, selection=prompt.options[0])


def paused_workflow() -> InvestigationWorkflow:
    workflow = InvestigationWorkflow.start(depth=DepthMode.STANDARD, at=STARTED)
    for minute, stage in enumerate(
        (
            WorkflowStage.FOCUS_CHECKPOINT,
            WorkflowStage.PREMISES_EXTRACTED,
            WorkflowStage.EVIDENCE_CHECKPOINT,
        ),
        start=1,
    ):
        workflow = workflow.advance(stage, at=STARTED + timedelta(minutes=minute))
    return workflow.pause(at=STARTED + timedelta(minutes=4))


def investigation_record() -> InvestigationRecord:
    premise = Premise(
        id="epi_closed_system",
        statement="The system is closed during measurement.",
        uncertainty=confidence(),
        origin="Investigation setup",
    )
    evidence = Evidence(
        id="epi_mass_reading",
        statement="The sample measured 2.4 kilograms.",
        uncertainty=confidence(),
        provenance=Provenance(origin="lab-notes.txt", locator="line 12"),
        details=MeasurementDetails(
            method="Calibrated digital scale",
            unit="kilogram",
            conditions="Stable indoor surface",
        ),
    )
    claim = DerivedClaim(
        id="epi_nonzero_mass",
        statement="The sample has nonzero mass.",
        uncertainty=confidence(),
        provenance=Provenance(origin="Synthesizer role", locator="run-1"),
        dependencies=(premise.id, evidence.id),
        derivation="A positive calibrated measurement implies nonzero mass.",
        links=(EpistemicLink(kind=LinkKind.SUPPORTS, target_id=evidence.id),),
    )
    hypothesis = ExploratoryItem(
        id="epi_temperature_connection",
        statement="Temperature may explain variation between readings.",
        uncertainty=confidence(),
        provenance=Provenance(origin="Connection Finder role", locator="run-1"),
        exploratory_type=ExploratoryType.CONNECTION,
        based_on=(evidence.id,),
    )
    return InvestigationRecord(
        id="inv_mass_question",
        seed="Why do repeated readings differ?",
        selected_focus="Test whether measurement conditions explain the variation.",
        workflow=paused_workflow(),
        epistemic_items=(premise, evidence, claim, hypothesis),
        decisions=(mode_decision(),),
        source_references=(
            LocalSourceReference(
                path="sources/lab-notes.txt",
                sha256="a" * 64,
                locator="lines 10-14",
            ),
        ),
        skeptical_challenges=(
            SkepticalChallenge(
                target_id=hypothesis.id,
                challenge="Only one environment has been observed.",
                disposition=ChallengeDisposition.REVISE,
                rationale="Narrow the hypothesis until another environment is measured.",
            ),
        ),
        selected_action=ActionProposal(
            statement="Repeat the measurement at two controlled temperatures.",
            expected_observation="Variation tracks temperature.",
            disconfirming_observation="Variation is unchanged across temperatures.",
            cost="Two measurement sessions.",
            risk="Low.",
            stopping_condition="Stop after three readings per temperature.",
        ),
        unresolved_questions=("Does humidity also affect the scale?",),
    )


def test_record_round_trips_without_losing_domain_content(tmp_path: Path) -> None:
    repository = MarkdownInvestigationRepository(tmp_path)
    original = investigation_record()

    path = repository.save(original)
    restored = repository.load(original.id)

    assert path == tmp_path / "inv_mass_question.md"
    assert restored == original
    assert restored.epistemic_items[2].links == original.epistemic_items[2].links
    assert restored.workflow.history == original.workflow.history
    assert restored.decisions == original.decisions


def test_generated_markdown_is_readable_and_keeps_categories_visible(tmp_path: Path) -> None:
    repository = MarkdownInvestigationRepository(tmp_path)

    text = repository.save(investigation_record()).read_text(encoding="utf-8")
    human_section = text.split("<!-- forge-record:begin v1 -->", maxsplit=1)[0]

    for heading in (
        "# Investigation: Why do repeated readings differ?",
        "## Premises",
        "## Evidence",
        "## Derived claims",
        "## Connections and hypotheses",
        "## Skeptical challenges",
        "## Selected action",
        "## Unresolved questions",
        "## Workflow history",
    ):
        assert heading in human_section
    assert "measurement" in human_section
    assert "Calibrated digital scale" in human_section
    assert "kilogram" in human_section
    assert "Stable indoor surface" in human_section
    assert "Synthesizer role" in human_section
    assert "Connection Finder role" in human_section
    assert "sources/lab-notes.txt" in human_section
    assert "OPENROUTER_API_KEY" not in text


def test_untrusted_markdown_is_escaped_in_the_human_readable_section(tmp_path: Path) -> None:
    repository = MarkdownInvestigationRepository(tmp_path)
    record = investigation_record().model_copy(
        update={"seed": "<script>alert(1)</script> [click](javascript:alert(1))"}
    )

    text = repository.save(record).read_text(encoding="utf-8")
    human_section = text.split("<!-- forge-record:begin v1 -->", maxsplit=1)[0]

    assert "<script>" not in human_section
    assert "[click](javascript:alert(1))" not in human_section
    assert "&lt;script&gt;" in human_section
    assert r"\[click\]\(javascript:alert\(1\)\)" in human_section


def test_active_working_record_round_trips_for_stage_level_resume(tmp_path: Path) -> None:
    record = investigation_record()
    active = InvestigationWorkflow.start(depth=DepthMode.STANDARD, at=STARTED)
    working = InvestigationRecord.model_validate(record.model_dump() | {"workflow": active})

    repository = MarkdownInvestigationRepository(tmp_path)
    repository.save(working)

    assert repository.load(working.id) == working


def test_source_references_store_location_and_hash_but_no_content() -> None:
    reference = LocalSourceReference(
        path="sources/observation.txt",
        sha256="b" * 64,
        locator="paragraph 3",
    )

    assert reference.model_dump() == {
        "path": "sources/observation.txt",
        "sha256": "b" * 64,
        "locator": "paragraph 3",
    }
    with pytest.raises(ValidationError):
        LocalSourceReference.model_validate(reference.model_dump() | {"content": "private text"})
    with pytest.raises(ValidationError):
        LocalSourceReference(path="bad\npath", sha256="not-a-hash", locator="line 1")


def test_investigation_id_cannot_escape_repository_root(tmp_path: Path) -> None:
    payload = investigation_record().model_dump()
    payload["id"] = "../outside"

    with pytest.raises(ValidationError):
        InvestigationRecord.model_validate(payload)


def test_record_rejects_explicitly_qualified_self_link() -> None:
    record = investigation_record()
    first_item = record.epistemic_items[0]
    self_link = EpistemicLink(
        kind=LinkKind.CONNECTS,
        target_id=first_item.id,
        target_investigation_id=record.id,
    )
    linked_item = first_item.model_copy(update={"links": (self_link,)})
    invalid_record = record.model_copy(
        update={"epistemic_items": (linked_item, *record.epistemic_items[1:])}
    )

    with pytest.raises(ValidationError, match="cannot link to itself"):
        InvestigationRecord.model_validate(invalid_record.model_dump(mode="python"))


def test_all_repository_operations_reject_symbolic_link_records(tmp_path: Path) -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "inv_mass_question.md"
    linked_record = tmp_path / "inv_linked_record.md"
    linked_record.symlink_to(fixture)
    repository = MarkdownInvestigationRepository(tmp_path)

    with pytest.raises(RecordFormatError, match="symbolic link"):
        repository.load("inv_linked_record")
    with pytest.raises(RecordFormatError, match="symbolic link"):
        repository.exists("inv_linked_record")
    with pytest.raises(RecordFormatError, match="symbolic link"):
        repository.list_records()

    assert linked_record.is_symlink()
    assert fixture.exists()


def test_failed_atomic_replace_preserves_previous_valid_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = MarkdownInvestigationRepository(tmp_path)
    original = investigation_record()
    target = repository.save(original)
    previous_text = target.read_text(encoding="utf-8")
    changed = original.model_copy(
        update={"seed": "A changed seed that must not replace the record."}
    )

    def interrupted_replace(source: Path | str, destination: Path | str) -> None:
        raise OSError("simulated interruption")

    monkeypatch.setattr("forge.persistence.markdown.os.replace", interrupted_replace)

    with pytest.raises(OSError, match="simulated interruption"):
        repository.save(changed)

    assert target.read_text(encoding="utf-8") == previous_text
    assert tuple(tmp_path.glob("*.tmp")) == ()


def test_load_rejects_missing_or_unknown_machine_metadata(tmp_path: Path) -> None:
    repository = MarkdownInvestigationRepository(tmp_path)
    target = tmp_path / "inv_mass_question.md"
    target.write_text("# Looks readable but has no canonical metadata\n", encoding="utf-8")

    with pytest.raises(RecordFormatError, match="metadata block"):
        repository.load("inv_mass_question")


def test_save_and_load_enforce_the_same_byte_limit(tmp_path: Path) -> None:
    record = investigation_record()
    rendered_size = len(render_record(record).encode("utf-8"))
    exact_repository = MarkdownInvestigationRepository(
        tmp_path / "exact", max_record_bytes=rendered_size
    )

    exact_repository.save(record)
    assert exact_repository.load(record.id) == record

    too_small_repository = MarkdownInvestigationRepository(
        tmp_path / "small",
        max_record_bytes=rendered_size - 1,
    )
    with pytest.raises(RecordFormatError, match="size limit"):
        too_small_repository.save(record)
    assert not (tmp_path / "small" / f"{record.id}.md").exists()


def test_load_reads_no_more_than_limit_plus_one_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = MarkdownInvestigationRepository(tmp_path, max_record_bytes=32)
    target = tmp_path / "inv_oversized.md"
    target.write_bytes(b"x" * 33)
    original_stat = Path.stat

    def stale_stat(path: Path, *args: object, **kwargs: object) -> object:
        if path == target:
            actual = original_stat(path, *args, **kwargs)
            return SimpleNamespace(st_size=32, st_mode=actual.st_mode)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stale_stat)

    with pytest.raises(RecordFormatError, match="size limit"):
        repository.load("inv_oversized")


def test_committed_fixture_is_a_valid_human_readable_record() -> None:
    fixture_root = Path(__file__).parents[1] / "fixtures"
    repository = MarkdownInvestigationRepository(fixture_root)

    record = repository.load("inv_mass_question")

    assert record == investigation_record()
