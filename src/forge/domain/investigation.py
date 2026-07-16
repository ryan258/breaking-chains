"""Immutable investigation workflow and legal state transitions."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class WorkflowModel(BaseModel):
    """Shared immutable workflow value configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class DepthMode(StrEnum):
    """Investigation breadth and effort level."""

    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class WorkflowStage(StrEnum):
    """Persisted stages in the investigation lifecycle."""

    SEEDED = "seeded"
    SOURCE_CONSENT = "source_consent"
    FOCUS_CHECKPOINT = "focus_checkpoint"
    PREMISES_EXTRACTED = "premises_extracted"
    EVIDENCE_CHECKPOINT = "evidence_checkpoint"
    CONNECTIONS_GENERATED = "connections_generated"
    HYPOTHESES_SYNTHESIZED = "hypotheses_synthesized"
    STRESS_TESTED = "stress_tested"
    ACTIONS_DESIGNED = "actions_designed"
    ACTION_CHECKPOINT = "action_checkpoint"
    COMPLETED = "completed"


class WorkflowStatus(StrEnum):
    """Whether orchestration may currently advance the workflow."""

    ACTIVE = "active"
    PAUSED = "paused"


class WorkflowEventKind(StrEnum):
    """Auditable kinds of workflow state change."""

    TRANSITIONED = "transitioned"
    PAUSED = "paused"
    RESUMED = "resumed"


class WorkflowEvent(WorkflowModel):
    """One timestamped workflow state change."""

    kind: WorkflowEventKind
    from_stage: WorkflowStage
    to_stage: WorkflowStage
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("workflow timestamps must be timezone-aware")
        return value


LEGAL_TRANSITIONS: dict[WorkflowStage, frozenset[WorkflowStage]] = {
    WorkflowStage.SEEDED: frozenset({WorkflowStage.SOURCE_CONSENT, WorkflowStage.FOCUS_CHECKPOINT}),
    WorkflowStage.SOURCE_CONSENT: frozenset({WorkflowStage.FOCUS_CHECKPOINT}),
    WorkflowStage.FOCUS_CHECKPOINT: frozenset({WorkflowStage.PREMISES_EXTRACTED}),
    WorkflowStage.PREMISES_EXTRACTED: frozenset({WorkflowStage.EVIDENCE_CHECKPOINT}),
    WorkflowStage.EVIDENCE_CHECKPOINT: frozenset({WorkflowStage.CONNECTIONS_GENERATED}),
    WorkflowStage.CONNECTIONS_GENERATED: frozenset({WorkflowStage.HYPOTHESES_SYNTHESIZED}),
    WorkflowStage.HYPOTHESES_SYNTHESIZED: frozenset({WorkflowStage.STRESS_TESTED}),
    WorkflowStage.STRESS_TESTED: frozenset({WorkflowStage.ACTIONS_DESIGNED}),
    WorkflowStage.ACTIONS_DESIGNED: frozenset({WorkflowStage.ACTION_CHECKPOINT}),
    WorkflowStage.ACTION_CHECKPOINT: frozenset({WorkflowStage.COMPLETED}),
    WorkflowStage.COMPLETED: frozenset(),
}


class InvestigationWorkflow(WorkflowModel):
    """Current state and complete transition history for an investigation."""

    depth: DepthMode
    stage: WorkflowStage
    status: WorkflowStatus
    created_at: datetime
    updated_at: datetime
    history: tuple[WorkflowEvent, ...] = ()

    @field_validator("created_at", "updated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("workflow timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_current_timestamps(self) -> "InvestigationWorkflow":
        if self.updated_at < self.created_at:
            raise ValueError("updated timestamp cannot be earlier than creation")
        if self.history and self.history[-1].occurred_at != self.updated_at:
            raise ValueError("updated timestamp must match the latest workflow event")
        if not self.history and self.updated_at != self.created_at:
            raise ValueError("a workflow without history cannot have a later update timestamp")
        self._validate_history()
        return self

    def _validate_history(self) -> None:
        stage = WorkflowStage.SEEDED
        status = WorkflowStatus.ACTIVE
        previous_time = self.created_at

        for event in self.history:
            if event.occurred_at < previous_time:
                raise ValueError("workflow history timestamps must be monotonic")
            if event.from_stage is not stage:
                raise ValueError("workflow history contains a disconnected event")

            if event.kind is WorkflowEventKind.TRANSITIONED:
                if (
                    status is WorkflowStatus.PAUSED
                    or event.to_stage not in LEGAL_TRANSITIONS[stage]
                ):
                    raise ValueError("workflow history contains an illegal transition")
                stage = event.to_stage
            elif event.kind is WorkflowEventKind.PAUSED:
                if status is WorkflowStatus.PAUSED or event.to_stage is not stage:
                    raise ValueError("workflow history contains an illegal pause")
                status = WorkflowStatus.PAUSED
            else:
                if status is WorkflowStatus.ACTIVE or event.to_stage is not stage:
                    raise ValueError("workflow history contains an illegal resume")
                status = WorkflowStatus.ACTIVE

            previous_time = event.occurred_at

        if stage is not self.stage:
            raise ValueError("workflow history does not lead to the stored stage")
        if status is not self.status:
            raise ValueError("workflow history does not lead to the stored status")

    @classmethod
    def start(cls, *, depth: DepthMode, at: datetime) -> "InvestigationWorkflow":
        """Create a seeded active workflow at a caller-supplied stable time."""

        return cls(
            depth=depth,
            stage=WorkflowStage.SEEDED,
            status=WorkflowStatus.ACTIVE,
            created_at=at,
            updated_at=at,
        )

    def advance(self, to_stage: WorkflowStage, *, at: datetime) -> "InvestigationWorkflow":
        """Move to a legal next stage without mutating the prior state."""

        if self.status is WorkflowStatus.PAUSED:
            raise ValueError("resume the investigation before advancing")
        if to_stage not in LEGAL_TRANSITIONS[self.stage]:
            raise ValueError(f"illegal workflow transition: {self.stage} to {to_stage}")
        return self._record(
            kind=WorkflowEventKind.TRANSITIONED,
            to_stage=to_stage,
            status=self.status,
            at=at,
        )

    def pause(self, *, at: datetime) -> "InvestigationWorkflow":
        """Pause work while preserving the exact current stage."""

        if self.status is WorkflowStatus.PAUSED:
            raise ValueError("investigation is already paused")
        return self._record(
            kind=WorkflowEventKind.PAUSED,
            to_stage=self.stage,
            status=WorkflowStatus.PAUSED,
            at=at,
        )

    def resume(self, *, at: datetime) -> "InvestigationWorkflow":
        """Resume work from the preserved current stage."""

        if self.status is WorkflowStatus.ACTIVE:
            raise ValueError("investigation is already active")
        return self._record(
            kind=WorkflowEventKind.RESUMED,
            to_stage=self.stage,
            status=WorkflowStatus.ACTIVE,
            at=at,
        )

    def _record(
        self,
        *,
        kind: WorkflowEventKind,
        to_stage: WorkflowStage,
        status: WorkflowStatus,
        at: datetime,
    ) -> "InvestigationWorkflow":
        event = WorkflowEvent(
            kind=kind,
            from_stage=self.stage,
            to_stage=to_stage,
            occurred_at=at,
        )
        if at < self.updated_at:
            raise ValueError("workflow event timestamp cannot be earlier than the current state")
        return self.model_copy(
            update={
                "stage": to_stage,
                "status": status,
                "updated_at": at,
                "history": (*self.history, event),
            }
        )


__all__ = [
    "DepthMode",
    "InvestigationWorkflow",
    "LEGAL_TRANSITIONS",
    "WorkflowEvent",
    "WorkflowEventKind",
    "WorkflowStage",
    "WorkflowStatus",
]
