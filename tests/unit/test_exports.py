from datetime import UTC, datetime

import pytest

from forge.domain.investigation import DepthMode, InvestigationWorkflow
from forge.exports import ExportFormat, export_record
from forge.persistence.markdown import render_record
from forge.persistence.metadata import InvestigationRecord


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
