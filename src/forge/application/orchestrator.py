"""Deterministic, checkpoint-driven investigation orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from forge.application.decisions import (
    ChoiceLetter,
    DecisionKind,
    DecisionOption,
    DecisionPrompt,
    submit_decision,
)
from forge.domain.epistemics import EpistemicItem
from forge.domain.investigation import (
    DepthMode,
    InvestigationWorkflow,
    WorkflowStage,
    WorkflowStatus,
)
from forge.gateways.model import ModelRole
from forge.persistence.metadata import ActionProposal, InvestigationRecord, SkepticalChallenge


@dataclass(frozen=True)
class SpecialistContribution:
    epistemic_items: tuple[EpistemicItem, ...] = ()
    skeptical_challenges: tuple[SkepticalChallenge, ...] = ()
    selected_action: ActionProposal | None = None
    unresolved_questions: tuple[str, ...] = ()


class SpecialistRunner(Protocol):
    def run(self, role: ModelRole, record: InvestigationRecord) -> SpecialistContribution: ...


class InvestigationStore(Protocol):
    def save(self, record: InvestigationRecord) -> None: ...

    def load(self, investigation_id: str) -> InvestigationRecord: ...


@dataclass(frozen=True)
class OrchestrationView:
    record: InvestigationRecord
    prompt: DecisionPrompt | None
    error: str | None = None


_ROLE_STAGES = {
    WorkflowStage.FOCUS_CHECKPOINT: (ModelRole.RESEARCHER, WorkflowStage.PREMISES_EXTRACTED),
    WorkflowStage.EVIDENCE_CHECKPOINT: (
        ModelRole.CONNECTION_FINDER,
        WorkflowStage.CONNECTIONS_GENERATED,
    ),
    WorkflowStage.CONNECTIONS_GENERATED: (
        ModelRole.SYNTHESIZER,
        WorkflowStage.HYPOTHESES_SYNTHESIZED,
    ),
    WorkflowStage.HYPOTHESES_SYNTHESIZED: (ModelRole.SKEPTIC, WorkflowStage.STRESS_TESTED),
    WorkflowStage.STRESS_TESTED: (
        ModelRole.EXPERIMENT_DESIGNER,
        WorkflowStage.ACTIONS_DESIGNED,
    ),
}


class InvestigationOrchestrator:
    def __init__(
        self,
        *,
        store: InvestigationStore,
        specialists: SpecialistRunner,
        clock: Callable[[], datetime],
    ) -> None:
        self._store = store
        self._specialists = specialists
        self._clock = clock

    def start(
        self,
        *,
        investigation_id: str,
        seed: str,
        depth: DepthMode,
        at: datetime,
    ) -> OrchestrationView:
        record = InvestigationRecord(
            id=investigation_id,
            seed=seed,
            workflow=InvestigationWorkflow.start(depth=depth, at=at),
        )
        self._store.save(record)
        return self.run_until_checkpoint(investigation_id)

    def run_until_checkpoint(self, investigation_id: str) -> OrchestrationView:
        record = self._store.load(investigation_id)
        while record.workflow.status is WorkflowStatus.ACTIVE:
            if record.workflow.stage is WorkflowStage.COMPLETED:
                return OrchestrationView(record=record, prompt=None)
            if record.pending_decision is not None:
                return OrchestrationView(record=record, prompt=record.pending_decision)
            record = self._advance_one_stage(record)
        return OrchestrationView(record=record, prompt=record.pending_decision)

    def submit_decision(
        self,
        investigation_id: str,
        *,
        prompt_id: str,
        raw_choice: str,
        custom_answer: str | None = None,
    ) -> OrchestrationView:
        record = self._store.load(investigation_id)
        prompt = record.pending_decision
        expected_kind = self._expected_decision_kind(record.workflow.stage)
        if prompt is None or prompt.id != prompt_id or prompt.kind is not expected_kind:
            return OrchestrationView(
                record=record,
                prompt=prompt,
                error="That choice belongs to an older or different question.",
            )
        attempt = submit_decision(prompt, raw_choice, custom_answer=custom_answer)
        if attempt.error is not None:
            return OrchestrationView(record=record, prompt=prompt, error=attempt.error)

        updates: dict[str, object] = {
            "decisions": (*record.decisions, attempt),
            "pending_decision": None,
        }
        if record.workflow.stage is WorkflowStage.FOCUS_CHECKPOINT:
            updates["selected_focus"] = attempt.custom_answer or attempt.selection.label
        elif record.workflow.stage is WorkflowStage.EVIDENCE_CHECKPOINT and attempt.custom_answer:
            updates["unresolved_questions"] = (
                *record.unresolved_questions,
                attempt.custom_answer,
            )
        record = record.model_copy(update=updates)
        self._store.save(record)
        return self.run_until_checkpoint(investigation_id)

    def pause(self, investigation_id: str) -> OrchestrationView:
        record = self._store.load(investigation_id)
        if record.workflow.status is WorkflowStatus.ACTIVE:
            record = record.model_copy(update={"workflow": record.workflow.pause(at=self._clock())})
            self._store.save(record)
        return OrchestrationView(record=record, prompt=record.pending_decision)

    def resume(self, investigation_id: str) -> OrchestrationView:
        record = self._store.load(investigation_id)
        if record.workflow.status is WorkflowStatus.PAUSED:
            record = record.model_copy(
                update={"workflow": record.workflow.resume(at=self._clock())}
            )
            self._store.save(record)
        return self.run_until_checkpoint(investigation_id)

    def _advance_one_stage(self, record: InvestigationRecord) -> InvestigationRecord:
        stage = record.workflow.stage
        if stage is WorkflowStage.SEEDED:
            return self._persist_checkpoint(record, WorkflowStage.FOCUS_CHECKPOINT)
        if stage is WorkflowStage.PREMISES_EXTRACTED:
            return self._persist_checkpoint(record, WorkflowStage.EVIDENCE_CHECKPOINT)
        if stage is WorkflowStage.ACTIONS_DESIGNED:
            return self._persist_checkpoint(record, WorkflowStage.ACTION_CHECKPOINT)
        if stage is WorkflowStage.ACTION_CHECKPOINT:
            return self._persist_transition(record, WorkflowStage.COMPLETED)

        role_stage = _ROLE_STAGES.get(stage)
        if role_stage is None:
            raise RuntimeError(f"orchestrator cannot advance stage {stage}")
        role, next_stage = role_stage
        contribution = self._specialists.run(role, record)
        record = self._apply_contribution(record, role, contribution)
        return self._persist_transition(record, next_stage)

    def _persist_checkpoint(
        self,
        record: InvestigationRecord,
        stage: WorkflowStage,
    ) -> InvestigationRecord:
        advanced = record.workflow.advance(stage, at=self._clock())
        checkpoint = record.model_copy(
            update={"workflow": advanced, "pending_decision": _decision_prompt(record.id, stage)}
        )
        self._store.save(checkpoint)
        return checkpoint

    def _persist_transition(
        self,
        record: InvestigationRecord,
        stage: WorkflowStage,
    ) -> InvestigationRecord:
        advanced = record.model_copy(
            update={"workflow": record.workflow.advance(stage, at=self._clock())}
        )
        self._store.save(advanced)
        return advanced

    @staticmethod
    def _apply_contribution(
        record: InvestigationRecord,
        role: ModelRole,
        contribution: SpecialistContribution,
    ) -> InvestigationRecord:
        updates: dict[str, object] = {
            "epistemic_items": (*record.epistemic_items, *contribution.epistemic_items),
            "unresolved_questions": (
                *record.unresolved_questions,
                *contribution.unresolved_questions,
            ),
        }
        if role is ModelRole.SKEPTIC:
            updates["skeptical_challenges"] = (
                *record.skeptical_challenges,
                *contribution.skeptical_challenges,
            )
        if role is ModelRole.EXPERIMENT_DESIGNER:
            updates["selected_action"] = contribution.selected_action
        return record.model_copy(update=updates)

    @staticmethod
    def _expected_decision_kind(stage: WorkflowStage) -> DecisionKind | None:
        return {
            WorkflowStage.FOCUS_CHECKPOINT: DecisionKind.FOCUS_CHECKPOINT,
            WorkflowStage.EVIDENCE_CHECKPOINT: DecisionKind.EVIDENCE_CHECKPOINT,
            WorkflowStage.ACTION_CHECKPOINT: DecisionKind.ACTION_CHECKPOINT,
        }.get(stage)


def _decision_prompt(investigation_id: str, stage: WorkflowStage) -> DecisionPrompt:
    kind = InvestigationOrchestrator._expected_decision_kind(stage)
    if kind is None:
        raise ValueError("only checkpoint stages have decision prompts")
    question, labels = {
        WorkflowStage.FOCUS_CHECKPOINT: (
            "Which focus should guide this investigation?",
            ("Trace constraints", "Challenge assumptions", "Seek connections", "Keep broad"),
        ),
        WorkflowStage.EVIDENCE_CHECKPOINT: (
            "How should we proceed with these premises and evidence?",
            ("Accept", "Emphasize uncertainty", "Proceed cautiously", "Pause here"),
        ),
        WorkflowStage.ACTION_CHECKPOINT: (
            "What should we do with the proposed test or action?",
            ("Accept action", "Defer action", "Reject action", "Pause here"),
        ),
    }[stage]
    options = tuple(
        DecisionOption(
            letter=letter,
            label=label,
            description=f"{label} for the next step.",
            is_recommended=letter is ChoiceLetter.A,
            accepts_custom_input=letter is ChoiceLetter.E,
        )
        for letter, label in zip(ChoiceLetter, (*labels, "Custom answer"), strict=True)
    )
    return DecisionPrompt(
        id=f"{investigation_id}-{kind.value}-v1",
        kind=kind,
        question=question,
        options=options,
    )


__all__ = [
    "InvestigationOrchestrator",
    "OrchestrationView",
    "SpecialistContribution",
    "SpecialistRunner",
]
