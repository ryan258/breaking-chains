"""Presentation-only views derived from canonical investigation records."""

import re
from dataclasses import dataclass

from forge.domain.epistemics import group_epistemic_items
from forge.domain.investigation import WorkflowStage
from forge.persistence.markdown import key_findings
from forge.persistence.metadata import InvestigationRecord

_STAGES = (
    WorkflowStage.SEEDED,
    WorkflowStage.SOURCE_CONSENT,
    WorkflowStage.FOCUS_CHECKPOINT,
    WorkflowStage.PREMISES_EXTRACTED,
    WorkflowStage.EVIDENCE_CHECKPOINT,
    WorkflowStage.CONNECTIONS_GENERATED,
    WorkflowStage.HYPOTHESES_SYNTHESIZED,
    WorkflowStage.STRESS_TESTED,
    WorkflowStage.ACTIONS_DESIGNED,
    WorkflowStage.ACTION_CHECKPOINT,
    WorkflowStage.COMPLETED,
)


@dataclass(frozen=True, slots=True)
class ReviewSection:
    title: str
    lines: tuple[str, ...]


def completed_stage_labels(record: InvestigationRecord) -> tuple[str, ...]:
    """Return an ordered, readable account of persisted workflow progress."""

    reached = {event.to_stage for event in record.workflow.history}
    reached.add(WorkflowStage.SEEDED)
    return tuple(stage.value.replace("_", " ").title() for stage in _STAGES if stage in reached)


def markdown_heading_text(value: str) -> str:
    """Render untrusted text literally inside a one-line Markdown heading."""

    normalized = " ".join(value.splitlines())
    return re.sub(r"([!\"#$%&'()*+,\-./:;<=>?@[\\\]^_`{|}~])", r"\\\1", normalized)


def review_sections(record: InvestigationRecord) -> tuple[ReviewSection, ...]:
    """Group canonical content for concise, non-authoritative UI review panels."""

    def item_line(item) -> str:
        return (
            f"{item.statement} — Confidence: {item.uncertainty.level.value} "
            f"({item.uncertainty.rationale})"
        )

    groups = group_epistemic_items(record.epistemic_items)
    premises = tuple(item_line(item) for item in groups.premises)
    evidence = tuple(item_line(item) for item in groups.evidence)
    claims = tuple(item_line(item) for item in groups.claims)
    exploratory = tuple(item_line(item) for item in groups.exploratory)
    challenges = tuple(
        f"{item.disposition.value.title()}: {item.challenge}"
        for item in record.skeptical_challenges
    )
    action = (record.selected_action.statement,) if record.selected_action is not None else ()
    return (
        ReviewSection("Findings", key_findings(record)),
        ReviewSection("Premises", premises),
        ReviewSection("Evidence", evidence),
        ReviewSection("Derived claims", claims),
        ReviewSection("Connections and hypotheses", exploratory),
        ReviewSection("Skeptical challenges", challenges),
        ReviewSection("Proposed action", action),
    )


__all__ = [
    "ReviewSection",
    "completed_stage_labels",
    "markdown_heading_text",
    "review_sections",
]
