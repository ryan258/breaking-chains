from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from forge.domain.investigation import (
    DepthMode,
    InvestigationWorkflow,
    WorkflowEventKind,
    WorkflowStage,
    WorkflowStatus,
)

STARTED = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)


def test_new_investigation_starts_seeded_and_active() -> None:
    investigation = InvestigationWorkflow.start(depth=DepthMode.STANDARD, at=STARTED)

    assert investigation.stage is WorkflowStage.SEEDED
    assert investigation.status is WorkflowStatus.ACTIVE
    assert investigation.depth is DepthMode.STANDARD
    assert investigation.created_at == STARTED
    assert investigation.updated_at == STARTED
    assert investigation.history == ()


def test_legal_transition_returns_new_state_with_timestamped_history() -> None:
    investigation = InvestigationWorkflow.start(depth=DepthMode.QUICK, at=STARTED)
    transitioned_at = STARTED + timedelta(minutes=1)

    advanced = investigation.advance(WorkflowStage.SOURCE_CONSENT, at=transitioned_at)

    assert investigation.stage is WorkflowStage.SEEDED
    assert investigation.history == ()
    assert advanced.stage is WorkflowStage.SOURCE_CONSENT
    assert advanced.updated_at == transitioned_at
    assert advanced.history[-1].kind is WorkflowEventKind.TRANSITIONED
    assert advanced.history[-1].from_stage is WorkflowStage.SEEDED
    assert advanced.history[-1].to_stage is WorkflowStage.SOURCE_CONSENT
    assert advanced.history[-1].occurred_at == transitioned_at


def test_seed_can_skip_source_consent_when_no_local_material_will_leave() -> None:
    investigation = InvestigationWorkflow.start(depth=DepthMode.STANDARD, at=STARTED)

    advanced = investigation.advance(WorkflowStage.FOCUS_CHECKPOINT, at=STARTED)

    assert advanced.stage is WorkflowStage.FOCUS_CHECKPOINT


def test_illegal_transition_raises_without_mutating_state() -> None:
    investigation = InvestigationWorkflow.start(depth=DepthMode.STANDARD, at=STARTED)

    with pytest.raises(ValueError, match="illegal workflow transition"):
        investigation.advance(WorkflowStage.HYPOTHESES_SYNTHESIZED, at=STARTED)

    assert investigation.stage is WorkflowStage.SEEDED
    assert investigation.history == ()


def test_pause_and_resume_preserve_stage_and_record_history() -> None:
    investigation = InvestigationWorkflow.start(depth=DepthMode.DEEP, at=STARTED)
    paused_at = STARTED + timedelta(minutes=1)
    resumed_at = STARTED + timedelta(minutes=2)

    paused = investigation.pause(at=paused_at)
    resumed = paused.resume(at=resumed_at)

    assert paused.stage is WorkflowStage.SEEDED
    assert paused.status is WorkflowStatus.PAUSED
    assert paused.history[-1].kind is WorkflowEventKind.PAUSED
    assert resumed.stage is WorkflowStage.SEEDED
    assert resumed.status is WorkflowStatus.ACTIVE
    assert resumed.history[-1].kind is WorkflowEventKind.RESUMED
    assert resumed.updated_at == resumed_at


def test_paused_investigation_cannot_advance() -> None:
    investigation = InvestigationWorkflow.start(depth=DepthMode.STANDARD, at=STARTED).pause(
        at=STARTED
    )

    with pytest.raises(ValueError, match="resume the investigation before advancing"):
        investigation.advance(WorkflowStage.FOCUS_CHECKPOINT, at=STARTED)


def test_pause_and_resume_reject_duplicate_actions_without_mutating_state() -> None:
    active = InvestigationWorkflow.start(depth=DepthMode.STANDARD, at=STARTED)
    paused = active.pause(at=STARTED)

    with pytest.raises(ValueError, match="already active"):
        active.resume(at=STARTED)
    with pytest.raises(ValueError, match="already paused"):
        paused.pause(at=STARTED)

    assert active.history == ()
    assert len(paused.history) == 1


def test_events_require_timezone_aware_monotonic_timestamps() -> None:
    investigation = InvestigationWorkflow.start(depth=DepthMode.STANDARD, at=STARTED)

    with pytest.raises(ValueError, match="timezone-aware"):
        investigation.pause(at=datetime(2026, 7, 16, 12, 1))
    with pytest.raises(ValueError, match="cannot be earlier"):
        investigation.pause(at=STARTED - timedelta(seconds=1))


def test_deserialization_rejects_state_that_disagrees_with_history() -> None:
    investigation = InvestigationWorkflow.start(depth=DepthMode.STANDARD, at=STARTED).advance(
        WorkflowStage.FOCUS_CHECKPOINT,
        at=STARTED + timedelta(minutes=1),
    )
    payload = investigation.model_dump()
    payload["stage"] = WorkflowStage.HYPOTHESES_SYNTHESIZED

    with pytest.raises(ValidationError, match="history does not lead to the stored stage"):
        InvestigationWorkflow.model_validate(payload)


def test_deserialization_rejects_out_of_order_history_timestamps() -> None:
    investigation = InvestigationWorkflow.start(depth=DepthMode.STANDARD, at=STARTED)
    investigation = investigation.pause(at=STARTED + timedelta(minutes=2))
    investigation = investigation.resume(at=STARTED + timedelta(minutes=3))
    payload = investigation.model_dump()
    payload["history"][0]["occurred_at"] = STARTED + timedelta(minutes=4)

    with pytest.raises(ValidationError, match="history timestamps must be monotonic"):
        InvestigationWorkflow.model_validate(payload)


def test_full_workflow_reaches_completed_in_order() -> None:
    investigation = InvestigationWorkflow.start(depth=DepthMode.STANDARD, at=STARTED)
    stages = (
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

    for index, stage in enumerate(stages, start=1):
        investigation = investigation.advance(stage, at=STARTED + timedelta(minutes=index))

    assert investigation.stage is WorkflowStage.COMPLETED
    assert len(investigation.history) == len(stages)


def test_completed_investigation_cannot_advance() -> None:
    investigation = InvestigationWorkflow.start(depth=DepthMode.STANDARD, at=STARTED)
    for stage in (
        WorkflowStage.FOCUS_CHECKPOINT,
        WorkflowStage.PREMISES_EXTRACTED,
        WorkflowStage.EVIDENCE_CHECKPOINT,
        WorkflowStage.CONNECTIONS_GENERATED,
        WorkflowStage.HYPOTHESES_SYNTHESIZED,
        WorkflowStage.STRESS_TESTED,
        WorkflowStage.ACTIONS_DESIGNED,
        WorkflowStage.ACTION_CHECKPOINT,
        WorkflowStage.COMPLETED,
    ):
        investigation = investigation.advance(stage, at=STARTED)

    with pytest.raises(ValueError, match="illegal workflow transition"):
        investigation.advance(WorkflowStage.SEEDED, at=STARTED)
