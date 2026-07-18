"""Derived, shareable exports of canonical investigation records."""

import html
import re
from dataclasses import dataclass
from enum import StrEnum

from forge.persistence.markdown import render_record
from forge.persistence.metadata import InvestigationRecord


class ExportFormat(StrEnum):
    """Formats available at the user-facing export boundary."""

    MARKDOWN = "markdown"
    HTML = "html"
    TEXT = "text"

    @property
    def label(self) -> str:
        return {
            ExportFormat.MARKDOWN: "Markdown",
            ExportFormat.HTML: "HTML",
            ExportFormat.TEXT: "Plain text",
        }[self]


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    """Download-ready representation of one investigation."""

    data: bytes
    file_name: str
    mime_type: str


def export_record(record: InvestigationRecord, export_format: ExportFormat) -> ExportArtifact:
    """Render a record without changing its canonical Markdown storage."""

    canonical_markdown = render_record(record)
    if export_format is ExportFormat.MARKDOWN:
        text = canonical_markdown
        extension = "md"
        mime_type = "text/markdown"
    elif export_format is ExportFormat.HTML:
        text = _html_document(record, canonical_markdown)
        extension = "html"
        mime_type = "text/html"
    else:
        text = _plain_text(canonical_markdown)
        extension = "txt"
        mime_type = "text/plain"
    return ExportArtifact(
        data=text.encode("utf-8"),
        file_name=f"{record.id}.{extension}",
        mime_type=mime_type,
    )


def _html_document(record: InvestigationRecord, canonical_markdown: str) -> str:
    title = html.escape(f"Investigation: {record.seed}", quote=True)
    content = html.escape(canonical_markdown, quote=False)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{
      margin: 0; background: #f7f5ef; color: #20201d;
      font: 1rem/1.55 system-ui, sans-serif;
    }}
    main {{ max-width: 72rem; margin: 0 auto; padding: 2rem; }}
    pre {{ overflow-wrap: anywhere; white-space: pre-wrap; font: inherit; }}
  </style>
</head>
<body>
  <main><pre>{content}</pre></main>
</body>
</html>
"""


def _plain_text(canonical_markdown: str) -> str:
    lines: list[str] = []
    in_code_block = False
    for line in canonical_markdown.splitlines():
        if line.startswith("<!-- forge-record:"):
            continue
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if not in_code_block:
            line = re.sub(r"^#{1,6}\s+", "", line)
            line = re.sub(r"^(\s*)-\s+", r"\1", line)
            line = line.replace("**", "").replace("`", "")
            for character in ("\\", "[", "]", "(", ")"):
                line = line.replace(f"\\{character}", character)
            line = html.unescape(line)
        lines.append(line.rstrip())
    return "\n".join(lines).rstrip() + "\n"


__all__ = ["ExportArtifact", "ExportFormat", "export_record"]
