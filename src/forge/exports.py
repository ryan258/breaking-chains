"""Derived, shareable exports of canonical investigation records."""

import html
import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from forge.domain.epistemics import (
    DerivedClaim,
    EpistemicItem,
    Evidence,
    ExploratoryItem,
    Premise,
    group_epistemic_items,
)
from forge.persistence.markdown import key_findings, render_record
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


_REPORT_CSS = """
    :root {
      --navy: #0b1f33;
      --blue: #1261a0;
      --cyan: #35a7c7;
      --ink: #17212b;
      --muted: #5f6b76;
      --line: #d9e0e5;
      --wash: #f2f5f7;
      --paper: #ffffff;
      --positive: #16705a;
      --caution: #a35d00;
    }
    * { box-sizing: border-box; }
    html { color-scheme: light; }
    body {
      margin: 0;
      color: var(--ink);
      background: #e9edf0;
      font: 15px/1.58 Inter, "Helvetica Neue", Arial, sans-serif;
      -webkit-font-smoothing: antialiased;
    }
    .report-shell {
      width: min(1120px, calc(100% - 40px));
      margin: 32px auto;
      background: var(--paper);
      box-shadow: 0 18px 60px rgb(11 31 51 / 14%);
    }
    .report-cover {
      position: relative;
      display: flex;
      flex-direction: column;
      min-height: 590px;
      overflow: hidden;
      color: #fff;
      background: var(--navy);
      padding: 64px 72px 54px;
    }
    .report-cover::after {
      position: absolute;
      right: -120px;
      bottom: -230px;
      width: 560px;
      height: 560px;
      border: 80px solid rgb(53 167 199 / 22%);
      border-radius: 50%;
      content: "";
    }
    .cover-brand {
      padding-bottom: 18px;
      border-bottom: 1px solid rgb(255 255 255 / 32%);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .cover-kicker {
      margin-top: 110px;
      color: #83d2e5;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }
    .report-cover h1 {
      position: relative;
      z-index: 1;
      max-width: 820px;
      margin: 18px 0 20px;
      font: 600 clamp(38px, 6vw, 68px)/1.06 Georgia, "Times New Roman", serif;
      letter-spacing: -0.025em;
    }
    .cover-focus {
      position: relative;
      z-index: 1;
      max-width: 700px;
      margin: 0 0 40px;
      color: #cbd7df;
      font-size: 19px;
    }
    .report-metadata {
      z-index: 1;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      width: 100%;
      margin: auto 0 0;
      border-top: 1px solid rgb(255 255 255 / 32%);
      padding-top: 20px;
    }
    .report-metadata div { padding-right: 18px; }
    .report-metadata dt {
      color: #83d2e5;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }
    .report-metadata dd {
      overflow-wrap: anywhere;
      margin: 5px 0 0;
      font-size: 13px;
    }
    .report-metadata .case-id dd { font-size: 11px; letter-spacing: -0.01em; }
    .executive-summary,
    .report-section {
      padding: 64px 72px;
      border-bottom: 1px solid var(--line);
    }
    .executive-summary {
      display: grid;
      grid-template-columns: 72px 1fr;
      background: #f8fafb;
    }
    .section-heading {
      display: grid;
      grid-template-columns: 72px 1fr;
      margin-bottom: 34px;
    }
    .section-number {
      color: var(--cyan);
      font-size: 13px;
      font-weight: 800;
      letter-spacing: 0.08em;
    }
    .eyebrow {
      margin: 0 0 5px;
      color: var(--blue);
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }
    h2 {
      margin: 0;
      color: var(--navy);
      font: 600 clamp(28px, 4vw, 42px)/1.14 Georgia, "Times New Roman", serif;
      letter-spacing: -0.02em;
    }
    .finding-list {
      margin: 36px 0 0;
      padding: 0;
      list-style: none;
    }
    .finding-list li {
      display: grid;
      grid-template-columns: 44px 1fr;
      gap: 16px;
      border-top: 1px solid var(--line);
      padding: 20px 0;
      break-inside: avoid;
    }
    .finding-list p { max-width: 780px; margin: 0; font-size: 17px; }
    .finding-index { color: var(--blue); font-size: 12px; font-weight: 800; }
    .recommendation { background: var(--paper); }
    .recommendation-callout {
      margin-left: 72px;
      border-left: 6px solid var(--cyan);
      background: var(--navy);
      color: #fff;
      padding: 32px 36px;
      break-inside: avoid;
    }
    .recommendation-callout h3 {
      max-width: 820px;
      margin: 0 0 28px;
      font: 600 25px/1.35 Georgia, "Times New Roman", serif;
    }
    .recommendation-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px 32px;
    }
    .recommendation-grid div {
      border-top: 1px solid rgb(255 255 255 / 28%);
      padding-top: 12px;
    }
    .recommendation-grid span {
      color: #83d2e5;
      font-size: 10px;
      font-weight: 800;
      text-transform: uppercase;
    }
    .recommendation-grid p { margin: 6px 0 0; }
    .analysis-grid { display: grid; gap: 48px; margin-left: 72px; }
    .analysis-group > header {
      display: grid;
      grid-template-columns: minmax(180px, 0.8fr) 2fr;
      gap: 24px;
      border-bottom: 2px solid var(--navy);
      padding-bottom: 12px;
    }
    .analysis-group h3 { margin: 0; color: var(--navy); font-size: 18px; }
    .analysis-group header p { margin: 0; color: var(--muted); }
    .item-list {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1px;
      background: var(--line);
    }
    .analysis-item {
      min-width: 0;
      background: var(--paper);
      padding: 24px 22px;
      break-inside: avoid;
    }
    .item-meta { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; }
    .item-type, .confidence {
      color: var(--blue);
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .confidence-low { color: var(--caution); }
    .confidence-high { color: var(--positive); }
    .analysis-item h4 { margin: 12px 0 8px; color: var(--navy); font-size: 16px; line-height: 1.4; }
    .analysis-item p { margin: 7px 0 0; color: var(--muted); font-size: 13px; }
    .analysis-item .provenance, .analysis-item .trace { color: var(--ink); }
    .challenge-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-left: 72px; }
    .challenge-card {
      border-top: 4px solid var(--blue);
      background: var(--wash);
      padding: 24px;
      break-inside: avoid;
    }
    .challenge-card span {
      color: var(--blue);
      font-size: 10px;
      font-weight: 800;
      text-transform: uppercase;
    }
    .challenge-card h3 { margin: 9px 0; color: var(--navy); font-size: 17px; }
    .challenge-card p { margin: 0; color: var(--muted); }
    .open-questions ul { margin: 0 0 0 72px; padding: 0; list-style: none; }
    .open-questions li { border-top: 1px solid var(--line); padding: 18px 0; font-size: 17px; }
    .methodology { background: var(--wash); }
    .methodology > p { max-width: 760px; margin-left: 72px; }
    .method-stats { display: grid; grid-template-columns: repeat(4, 1fr); margin: 36px 0 0 72px; }
    .method-stats div { border-left: 1px solid #bdc8d0; padding: 12px 18px; }
    .method-stats strong { display: block; color: var(--navy); font: 600 32px/1 Georgia, serif; }
    .method-stats span { color: var(--muted); font-size: 11px; text-transform: uppercase; }
    .empty-state { margin: 22px 0; color: var(--muted); font-style: italic; }
    .canonical-appendix { border-bottom: 1px solid var(--line); padding: 32px 72px; }
    .appendix-title { margin: 0 0 12px; color: var(--navy); font-size: 18px; }
    .canonical-appendix pre {
      max-height: 640px;
      overflow: auto;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #101820;
      color: #dfe8ee;
      padding: 24px;
      font: 11px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace;
    }
    footer {
      display: flex;
      justify-content: space-between;
      color: var(--muted);
      padding: 24px 72px;
      font-size: 11px;
    }
    @page { size: A4; margin: 14mm; }
    @media print {
      body { background: #fff; font-size: 10pt; }
      .report-shell { width: 100%; margin: 0; box-shadow: none; }
      .report-cover { min-height: 250mm; break-after: page; }
      .executive-summary, .report-section { padding: 12mm 10mm; }
      .canonical-appendix { break-before: page; }
      .canonical-appendix pre { max-height: none; }
      a { color: inherit; }
    }
    @media (max-width: 760px) {
      .report-shell { width: 100%; margin: 0; }
      .report-cover { min-height: 650px; padding: 36px 24px; }
      .cover-kicker { margin-top: 70px; }
      .report-metadata {
        grid-template-columns: 1fr 1fr;
        gap: 16px;
      }
      .executive-summary, .report-section { padding: 42px 24px; }
      .executive-summary, .section-heading { grid-template-columns: 42px 1fr; }
      .recommendation-callout, .analysis-grid, .challenge-grid, .open-questions ul,
      .methodology > p, .method-stats { margin-left: 0; }
      .recommendation-grid, .item-list, .challenge-grid { grid-template-columns: 1fr; }
      .analysis-group > header { grid-template-columns: 1fr; gap: 6px; }
      .method-stats { grid-template-columns: 1fr 1fr; }
      .canonical-appendix, footer { padding: 28px 24px; }
    }
"""


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
    seed = _escape(record.seed)
    focus = _escape(record.selected_focus or "Focus not selected")
    findings = key_findings(record) or (
        "The investigation has not reached synthesis; no executive findings are available yet.",
    )
    groups = group_epistemic_items(record.epistemic_items)
    canonical = html.escape(canonical_markdown, quote=False)
    premise_section = _item_group(
        "Premises", groups.premises, "Explicit assumptions adopted for this case."
    )
    evidence_section = _item_group(
        "Evidence", groups.evidence, "Inspectable inputs and their provenance."
    )
    claim_section = _item_group(
        "Derived claims", groups.claims, "Conclusions derived from named dependencies."
    )
    exploratory_section = _item_group(
        "Hypotheses and connections",
        groups.exploratory,
        "Exploratory ideas, not evidence.",
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
{_REPORT_CSS}
  </style>
</head>
<body>
  <main class="report-shell">
    <header class="report-cover">
      <div class="cover-brand">First-Principles Forge</div>
      <div class="cover-kicker">Executive investigation report</div>
      <h1>{seed}</h1>
      <p class="cover-focus">{focus}</p>
      <dl class="report-metadata" aria-label="Report metadata">
        <div class="case-id"><dt>Case ID</dt><dd>{_escape(record.id)}</dd></div>
        <div><dt>Status</dt><dd>{_escape(record.workflow.status.value.title())}</dd></div>
        <div><dt>Stage</dt><dd>{_escape(_label(record.workflow.stage.value))}</dd></div>
        <div><dt>Updated</dt><dd>{record.workflow.updated_at:%B %d, %Y}</dd></div>
      </dl>
    </header>

    <section class="executive-summary" aria-labelledby="executive-summary-title">
      <div class="section-number">01</div>
      <div class="section-content">
        <p class="eyebrow">Executive summary</p>
        <h2 id="executive-summary-title">What matters most</h2>
        {_finding_list(findings)}
      </div>
    </section>

    {_action_section(record)}

    <section class="report-section" id="analysis" aria-labelledby="analysis-title">
      <div class="section-heading">
        <div class="section-number">03</div>
        <div><p class="eyebrow">Analysis</p>
        <h2 id="analysis-title">Reasoning and evidence</h2></div>
      </div>
      <div class="analysis-grid">
        {premise_section}
        {evidence_section}
        {claim_section}
        {exploratory_section}
      </div>
    </section>

    {_challenge_section(record)}
    {_open_questions_section(record)}

    <section class="report-section methodology" aria-labelledby="method-title">
      <div class="section-heading">
        <div class="section-number">06</div>
        <div><p class="eyebrow">Method and traceability</p>
        <h2 id="method-title">How to read this report</h2></div>
      </div>
      <p>This report keeps premises, evidence, derived claims, and exploratory ideas visibly
      separate. Confidence labels communicate uncertainty; they do not change an item’s
      epistemic category.</p>
      <div class="method-stats">
        <div><strong>{len(record.source_references)}</strong><span>Local sources</span></div>
        <div><strong>{len(record.epistemic_items)}</strong><span>Reasoning items</span></div>
        <div><strong>{len(record.skeptical_challenges)}</strong><span>Challenges</span></div>
        <div><strong>{len(record.model_receipts)}</strong><span>Model receipts</span></div>
      </div>
    </section>

    <section class="canonical-appendix" aria-labelledby="appendix-title">
      <h2 class="appendix-title" id="appendix-title">
      Machine-readable record and canonical Markdown</h2>
      <p>The following lossless record remains the source used to resume and rebuild indexes.</p>
      <pre>{canonical}</pre>
    </section>

    <footer>
      <span>First-Principles Forge</span>
      <span>Local, traceable reasoning</span>
    </footer>
  </main>
</body>
</html>
"""


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _label(value: str) -> str:
    return value.replace("_", " ").title()


def _finding_list(findings: tuple[str, ...]) -> str:
    return (
        '<ol class="finding-list">'
        + "".join(
            f'<li><span class="finding-index">{index:02d}</span><p>{_escape(finding)}</p></li>'
            for index, finding in enumerate(findings, start=1)
        )
        + "</ol>"
    )


def _item_group(title: str, items: Sequence[EpistemicItem], description: str) -> str:
    cards = "".join(_item_card(item) for item in items)
    if not cards:
        cards = '<p class="empty-state">No items recorded.</p>'
    return f"""<section class="analysis-group">
      <header><h3>{_escape(title)}</h3><p>{_escape(description)}</p></header>
      <div class="item-list">{cards}</div>
    </section>"""


def _item_card(item: EpistemicItem) -> str:
    confidence = item.uncertainty.level.value
    subtype = item.category
    provenance = ""
    trace = ""
    if isinstance(item, Evidence):
        subtype = item.details.evidence_type
        provenance = (
            f'<p class="provenance"><strong>Source:</strong> {_escape(item.provenance.origin)}</p>'
        )
    elif isinstance(item, Premise):
        provenance = f'<p class="provenance"><strong>Origin:</strong> {_escape(item.origin)}</p>'
    elif isinstance(item, DerivedClaim):
        trace = (
            f'<p class="trace"><strong>Depends on:</strong> '
            f"{_escape(', '.join(item.dependencies))}</p>"
        )
    elif isinstance(item, ExploratoryItem):
        subtype = item.exploratory_type.value
        if item.based_on:
            trace = (
                f'<p class="trace"><strong>Based on:</strong> '
                f"{_escape(', '.join(item.based_on))}</p>"
            )
    return f"""<article class="analysis-item">
      <div class="item-meta">
        <span class="item-type">{_escape(_label(subtype))}</span>
        <span class="confidence confidence-{_escape(confidence)}">
        {_escape(confidence.title())} confidence</span>
      </div>
      <h4>{_escape(item.statement)}</h4>
      <p class="rationale">{_escape(item.uncertainty.rationale)}</p>
      {provenance}{trace}
    </article>"""


def _action_section(record: InvestigationRecord) -> str:
    action = record.selected_action
    if action is None:
        body = '<p class="empty-state">No action has been selected.</p>'
    else:
        body = f"""<div class="recommendation-callout">
          <h3>{_escape(action.statement)}</h3>
          <div class="recommendation-grid">
            <div><span>Expected signal</span><p>{_escape(action.expected_observation)}</p></div>
            <div><span>Disconfirming signal</span>
            <p>{_escape(action.disconfirming_observation)}</p></div>
            <div><span>Cost</span><p>{_escape(action.cost)}</p></div>
            <div><span>Risk</span><p>{_escape(action.risk)}</p></div>
          </div>
        </div>"""
    return f"""<section class="report-section recommendation"
      aria-labelledby="recommendation-title">
      <div class="section-heading">
        <div class="section-number">02</div>
        <div><p class="eyebrow">Recommendation</p>
        <h2 id="recommendation-title">What to do next</h2></div>
      </div>{body}
    </section>"""


def _challenge_section(record: InvestigationRecord) -> str:
    challenges = (
        "".join(
            f"""<article class="challenge-card">
          <span>{_escape(challenge.disposition.value.title())}</span>
          <h3>{_escape(challenge.challenge)}</h3>
          <p>{_escape(challenge.rationale)}</p>
        </article>"""
            for challenge in record.skeptical_challenges
        )
        or '<p class="empty-state">No skeptical challenges recorded.</p>'
    )
    return f"""<section class="report-section" aria-labelledby="challenge-title">
      <div class="section-heading"><div class="section-number">04</div>
      <div><p class="eyebrow">Stress test</p>
      <h2 id="challenge-title">Challenges and revisions</h2></div></div>
      <div class="challenge-grid">{challenges}</div>
    </section>"""


def _open_questions_section(record: InvestigationRecord) -> str:
    questions = "".join(f"<li>{_escape(question)}</li>" for question in record.unresolved_questions)
    if not questions:
        questions = "<li>No unresolved questions recorded.</li>"
    return f"""<section class="report-section open-questions"
      aria-labelledby="questions-title">
      <div class="section-heading"><div class="section-number">05</div>
      <div><p class="eyebrow">Open issues</p>
      <h2 id="questions-title">Questions that remain</h2></div></div>
      <ul>{questions}</ul>
    </section>"""


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
