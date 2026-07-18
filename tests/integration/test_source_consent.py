from datetime import UTC, datetime
from pathlib import Path

import pytest

from forge.application.decisions import DecisionKind
from forge.application.orchestrator import InvestigationOrchestrator
from forge.application.source_ingestion import SourceImportError, import_local_source
from forge.domain.epistemics import Evidence, PrimarySourceDetails
from forge.domain.investigation import DepthMode, WorkflowStage, WorkflowStatus
from forge.gateways.fake import DeterministicSpecialistRunner
from forge.persistence.markdown import MarkdownInvestigationRepository
from forge.persistence.sqlite import SQLiteProjection
from forge.persistence.unit_of_work import InvestigationUnitOfWork


def make_orchestrator(tmp_path: Path):
    markdown = MarkdownInvestigationRepository(tmp_path / "outputs" / "investigations")
    store = InvestigationUnitOfWork(
        markdown,
        SQLiteProjection(tmp_path / "data" / "forge.sqlite3"),
    )
    runner = DeterministicSpecialistRunner()
    orchestrator = InvestigationOrchestrator(
        store=store,
        specialists=runner,
        clock=lambda: datetime.now(UTC),
        lock_root=tmp_path / "data" / "locks",
    )
    return orchestrator, runner, markdown


@pytest.mark.parametrize("suffix", [".txt", ".md"])
def test_text_and_markdown_import_as_utf8_source(tmp_path: Path, suffix: str) -> None:
    path = tmp_path / f"primary{suffix}"
    path.write_text("Observed directly.\n", encoding="utf-8")

    source = import_local_source(path)

    assert source.content == "Observed directly.\n"
    assert source.reference.path == str(path.resolve())
    assert len(source.reference.sha256) == 64


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        ("source.pdf", b"%PDF-1.7", "Only UTF-8 .txt and .md sources are supported."),
        ("source.txt", b"before\x00after", "Source must be UTF-8 text, not binary data."),
        ("source.md", b"\xff\xfe", "Source must be valid UTF-8 text."),
    ],
)
def test_unsupported_or_binary_sources_fail_clearly(
    tmp_path: Path,
    name: str,
    content: bytes,
    message: str,
) -> None:
    path = tmp_path / name
    path.write_bytes(content)

    with pytest.raises(SourceImportError, match=message):
        import_local_source(path)


@pytest.mark.asyncio
async def test_source_waits_at_consent_before_any_specialist_call(tmp_path: Path) -> None:
    source_path = tmp_path / "observation.md"
    source_path.write_text("A local observation.", encoding="utf-8")
    source = import_local_source(source_path)
    orchestrator, runner, markdown = make_orchestrator(tmp_path)

    consent = await orchestrator.start(
        investigation_id="inv_source_consent",
        seed="What follows from this source?",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 17, 12, 0, tzinfo=UTC),
        source_reference=source.reference,
    )

    assert consent.record.workflow.stage is WorkflowStage.SOURCE_CONSENT
    assert consent.prompt.kind is DecisionKind.SOURCE_CONSENT
    assert consent.record.source_transmission_approved is False
    assert consent.record.source_references == (source.reference,)
    assert runner.calls == []
    assert markdown.load(consent.record.id) == consent.record
    saved_markdown = (markdown.root / f"{consent.record.id}.md").read_text(encoding="utf-8")
    assert "**Transmission approved:** no" in saved_markdown


@pytest.mark.asyncio
async def test_approval_is_recorded_before_focus_and_model_work(tmp_path: Path) -> None:
    source_path = tmp_path / "observation.txt"
    source_path.write_text("A local observation.", encoding="utf-8")
    source = import_local_source(source_path)
    orchestrator, runner, _ = make_orchestrator(tmp_path)
    consent = await orchestrator.start(
        investigation_id="inv_source_approved",
        seed="Use this source?",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 17, 12, 0, tzinfo=UTC),
        source_reference=source.reference,
    )

    focus = await orchestrator.submit_decision(
        consent.record.id,
        prompt_id=consent.prompt.id,
        raw_choice="A",
    )

    assert focus.record.workflow.stage is WorkflowStage.FOCUS_CHECKPOINT
    assert focus.record.source_transmission_approved is True
    assert focus.record.decisions[-1].prompt.kind is DecisionKind.SOURCE_CONSENT
    assert runner.calls == []


@pytest.mark.parametrize("decline_choice", ["B", "C"])
@pytest.mark.asyncio
async def test_decline_keeps_reference_and_offers_manual_evidence_path(
    tmp_path: Path,
    decline_choice: str,
) -> None:
    source_path = tmp_path / "private.md"
    source_path.write_text("Keep this local.", encoding="utf-8")
    source = import_local_source(source_path)
    orchestrator, runner, _ = make_orchestrator(tmp_path)
    consent = await orchestrator.start(
        investigation_id="inv_source_declined",
        seed="Investigate without transmitting the file.",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 17, 12, 0, tzinfo=UTC),
        source_reference=source.reference,
    )

    focus = await orchestrator.submit_decision(
        consent.record.id,
        prompt_id=consent.prompt.id,
        raw_choice=decline_choice,
    )

    assert focus.record.workflow.stage is WorkflowStage.FOCUS_CHECKPOINT
    assert focus.record.source_transmission_approved is False
    assert focus.record.source_references == (source.reference,)
    assert "manual" in focus.record.unresolved_questions[-1].lower()
    assert runner.calls == []


@pytest.mark.asyncio
async def test_manual_source_choice_creates_local_only_primary_source_evidence(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "private.md"
    source_path.write_text("Private content must not be copied or transmitted.", encoding="utf-8")
    source = import_local_source(source_path)
    orchestrator, runner, markdown = make_orchestrator(tmp_path)
    consent = await orchestrator.start(
        investigation_id="inv_source_manual_evidence",
        seed="Keep a traceable local source reference.",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 17, 12, 0, tzinfo=UTC),
        source_reference=source.reference,
    )

    focus = await orchestrator.submit_decision(
        consent.record.id,
        prompt_id=consent.prompt.id,
        raw_choice="C",
    )

    assert focus.record.source_transmission_approved is False
    assert len(focus.record.epistemic_items) == 1
    manual_evidence = focus.record.epistemic_items[0]
    assert isinstance(manual_evidence, Evidence)
    assert isinstance(manual_evidence.details, PrimarySourceDetails)
    assert manual_evidence.details.source_reference == str(source_path)
    assert manual_evidence.details.content_hash == source.reference.sha256
    saved = markdown.root.joinpath(f"{focus.record.id}.md").read_text(encoding="utf-8")
    assert "Private content must not be copied or transmitted." not in saved
    assert runner.calls == []


@pytest.mark.asyncio
async def test_source_consent_can_pause_without_losing_the_question(tmp_path: Path) -> None:
    source_path = tmp_path / "pause.txt"
    source_path.write_text("Pause before deciding.", encoding="utf-8")
    source = import_local_source(source_path)
    orchestrator, runner, _ = make_orchestrator(tmp_path)
    consent = await orchestrator.start(
        investigation_id="inv_source_pause",
        seed="Pause safely.",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 17, 12, 0, tzinfo=UTC),
        source_reference=source.reference,
    )

    paused = await orchestrator.submit_decision(
        consent.record.id,
        prompt_id=consent.prompt.id,
        raw_choice="D",
    )

    assert paused.record.workflow.status is WorkflowStatus.PAUSED
    assert paused.record.pending_decision == consent.prompt
    assert runner.calls == []
