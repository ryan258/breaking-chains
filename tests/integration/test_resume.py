from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from forge.application.orchestrator import InvestigationOrchestrator
from forge.domain.investigation import DepthMode, WorkflowStage, WorkflowStatus
from forge.gateways.fake import DeterministicSpecialistRunner
from forge.gateways.model import ModelRole
from forge.persistence.markdown import MarkdownInvestigationRepository
from forge.persistence.sqlite import SQLiteProjection
from forge.persistence.unit_of_work import InvestigationUnitOfWork


class TickingClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 7, 16, 22, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        self.current += timedelta(seconds=1)
        return self.current


class CrashAfterStageStore:
    def __init__(
        self,
        unit_of_work: InvestigationUnitOfWork,
        crash_stage: WorkflowStage | None = None,
    ) -> None:
        self.unit_of_work = unit_of_work
        self.crash_stage = crash_stage
        self.did_crash = False

    def save(self, record) -> None:
        self.unit_of_work.save(record)
        if record.workflow.stage is self.crash_stage and not self.did_crash:
            self.did_crash = True
            raise RuntimeError("simulated process stop after durable save")

    def load(self, investigation_id: str):
        return self.unit_of_work.load(investigation_id)

    def exists(self, investigation_id: str) -> bool:
        return self.unit_of_work.exists(investigation_id)


def unit_of_work(tmp_path: Path) -> InvestigationUnitOfWork:
    return InvestigationUnitOfWork(
        MarkdownInvestigationRepository(tmp_path / "outputs" / "investigations"),
        SQLiteProjection(tmp_path / "data" / "forge.sqlite3"),
    )


async def choose_a(orchestrator: InvestigationOrchestrator, view):
    return await orchestrator.submit_decision(
        view.record.id,
        prompt_id=view.prompt.id,
        raw_choice="A",
    )


@pytest.mark.asyncio
async def test_pause_restart_and_resume_preserve_prompt_without_repeating_research(
    tmp_path: Path,
) -> None:
    uow = unit_of_work(tmp_path)
    initial_runner = DeterministicSpecialistRunner()
    initial = InvestigationOrchestrator(
        store=CrashAfterStageStore(uow),
        specialists=initial_runner,
        clock=TickingClock(),
        lock_root=tmp_path / "locks",
    )
    focus = await initial.start(
        investigation_id="inv_pause_resume",
        seed="What survives interruption?",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 16, 22, 0, tzinfo=UTC),
    )
    evidence = await choose_a(initial, focus)
    paused = await initial.pause(evidence.record.id)

    restarted_runner = DeterministicSpecialistRunner()
    restarted = InvestigationOrchestrator(
        store=CrashAfterStageStore(uow),
        specialists=restarted_runner,
        clock=TickingClock(),
        lock_root=tmp_path / "locks",
    )
    resumed = await restarted.resume(paused.record.id)
    resumed_again = await restarted.resume(paused.record.id)

    assert paused.record.workflow.status is WorkflowStatus.PAUSED
    assert resumed.record.workflow.status is WorkflowStatus.ACTIVE
    assert resumed.prompt == evidence.prompt
    assert resumed_again.prompt == evidence.prompt
    assert initial_runner.calls == [ModelRole.RESEARCHER]
    assert restarted_runner.calls == []


@pytest.mark.asyncio
async def test_local_continuation_uses_the_saved_live_connection_as_its_basis(
    tmp_path: Path,
) -> None:
    uow = unit_of_work(tmp_path)
    crashing_store = CrashAfterStageStore(uow, WorkflowStage.CONNECTIONS_GENERATED)
    initial = InvestigationOrchestrator(
        store=crashing_store,
        specialists=DeterministicSpecialistRunner(),
        clock=TickingClock(),
        lock_root=tmp_path / "locks",
    )
    focus = await initial.start(
        investigation_id="inv_local_continuation",
        seed="Can saved live work continue locally?",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 16, 22, 0, tzinfo=UTC),
    )
    evidence = await choose_a(initial, focus)

    with pytest.raises(RuntimeError, match="simulated process stop"):
        await choose_a(initial, evidence)

    persisted = uow.load(focus.record.id)
    renamed_items = tuple(
        item.model_copy(update={"id": "epi_live_connection"})
        if item.id == "epi_constraint_connection"
        else item
        for item in persisted.epistemic_items
    )
    uow.save(persisted.model_copy(update={"epistemic_items": renamed_items}))
    pausing = InvestigationOrchestrator(
        store=CrashAfterStageStore(uow),
        specialists=DeterministicSpecialistRunner(),
        clock=TickingClock(),
        lock_root=tmp_path / "locks",
    )
    await pausing.pause(persisted.id)

    local_runner = DeterministicSpecialistRunner()
    continuing = InvestigationOrchestrator(
        store=CrashAfterStageStore(uow),
        specialists=local_runner,
        clock=TickingClock(),
        lock_root=tmp_path / "locks",
    )
    resumed = await continuing.resume(persisted.id)

    assert resumed.record.workflow.stage is WorkflowStage.ACTION_CHECKPOINT
    hypothesis = next(
        item for item in resumed.record.epistemic_items if item.id == "epi_constraint_hypothesis"
    )
    assert hypothesis.based_on == ("epi_live_connection",)
    assert local_runner.calls == [
        ModelRole.SYNTHESIZER,
        ModelRole.SKEPTIC,
        ModelRole.EXPERIMENT_DESIGNER,
    ]


@pytest.mark.parametrize("defer_letter", ["B", "D"])
@pytest.mark.asyncio
async def test_deferred_action_is_reasked_after_resume_instead_of_completing(
    tmp_path: Path,
    defer_letter: str,
) -> None:
    uow = unit_of_work(tmp_path)
    runner = DeterministicSpecialistRunner()
    orchestrator = InvestigationOrchestrator(
        store=CrashAfterStageStore(uow),
        specialists=runner,
        clock=TickingClock(),
        lock_root=tmp_path / "locks",
    )
    focus = await orchestrator.start(
        investigation_id="inv_defer_action",
        seed="Does deferring keep the question open?",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 16, 22, 0, tzinfo=UTC),
    )
    evidence = await choose_a(orchestrator, focus)
    action = await choose_a(orchestrator, evidence)

    deferred = await orchestrator.submit_decision(
        action.record.id,
        prompt_id=action.prompt.id,
        raw_choice=defer_letter,
    )

    assert deferred.record.workflow.status is WorkflowStatus.PAUSED
    assert deferred.record.workflow.stage is WorkflowStage.ACTION_CHECKPOINT

    calls_before_resume = list(runner.calls)
    resumed = await orchestrator.resume(action.record.id)

    assert resumed.record.workflow.status is WorkflowStatus.ACTIVE
    assert resumed.record.workflow.stage is WorkflowStage.ACTION_CHECKPOINT
    assert resumed.prompt == action.prompt
    assert resumed.record.selected_action is not None
    assert runner.calls == calls_before_resume

    completed = await choose_a(orchestrator, resumed)

    assert completed.record.workflow.stage is WorkflowStage.COMPLETED
    assert completed.record.selected_action is not None
    assert runner.calls == calls_before_resume


@pytest.mark.parametrize(
    ("crash_stage", "completed_role"),
    [
        (WorkflowStage.PREMISES_EXTRACTED, ModelRole.RESEARCHER),
        (WorkflowStage.CONNECTIONS_GENERATED, ModelRole.CONNECTION_FINDER),
        (WorkflowStage.HYPOTHESES_SYNTHESIZED, ModelRole.SYNTHESIZER),
        (WorkflowStage.STRESS_TESTED, ModelRole.SKEPTIC),
        (WorkflowStage.ACTIONS_DESIGNED, ModelRole.EXPERIMENT_DESIGNER),
    ],
)
@pytest.mark.asyncio
async def test_restart_never_repeats_a_specialist_for_a_persisted_stage(
    tmp_path: Path,
    crash_stage: WorkflowStage,
    completed_role: ModelRole,
) -> None:
    uow = unit_of_work(tmp_path)
    crashing_store = CrashAfterStageStore(uow, crash_stage)
    initial_runner = DeterministicSpecialistRunner()
    initial = InvestigationOrchestrator(
        store=crashing_store,
        specialists=initial_runner,
        clock=TickingClock(),
        lock_root=tmp_path / "locks",
    )
    focus = await initial.start(
        investigation_id=f"inv_restart_{crash_stage.value}",
        seed="Which completed work should survive?",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 16, 22, 0, tzinfo=UTC),
    )

    with pytest.raises(RuntimeError, match="simulated process stop"):
        if crash_stage is WorkflowStage.PREMISES_EXTRACTED:
            await choose_a(initial, focus)
        else:
            evidence = await choose_a(initial, focus)
            await choose_a(initial, evidence)

    persisted = uow.load(focus.record.id)
    assert persisted.workflow.stage is crash_stage

    restarted_runner = DeterministicSpecialistRunner()
    restarted = InvestigationOrchestrator(
        store=CrashAfterStageStore(uow),
        specialists=restarted_runner,
        clock=TickingClock(),
        lock_root=tmp_path / "locks",
    )
    await restarted.run_until_checkpoint(focus.record.id)

    assert initial_runner.calls.count(completed_role) == 1
    assert completed_role not in restarted_runner.calls
