"""Versioned, validated content stored in canonical investigation records."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from forge.application.decisions import ChoiceLetter, DecisionAttempt, DecisionKind, DecisionPrompt
from forge.domain.epistemics import (
    DerivedClaim,
    EpistemicItem,
    ExploratoryItem,
    NonEmptyText,
    OptionalText,
)
from forge.domain.identifiers import EpistemicItemId, InvestigationId
from forge.domain.investigation import InvestigationWorkflow, WorkflowStage
from forge.gateways.model import ModelReceipt

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
    procedure: OptionalText = None
    expected_observation: NonEmptyText
    disconfirming_observation: NonEmptyText
    cost: NonEmptyText
    risk: NonEmptyText
    stopping_condition: NonEmptyText
    reproducibility_needs: OptionalText = None


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
    prior_investigation_ids: tuple[InvestigationId, ...] = ()
    source_transmission_approved: bool = False
    live_execution_approved: bool = False
    model_receipts: tuple[ModelReceipt, ...] = ()
    skeptical_challenges: tuple[SkepticalChallenge, ...] = ()
    skeptical_revision_cycles: int = Field(default=0, ge=0)
    selected_action: ActionProposal | None = None
    unresolved_questions: tuple[NonEmptyText, ...] = ()

    @model_validator(mode="after")
    def validate_canonical_record(self) -> "InvestigationRecord":
        expected_decision = {
            WorkflowStage.SOURCE_CONSENT: DecisionKind.SOURCE_CONSENT,
            WorkflowStage.FOCUS_CHECKPOINT: DecisionKind.FOCUS_CHECKPOINT,
            WorkflowStage.EVIDENCE_CHECKPOINT: DecisionKind.EVIDENCE_CHECKPOINT,
            WorkflowStage.ACTION_CHECKPOINT: DecisionKind.ACTION_CHECKPOINT,
        }.get(self.workflow.stage)
        if (
            self.pending_decision is not None
            and self.pending_decision.kind
            not in {DecisionKind.RECOVERY, DecisionKind.BUDGET_EXHAUSTED}
            and self.pending_decision.kind is not expected_decision
        ):
            raise ValueError("pending decision does not match the current workflow stage")
        if self.source_transmission_approved:
            recorded_approval = any(
                decision.prompt.kind is DecisionKind.SOURCE_CONSENT
                and decision.selection is not None
                and decision.selection.letter is ChoiceLetter.A
                for decision in self.decisions
            )
            if not self.source_references or not recorded_approval:
                raise ValueError("source transmission requires a recorded A approval")
        if self.live_execution_approved:
            recorded_live_approval = any(
                decision.prompt.kind is DecisionKind.LIVE_CONFIRMATION
                and decision.selection is not None
                and decision.selection.letter is ChoiceLetter.A
                for decision in self.decisions
            )
            if not recorded_live_approval:
                raise ValueError("live execution requires a recorded A approval")
        if self.model_receipts and not self.live_execution_approved:
            raise ValueError("model receipts require approved live execution")
        item_ids = tuple(item.id for item in self.epistemic_items)
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("epistemic item identifiers must be unique within a record")
        item_id_set = set(item_ids)
        for item in self.epistemic_items:
            for link in item.links:
                target_investigation_id = link.target_investigation_id or self.id
                if target_investigation_id == self.id and link.target_id == item.id:
                    raise ValueError("an epistemic item cannot link to itself")
                if target_investigation_id == self.id and link.target_id not in item_id_set:
                    raise ValueError("relationship references an unknown local epistemic item")
            local_references: tuple[EpistemicItemId, ...] = ()
            if isinstance(item, DerivedClaim):
                local_references = item.dependencies
            elif isinstance(item, ExploratoryItem):
                local_references = item.based_on
            if not set(local_references).issubset(item_id_set):
                raise ValueError("item references an unknown local epistemic item")
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
