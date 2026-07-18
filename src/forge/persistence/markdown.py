"""Human-readable canonical Markdown repository with lossless metadata."""

import html
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from forge.domain.epistemics import DerivedClaim, EpistemicItem, Evidence, ExploratoryItem, Premise
from forge.domain.identifiers import InvestigationId
from forge.persistence.metadata import InvestigationRecord

_METADATA_HEADER = "<!-- forge-record:begin v1 -->\n```json\n"
_METADATA_FOOTER = "\n```\n<!-- forge-record:end -->\n"
_MAX_RECORD_BYTES = 10 * 1024 * 1024
_INVESTIGATION_ID_ADAPTER = TypeAdapter(InvestigationId)


class RecordFormatError(ValueError):
    """A canonical record is missing, unsupported, or invalid."""


class MarkdownInvestigationRepository:
    """Store complete investigations as atomic canonical Markdown files."""

    def __init__(self, root: Path, *, max_record_bytes: int = _MAX_RECORD_BYTES) -> None:
        if max_record_bytes < 1:
            raise ValueError("max_record_bytes must be positive")
        self.root = root
        self.max_record_bytes = max_record_bytes

    def save(self, record: InvestigationRecord) -> Path:
        """Atomically replace a record only after fully rendering it."""

        try:
            validated_record = InvestigationRecord.model_validate(record.model_dump(mode="python"))
        except ValidationError:
            raise RecordFormatError("invalid investigation record") from None
        rendered_bytes = render_record(validated_record).encode("utf-8")
        if len(rendered_bytes) > self.max_record_bytes:
            raise RecordFormatError("investigation record exceeds the configured size limit")

        self.root.mkdir(parents=True, exist_ok=True)
        target = self._target(validated_record.id)
        _reject_symbolic_link(target)
        temporary_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=self.root,
                prefix=f".{validated_record.id}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(rendered_bytes)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, target)
            _sync_directory(self.root)
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise

        return target

    def load(self, investigation_id: str) -> InvestigationRecord:
        """Load and validate the complete machine-readable record boundary."""

        target = self._target(investigation_id)
        _reject_symbolic_link(target)
        with target.open("rb") as record_file:
            record_bytes = record_file.read(self.max_record_bytes + 1)
        if len(record_bytes) > self.max_record_bytes:
            raise RecordFormatError("investigation record exceeds the configured size limit")
        try:
            text = record_bytes.decode("utf-8")
        except UnicodeDecodeError:
            raise RecordFormatError("investigation record is not valid UTF-8") from None
        return parse_record(text)

    def exists(self, investigation_id: str) -> bool:
        """Return whether a canonical record exists for a validated identifier."""

        target = self._target(investigation_id)
        _reject_symbolic_link(target)
        return target.is_file()

    def list_records(self) -> tuple[InvestigationRecord, ...]:
        """Load every canonical record in deterministic identifier order."""

        if not self.root.exists():
            return ()
        records = []
        for path in sorted(self.root.glob("inv_*.md")):
            if path.is_symlink():
                raise RecordFormatError("canonical record cannot be a symbolic link")
            records.append(self.load(path.stem))
        return tuple(records)

    def _target(self, investigation_id: str) -> Path:
        try:
            safe_id = _INVESTIGATION_ID_ADAPTER.validate_python(investigation_id)
        except ValidationError:
            raise RecordFormatError("invalid investigation identifier") from None
        return self.root / f"{safe_id}.md"


def render_record(record: InvestigationRecord) -> str:
    """Render a readable report followed by the lossless versioned record."""

    premises = [item for item in record.epistemic_items if isinstance(item, Premise)]
    evidence = [item for item in record.epistemic_items if isinstance(item, Evidence)]
    claims = [item for item in record.epistemic_items if isinstance(item, DerivedClaim)]
    exploratory = [item for item in record.epistemic_items if isinstance(item, ExploratoryItem)]

    lines = [
        f"# Investigation: {_markdown_text(record.seed)}",
        "",
        "## Overview",
        "",
        f"- **ID:** {_markdown_text(record.id)}",
        f"- **Stage:** {record.workflow.stage.value}",
        f"- **Status:** {record.workflow.status.value}",
        f"- **Depth:** {record.workflow.depth.value}",
        f"- **Created:** {record.workflow.created_at.isoformat()}",
        f"- **Updated:** {record.workflow.updated_at.isoformat()}",
        f"- **Selected focus:** {_markdown_text(record.selected_focus or 'Not selected yet')}",
        "- **Prior investigations:** " + (", ".join(record.prior_investigation_ids) or "None"),
        "",
        "## Local source references",
        "",
        *_source_lines(record),
        "",
        "## Premises",
        "",
        *_epistemic_lines(premises),
        "",
        "## Evidence",
        "",
        *_epistemic_lines(evidence),
        "",
        "## Derived claims",
        "",
        *_epistemic_lines(claims),
        "",
        "## Connections and hypotheses",
        "",
        *_epistemic_lines(exploratory),
        "",
        "## Skeptical challenges",
        "",
        *_challenge_lines(record),
        "",
        "## Selected action",
        "",
        *_action_lines(record),
        "",
        "## Unresolved questions",
        "",
        *(_bullet_lines(record.unresolved_questions)),
        "",
        "## Decisions",
        "",
        *_decision_lines(record),
        "",
        "## Workflow history",
        "",
        *_history_lines(record),
        "",
        "## Machine-readable record",
        "",
        "This versioned block is the canonical data used to resume and rebuild indexes.",
        "",
        _METADATA_HEADER.rstrip("\n"),
        record.model_dump_json(indent=2),
        _METADATA_FOOTER.rstrip("\n"),
        "",
    ]
    return "\n".join(lines)


def parse_record(text: str) -> InvestigationRecord:
    """Extract and validate the final anchored canonical metadata block."""

    if not text.endswith(_METADATA_FOOTER):
        raise RecordFormatError("canonical metadata block is missing or unsupported")
    header_index = text.rfind(_METADATA_HEADER)
    if header_index < 0:
        raise RecordFormatError("canonical metadata block is missing or unsupported")
    json_start = header_index + len(_METADATA_HEADER)
    json_end = len(text) - len(_METADATA_FOOTER)
    try:
        return InvestigationRecord.model_validate_json(text[json_start:json_end])
    except ValidationError:
        raise RecordFormatError("canonical metadata block is invalid") from None


def _epistemic_lines(items: Iterable[EpistemicItem]) -> list[str]:
    lines: list[str] = []
    for item in items:
        subtype = ""
        if isinstance(item, Evidence):
            subtype = f" / {item.details.evidence_type}"
        elif isinstance(item, ExploratoryItem):
            subtype = f" / {item.exploratory_type.value}"
        lines.extend(
            (
                f"- **{_markdown_text(item.id)}** `{item.category}{subtype}` — "
                f"{_markdown_text(item.statement)}",
                f"  - Confidence: {item.uncertainty.level.value} — "
                f"{_markdown_text(item.uncertainty.rationale)}",
            )
        )
        if isinstance(item, Evidence):
            lines.extend(_provenance_lines(item.provenance.origin, item.provenance.locator))
            for field_name, value in item.details.model_dump(mode="json").items():
                if field_name != "evidence_type" and value is not None:
                    label = field_name.replace("_", " ").title()
                    lines.append(f"  - {label}: {_markdown_text(str(value))}")
        elif isinstance(item, Premise):
            lines.append(f"  - Origin: {_markdown_text(item.origin)}")
        if isinstance(item, DerivedClaim):
            lines.extend(_provenance_lines(item.provenance.origin, item.provenance.locator))
            lines.append(f"  - Dependencies: {', '.join(item.dependencies)}")
            lines.append(f"  - Derivation: {_markdown_text(item.derivation)}")
        elif isinstance(item, ExploratoryItem):
            lines.extend(_provenance_lines(item.provenance.origin, item.provenance.locator))
            if item.based_on:
                lines.append(f"  - Based on: {', '.join(item.based_on)}")
        if item.links:
            rendered_links = ", ".join(
                f"{link.kind.value} "
                f"{f'{link.target_investigation_id}/' if link.target_investigation_id else ''}"
                f"{link.target_id}"
                for link in item.links
            )
            lines.append(f"  - Relationships: {_markdown_text(rendered_links)}")
    return lines or ["- None recorded."]


def _source_lines(record: InvestigationRecord) -> list[str]:
    if not record.source_references:
        return ["- None recorded."]
    return [
        "- **Transmission approved:** " + ("yes" if record.source_transmission_approved else "no"),
        *[
            f"- **Path:** {_markdown_text(source.path)} — **SHA-256:** {source.sha256}"
            + (f" — **Location:** {_markdown_text(source.locator)}" if source.locator else "")
            for source in record.source_references
        ],
    ]


def _challenge_lines(record: InvestigationRecord) -> list[str]:
    if not record.skeptical_challenges:
        return ["- None recorded."]
    return [
        f"- **{challenge.disposition.value.title()} {challenge.target_id}:** "
        f"{_markdown_text(challenge.challenge)} — {_markdown_text(challenge.rationale)}"
        for challenge in record.skeptical_challenges
    ]


def _action_lines(record: InvestigationRecord) -> list[str]:
    action = record.selected_action
    if action is None:
        return ["- None selected."]
    lines = [
        f"- **Action:** {_markdown_text(action.statement)}",
    ]
    if action.procedure is not None:
        lines.append(f"- **Procedure:** {_markdown_text(action.procedure)}")
    lines.extend(
        [
            f"- **Expected:** {_markdown_text(action.expected_observation)}",
            f"- **Disconfirming:** {_markdown_text(action.disconfirming_observation)}",
            f"- **Cost:** {_markdown_text(action.cost)}",
            f"- **Risk:** {_markdown_text(action.risk)}",
            f"- **Stop when:** {_markdown_text(action.stopping_condition)}",
        ]
    )
    if action.reproducibility_needs is not None:
        lines.append(f"- **Reproducibility:** {_markdown_text(action.reproducibility_needs)}")
    return lines


def _decision_lines(record: InvestigationRecord) -> list[str]:
    if not record.decisions:
        return ["- None recorded."]
    lines = []
    for attempt in record.decisions:
        if attempt.selection is not None:
            answer = attempt.custom_answer or attempt.selection.label
            lines.append(
                f"- **{attempt.prompt.kind.value}: {attempt.selection.letter.value}** — "
                f"{_markdown_text(answer)}"
            )
        else:
            lines.append(
                f"- **{attempt.prompt.kind.value}: invalid** — {_markdown_text(attempt.error)}"
            )
    return lines


def _history_lines(record: InvestigationRecord) -> list[str]:
    if not record.workflow.history:
        return ["- No state changes recorded."]
    return [
        f"- {event.occurred_at.isoformat()} — {event.kind.value}: "
        f"{event.from_stage.value} → {event.to_stage.value}"
        for event in record.workflow.history
    ]


def _bullet_lines(values: Iterable[str]) -> list[str]:
    lines = [f"- {_markdown_text(value)}" for value in values]
    return lines or ["- None recorded."]


def _markdown_text(value: str | None) -> str:
    escaped = html.escape(value or "", quote=False)
    for character in ("\\", "`", "[", "]", "(", ")"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped.replace("\n", "\n    ")


def _provenance_lines(origin: str, locator: str | None) -> list[str]:
    location = f" — {_markdown_text(locator)}" if locator else ""
    return [f"  - Provenance: {_markdown_text(origin)}{location}"]


def _sync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _reject_symbolic_link(path: Path) -> None:
    if path.is_symlink():
        raise RecordFormatError("canonical record cannot be a symbolic link")


__all__ = [
    "MarkdownInvestigationRepository",
    "RecordFormatError",
    "parse_record",
    "render_record",
]
