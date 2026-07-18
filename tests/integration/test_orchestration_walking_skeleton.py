import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from forge.application.decisions import ChoiceLetter
from forge.application.orchestrator import InvestigationOrchestrator
from forge.domain.investigation import DepthMode, WorkflowStage, WorkflowStatus
from forge.gateways.fake import DeterministicSpecialistRunner
from forge.gateways.model import ModelRole
from forge.persistence.markdown import MarkdownInvestigationRepository
from forge.persistence.sqlite import SQLiteProjection
from forge.persistence.unit_of_work import InvestigationUnitOfWork


class TickingClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 7, 16, 21, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        self.current += timedelta(seconds=1)
        return self.current


class RecordingStore:
    def __init__(self, unit_of_work: InvestigationUnitOfWork) -> None:
        self.unit_of_work = unit_of_work
        self.saved_stages: list[WorkflowStage] = []

    def save(self, record):
        self.unit_of_work.save(record)
        self.saved_stages.append(record.workflow.stage)

    def load(self, investigation_id: str):
        return self.unit_of_work.load(investigation_id)

    def exists(self, investigation_id: str) -> bool:
        return self.unit_of_work.exists(investigation_id)


def setup_orchestrator(tmp_path: Path):
    markdown = MarkdownInvestigationRepository(tmp_path / "outputs" / "investigations")
    projection = SQLiteProjection(tmp_path / "data" / "forge.sqlite3")
    store = RecordingStore(InvestigationUnitOfWork(markdown, projection))
    runner = DeterministicSpecialistRunner()
    orchestrator = InvestigationOrchestrator(
        store=store,
        specialists=runner,
        clock=TickingClock(),
        lock_root=tmp_path / "locks",
    )
    return orchestrator, store, runner, markdown, projection


async def choose_a(orchestrator: InvestigationOrchestrator, view):
    return await orchestrator.submit_decision(
        view.record.id,
        prompt_id=view.prompt.id,
        raw_choice=ChoiceLetter.A,
    )


@pytest.mark.asyncio
async def test_quick_investigation_reaches_completed_through_all_checkpoints(
    tmp_path: Path,
) -> None:
    orchestrator, store, runner, markdown, projection = setup_orchestrator(tmp_path)

    focus = await orchestrator.start(
        investigation_id="inv_walking_skeleton",
        seed="What follows from conservation under constraint?",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 16, 21, 0, tzinfo=UTC),
    )
    evidence = await choose_a(orchestrator, focus)
    action = await choose_a(orchestrator, evidence)
    completed = await choose_a(orchestrator, action)

    assert completed.record.workflow.stage is WorkflowStage.COMPLETED
    assert completed.prompt is None
    assert completed.record.selected_focus
    assert completed.record.epistemic_items
    assert completed.record.skeptical_challenges
    assert completed.record.selected_action is not None
    assert runner.calls == [
        ModelRole.RESEARCHER,
        ModelRole.CONNECTION_FINDER,
        ModelRole.SYNTHESIZER,
        ModelRole.SKEPTIC,
        ModelRole.EXPERIMENT_DESIGNER,
    ]
    assert store.saved_stages == [
        WorkflowStage.SEEDED,
        WorkflowStage.FOCUS_CHECKPOINT,
        WorkflowStage.FOCUS_CHECKPOINT,
        WorkflowStage.PREMISES_EXTRACTED,
        WorkflowStage.EVIDENCE_CHECKPOINT,
        WorkflowStage.EVIDENCE_CHECKPOINT,
        WorkflowStage.CONNECTIONS_GENERATED,
        WorkflowStage.HYPOTHESES_SYNTHESIZED,
        WorkflowStage.STRESS_TESTED,
        WorkflowStage.ACTIONS_DESIGNED,
        WorkflowStage.ACTION_CHECKPOINT,
        WorkflowStage.ACTION_CHECKPOINT,
        WorkflowStage.COMPLETED,
    ]
    assert markdown.load(completed.record.id) == completed.record
    assert projection.load_record(completed.record.id) == completed.record


@pytest.mark.asyncio
async def test_stale_prompt_is_rejected_without_running_a_specialist(tmp_path: Path) -> None:
    orchestrator, _, runner, _, _ = setup_orchestrator(tmp_path)
    focus = await orchestrator.start(
        investigation_id="inv_stale_prompt",
        seed="Where does the bottleneck come from?",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 16, 21, 0, tzinfo=UTC),
    )

    result = await orchestrator.submit_decision(
        focus.record.id,
        prompt_id="some-other-prompt",
        raw_choice="A",
    )

    assert result.error == "That choice belongs to an older or different question."
    assert result.prompt == focus.prompt
    assert runner.calls == []


@pytest.mark.asyncio
async def test_start_is_idempotent_for_an_existing_working_record(tmp_path: Path) -> None:
    orchestrator, _, runner, _, _ = setup_orchestrator(tmp_path)
    focus = await orchestrator.start(
        investigation_id="inv_idempotent_start",
        seed="Preserve this seed.",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 16, 21, 0, tzinfo=UTC),
    )
    evidence = await choose_a(orchestrator, focus)

    restarted = await orchestrator.start(
        investigation_id="inv_idempotent_start",
        seed="Do not overwrite with this seed.",
        depth=DepthMode.DEEP,
        at=datetime(2026, 7, 16, 23, 0, tzinfo=UTC),
    )

    assert restarted.record == evidence.record
    assert restarted.record.seed == "Preserve this seed."
    assert runner.calls == [ModelRole.RESEARCHER]


@pytest.mark.asyncio
async def test_projection_failure_never_blocks_canonical_progress(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    orchestrator, store, runner, markdown, projection = setup_orchestrator(tmp_path)
    focus = await orchestrator.start(
        investigation_id="inv_projection_rollback",
        seed="Can a failed save lose the checkpoint?",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 16, 21, 0, tzinfo=UTC),
    )

    def fail_projection_save(record: object) -> None:
        raise RuntimeError("simulated projection failure")

    monkeypatch.setattr(projection, "save", fail_projection_save)

    evidence = await choose_a(orchestrator, focus)

    assert evidence.record.workflow.stage is WorkflowStage.EVIDENCE_CHECKPOINT
    assert runner.calls == [ModelRole.RESEARCHER]
    assert markdown.load(focus.record.id) == evidence.record
    rebuilt = SQLiteProjection(tmp_path / "data" / "forge.sqlite3")
    assert rebuilt.load_record(focus.record.id) == evidence.record


@pytest.mark.asyncio
async def test_invalid_choice_keeps_checkpoint_without_running_a_role(tmp_path: Path) -> None:
    orchestrator, _, runner, _, _ = setup_orchestrator(tmp_path)
    focus = await orchestrator.start(
        investigation_id="inv_invalid_checkpoint_choice",
        seed="What should invalid input do?",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 16, 21, 0, tzinfo=UTC),
    )

    result = await orchestrator.submit_decision(
        focus.record.id,
        prompt_id=focus.prompt.id,
        raw_choice="not-a-letter",
    )

    assert result.error == "Choose A, B, C, D, or E."
    assert result.prompt == focus.prompt
    assert runner.calls == []


@pytest.mark.asyncio
async def test_paused_checkpoint_rejects_input_until_resumed(tmp_path: Path) -> None:
    orchestrator, _, runner, _, _ = setup_orchestrator(tmp_path)
    focus = await orchestrator.start(
        investigation_id="inv_paused_checkpoint",
        seed="Can an old screen advance paused work?",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 16, 21, 0, tzinfo=UTC),
    )
    paused = await orchestrator.pause(focus.record.id)

    result = await orchestrator.submit_decision(
        paused.record.id,
        prompt_id=paused.prompt.id,
        raw_choice="A",
    )

    assert result.error == "Resume this investigation before choosing."
    assert result.record == paused.record
    assert runner.calls == []


@pytest.mark.asyncio
async def test_evidence_pause_choice_stops_before_connection_work(tmp_path: Path) -> None:
    orchestrator, _, runner, _, _ = setup_orchestrator(tmp_path)
    focus = await orchestrator.start(
        investigation_id="inv_evidence_pause",
        seed="Should D really pause?",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 16, 21, 0, tzinfo=UTC),
    )
    evidence = await choose_a(orchestrator, focus)

    paused = await orchestrator.submit_decision(
        evidence.record.id,
        prompt_id=evidence.prompt.id,
        raw_choice="D",
    )

    assert paused.record.workflow.status is WorkflowStatus.PAUSED
    assert runner.calls == [ModelRole.RESEARCHER]

    resumed = await orchestrator.resume(paused.record.id)

    assert resumed.record.workflow.stage is WorkflowStage.ACTION_CHECKPOINT
    assert runner.calls[-4:] == [
        ModelRole.CONNECTION_FINDER,
        ModelRole.SYNTHESIZER,
        ModelRole.SKEPTIC,
        ModelRole.EXPERIMENT_DESIGNER,
    ]


@pytest.mark.asyncio
async def test_action_rejection_completes_without_a_selected_action(tmp_path: Path) -> None:
    orchestrator, _, _, _, _ = setup_orchestrator(tmp_path)
    focus = await orchestrator.start(
        investigation_id="inv_reject_action",
        seed="Can the proposed action be rejected?",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 16, 21, 0, tzinfo=UTC),
    )
    evidence = await choose_a(orchestrator, focus)
    action = await choose_a(orchestrator, evidence)

    completed = await orchestrator.submit_decision(
        action.record.id,
        prompt_id=action.prompt.id,
        raw_choice="C",
    )

    assert completed.record.workflow.stage is WorkflowStage.COMPLETED
    assert completed.record.selected_action is None


@pytest.mark.asyncio
async def test_custom_action_replaces_the_proposed_statement(tmp_path: Path) -> None:
    orchestrator, _, _, _, _ = setup_orchestrator(tmp_path)
    focus = await orchestrator.start(
        investigation_id="inv_custom_action",
        seed="Can the action be customized?",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 16, 21, 0, tzinfo=UTC),
    )
    evidence = await choose_a(orchestrator, focus)
    action = await choose_a(orchestrator, evidence)

    completed = await orchestrator.submit_decision(
        action.record.id,
        prompt_id=action.prompt.id,
        raw_choice="E",
        custom_answer="Run the comparison with one system first.",
    )

    assert completed.record.workflow.stage is WorkflowStage.COMPLETED
    assert completed.record.selected_action is not None
    assert completed.record.selected_action.statement == "Run the comparison with one system first."


class BlockingResearchRunner(DeterministicSpecialistRunner):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def run(self, role, record):
        if role is ModelRole.RESEARCHER:
            self.started.set()
            await self.release.wait()
        return await super().run(role, record)


@pytest.mark.asyncio
async def test_concurrent_replay_runs_one_specialist_and_accepts_one_decision(
    tmp_path: Path,
) -> None:
    markdown = MarkdownInvestigationRepository(tmp_path / "outputs" / "investigations")
    projection = SQLiteProjection(tmp_path / "data" / "forge.sqlite3")
    store = RecordingStore(InvestigationUnitOfWork(markdown, projection))
    runner = BlockingResearchRunner()
    orchestrator = InvestigationOrchestrator(
        store=store,
        specialists=runner,
        clock=TickingClock(),
        lock_root=tmp_path / "locks",
    )
    focus = await orchestrator.start(
        investigation_id="inv_concurrent_replay",
        seed="Can this decision run twice?",
        depth=DepthMode.QUICK,
        at=datetime(2026, 7, 16, 21, 0, tzinfo=UTC),
    )

    first = asyncio.create_task(
        orchestrator.submit_decision(
            focus.record.id,
            prompt_id=focus.prompt.id,
            raw_choice="A",
        )
    )
    await runner.started.wait()
    second = asyncio.create_task(
        orchestrator.submit_decision(
            focus.record.id,
            prompt_id=focus.prompt.id,
            raw_choice="A",
        )
    )
    await asyncio.sleep(0)
    runner.release.set()
    results = await asyncio.gather(first, second)

    assert runner.calls.count(ModelRole.RESEARCHER) == 1
    assert sum(result.error is None for result in results) == 1
    assert sum(result.error is not None for result in results) == 1
    persisted = store.load(focus.record.id)
    assert len(persisted.decisions) == 1
