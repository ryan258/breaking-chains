from datetime import UTC, datetime

import pytest

from forge.domain.epistemics import (
    Confidence,
    ConfidenceLevel,
    DirectObservationDetails,
    Evidence,
    Premise,
    Provenance,
)
from forge.domain.investigation import DepthMode, InvestigationWorkflow
from forge.exports import ExportFormat, export_record
from forge.persistence.markdown import render_record
from forge.persistence.metadata import (
    ActionProposal,
    ChallengeDisposition,
    InvestigationRecord,
    SkepticalChallenge,
)


@pytest.fixture
def record() -> InvestigationRecord:
    return InvestigationRecord(
        id="inv_export_example",
        seed="What does <script>alert('no')</script> reveal?",
        selected_focus="Compare <img src=x onerror=alert(1)> formats without losing data.",
        workflow=InvestigationWorkflow.start(
            depth=DepthMode.QUICK,
            at=datetime(2026, 7, 18, tzinfo=UTC),
        ),
        unresolved_questions=("Which format is easiest to share?",),
    )


def test_markdown_export_preserves_the_canonical_record(record: InvestigationRecord) -> None:
    artifact = export_record(record, ExportFormat.MARKDOWN)

    assert artifact.data.decode("utf-8") == render_record(record)
    assert artifact.file_name == "inv_export_example.md"
    assert artifact.mime_type == "text/markdown"


def test_html_export_is_a_safe_standalone_document(record: InvestigationRecord) -> None:
    artifact = export_record(record, ExportFormat.HTML)
    text = artifact.data.decode("utf-8")

    assert text.startswith("<!doctype html>")
    assert "<title>Investigation: What does &lt;script&gt;" in text
    assert "<script>alert('no')</script>" not in text
    assert "<img src=x onerror=alert(1)>" not in text
    assert "Compare &lt;img src=x onerror=alert(1)&gt; formats" in text
    assert "Machine-readable record" in text
    assert '<header class="report-cover">' in text
    assert '<section class="executive-summary"' in text
    assert '<section class="report-section" id="analysis"' in text
    assert '<section class="canonical-appendix"' in text
    assert "@page" in text
    assert "break-inside: avoid" in text
    assert "<details" not in text
    metadata_css = text.split(".report-metadata {", maxsplit=1)[1].split("}", maxsplit=1)[0]
    assert "position: absolute" not in metadata_css
    assert "<main><pre>" not in text
    assert artifact.file_name == "inv_export_example.html"
    assert artifact.mime_type == "text/html"


def test_kids_html_export_is_a_safe_playful_document(record: InvestigationRecord) -> None:
    artifact = export_record(record, ExportFormat.KIDS_HTML)
    text = artifact.data.decode("utf-8")

    assert text.startswith("<!doctype html>")
    assert "<title>Mystery Mission: What does &lt;script&gt;" in text
    assert "<script>alert('no')</script>" not in text
    assert "<img src=x onerror=alert(1)>" not in text
    assert '<header class="kid-cover">' in text
    assert "The clue board" in text
    assert "Nothing pinned here yet." in text
    assert "Which format is easiest to share?" in text
    assert "For grown-ups: the whole case file" in text
    assert "No experiment picked yet" in text
    assert "@page" in text
    assert "<details" not in text
    assert artifact.file_name == "inv_export_example.kids.html"
    assert artifact.mime_type == "text/html"


def test_kids_html_export_renders_populated_records_in_kid_language() -> None:
    record = InvestigationRecord(
        id="inv_kids_populated",
        seed="Why does the kettle whistle?",
        selected_focus="Where the sound comes from.",
        workflow=InvestigationWorkflow.start(
            depth=DepthMode.QUICK,
            at=datetime(2026, 7, 18, tzinfo=UTC),
        ),
        epistemic_items=(
            Premise(
                id="epi_kids_premise",
                statement="The kettle is sealed except at the spout.",
                uncertainty=Confidence(level=ConfidenceLevel.HIGH, rationale="We checked the lid."),
                origin="Kitchen inspection",
            ),
            Evidence(
                id="epi_kids_evidence",
                statement="The whistle starts right around boiling.",
                uncertainty=Confidence(level=ConfidenceLevel.LOW, rationale="Only one try so far."),
                provenance=Provenance(origin="Kitchen notebook"),
                details=DirectObservationDetails(observer="Kid detective", conditions="One boil"),
            ),
        ),
        skeptical_challenges=(
            SkepticalChallenge(
                target_id="epi_kids_evidence",
                challenge="Maybe the lid rattles instead of the spout whistling.",
                disposition=ChallengeDisposition.REVISE,
                rationale="Hold the lid still on the next boil.",
            ),
        ),
        selected_action=ActionProposal(
            statement="Boil water and briefly cover the spout with a spoon.",
            expected_observation="The whistle stops while the spout is covered.",
            disconfirming_observation="The whistle keeps going anyway.",
            cost="Five minutes and one kettle of water.",
            risk="Hot steam near hands.",
            stopping_condition="Stop after one minute or if anything feels unsafe.",
        ),
    )

    text = export_record(record, ExportFormat.KIDS_HTML).data.decode("utf-8")

    assert "Pretty sure" in text
    assert "Just guessing" in text
    assert "Where it came from:</strong> Kitchen notebook" in text
    assert "Changed a bit" in text
    assert "When to stop" in text
    assert "grown-up nearby" in text
    assert "Nothing pinned here yet." in text  # claims and guesses stay empty


def test_text_export_removes_markdown_presentation_syntax(record: InvestigationRecord) -> None:
    artifact = export_record(record, ExportFormat.TEXT)
    text = artifact.data.decode("utf-8")

    assert text.startswith("Investigation: What does <script>alert('no')</script> reveal?")
    assert "Findings" in text
    assert "Machine-readable record" in text
    assert "# Investigation" not in text
    assert "**ID:**" not in text
    assert artifact.file_name == "inv_export_example.txt"
    assert artifact.mime_type == "text/plain"
