"""Versioned, validated content stored in canonical investigation records."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

from forge.application.decisions import DecisionAttempt, DecisionKind, DecisionPrompt
from forge.domain.epistemics import EpistemicItem
from forge.domain.identifiers import EpistemicItemId, InvestigationId
from forge.domain.investigation import InvestigationWorkflow, WorkflowStage

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
OptionalText = NonEmptyText | None
Sha256Digest = Annotated[
    str,
    StringConstraints(to_lower=True, pattern=r"^[a-f0-9]{64}$"),
]


class MetadataModel(BaseModel):
    """Immutable strict value used in the canonical metadata block."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class LocalSourceReference(MetadataModel):
    """Inspectable local source identity without embedding its contents."""

    path: NonEmptyText
    sha256: Sha256Digest
    locator: OptionalText = None

    @field_validator("path", "locator")
    @classmethod
    def reject_control_characters(cls, value: str | None) -> str | None:
        if value is not None and any(character in value for character in ("\x00", "\n", "\r")):
            raise ValueError("source locations cannot contain control characters")
        return value


class ChallengeDisposition(StrEnum):
    """Outcome of a skeptical challenge."""

    RETAIN = "retain"
    REVISE = "revise"
    REJECT = "reject"


class SkepticalChallenge(MetadataModel):
    """A challenge and its explicit effect on an exploratory item."""

    target_id: EpistemicItemId
    challenge: NonEmptyText
    disposition: ChallengeDisposition
    rationale: NonEmptyText


class ActionProposal(MetadataModel):
    """The smallest informative test or practical next action."""

    statement: NonEmptyText
    expected_observation: NonEmptyText
    disconfirming_observation: NonEmptyText
    cost: NonEmptyText
    risk: NonEmptyText
    stopping_condition: NonEmptyText


class InvestigationRecord(MetadataModel):
    """Complete intellectual and workflow content for one investigation."""

    schema_version: Literal[1] = 1
    id: InvestigationId
    seed: NonEmptyText
    selected_focus: OptionalText = None
    workflow: InvestigationWorkflow
    epistemic_items: tuple[EpistemicItem, ...] = ()
    decisions: tuple[DecisionAttempt, ...] = ()
    pending_decision: DecisionPrompt | None = None
    source_references: tuple[LocalSourceReference, ...] = ()
    skeptical_challenges: tuple[SkepticalChallenge, ...] = ()
    selected_action: ActionProposal | None = None
    unresolved_questions: tuple[NonEmptyText, ...] = ()

    @model_validator(mode="after")
    def validate_canonical_record(self) -> "InvestigationRecord":
        expected_decision = {
            WorkflowStage.FOCUS_CHECKPOINT: DecisionKind.FOCUS_CHECKPOINT,
            WorkflowStage.EVIDENCE_CHECKPOINT: DecisionKind.EVIDENCE_CHECKPOINT,
            WorkflowStage.ACTION_CHECKPOINT: DecisionKind.ACTION_CHECKPOINT,
        }.get(self.workflow.stage)
        if (
            self.pending_decision is not None
            and self.pending_decision.kind is not expected_decision
        ):
            raise ValueError("pending decision does not match the current workflow stage")
        item_ids = tuple(item.id for item in self.epistemic_items)
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("epistemic item identifiers must be unique within a record")
        for item in self.epistemic_items:
            if any(
                (link.target_investigation_id or self.id) == self.id and link.target_id == item.id
                for link in item.links
            ):
                raise ValueError("an epistemic item cannot link to itself")
        challenge_targets = {challenge.target_id for challenge in self.skeptical_challenges}
        if not challenge_targets.issubset(item_ids):
            raise ValueError("skeptical challenges must target an item in the record")
        return self


__all__ = [
    "ActionProposal",
    "ChallengeDisposition",
    "InvestigationId",
    "InvestigationRecord",
    "LocalSourceReference",
    "SkepticalChallenge",
]
