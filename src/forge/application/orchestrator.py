"""Deterministic, checkpoint-driven investigation orchestration."""

from __future__ import annotations

import asyncio
import fcntl
import os
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from pydantic import TypeAdapter, ValidationError

from forge.application.budgets import BudgetExceeded
from forge.application.decisions import (
    ChoiceLetter,
    DecisionAttempt,
    DecisionKind,
    DecisionOption,
    DecisionPrompt,
    submit_decision,
)
from forge.domain.epistemics import (
    Confidence,
    ConfidenceLevel,
    EpistemicItem,
    Evidence,
    PrimarySourceDetails,
    Provenance,
)
from forge.domain.identifiers import InvestigationId
from forge.domain.investigation import (
    DepthMode,
    InvestigationWorkflow,
    WorkflowStage,
    WorkflowStatus,
)
from forge.gateways.model import FailureKind, ModelReceipt, ModelRole
from forge.persistence.metadata import (
    ActionProposal,
    ChallengeDisposition,
    InvestigationRecord,
    LocalSourceReference,
    SkepticalChallenge,
)

_INVESTIGATION_ID_ADAPTER = TypeAdapter(InvestigationId)


@dataclass(frozen=True)
class SpecialistContribution:
    epistemic_items: tuple[EpistemicItem, ...] = ()
    skeptical_challenges: tuple[SkepticalChallenge, ...] = ()
    selected_action: ActionProposal | None = None
    unresolved_questions: tuple[str, ...] = ()
    decision_prompt: DecisionPrompt | None = None
    model_receipts: tuple[ModelReceipt, ...] = ()


class SpecialistRunner(Protocol):
    async def run(
        self,
        role: ModelRole,
        record: InvestigationRecord,
    ) -> SpecialistContribution: ...


class SpecialistExecutionError(RuntimeError):
    """A sanitized specialist failure that must be persisted before recovery."""

    def __init__(
        self,
        message: str,
        *,
        failure_kind: FailureKind,
        receipt: ModelReceipt,
    ) -> None:
        super().__init__(message)
        self.failure_kind = failure_kind
        self.receipt = receipt


class InvestigationStore(Protocol):
    def save(self, record: InvestigationRecord) -> None: ...

    def load(self, investigation_id: str) -> InvestigationRecord: ...

    def exists(self, investigation_id: str) -> bool: ...


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

_MAX_SKEPTICAL_REVISIONS = {
    DepthMode.QUICK: 0,
    DepthMode.STANDARD: 1,
    DepthMode.DEEP: 3,
}


class InvestigationOrchestrator:
    def __init__(
        self,
        *,
        store: InvestigationStore,
        specialists: SpecialistRunner,
        clock: Callable[[], datetime],
        lock_root: Path,
    ) -> None:
        self._store = store
        self._specialists = specialists
        self._clock = clock
        self._lock_root = lock_root

    async def start(
        self,
        *,
        investigation_id: str,
        seed: str,
        depth: DepthMode,
        at: datetime,
        source_reference: LocalSourceReference | None = None,
        prior_investigation_ids: tuple[str, ...] = (),
        preflight_decisions: tuple[DecisionAttempt, ...] = (),
        live_confirmation: DecisionAttempt | None = None,
    ) -> OrchestrationView:
        if (
            live_confirmation is not None
            and live_confirmation.prompt.id != f"{investigation_id}-live-confirmation-v1"
        ):
            raise ValueError("live confirmation does not belong to this investigation")
        async with self._investigation_lock(investigation_id):
            if not self._store.exists(investigation_id):
                live_approved = bool(
                    live_confirmation is not None
                    and live_confirmation.selection is not None
                    and live_confirmation.prompt.kind is DecisionKind.LIVE_CONFIRMATION
                    and live_confirmation.selection.letter is ChoiceLetter.A
                )
                record = InvestigationRecord(
                    id=investigation_id,
                    seed=seed,
                    workflow=InvestigationWorkflow.start(depth=depth, at=at),
                    decisions=(
                        *preflight_decisions,
                        *((live_confirmation,) if live_confirmation else ()),
                    ),
                    source_references=(source_reference,) if source_reference else (),
                    prior_investigation_ids=prior_investigation_ids,
                    live_execution_approved=live_approved,
                )
                self._store.save(record)
            return await self._run_until_checkpoint_locked(investigation_id)

    async def run_until_checkpoint(self, investigation_id: str) -> OrchestrationView:
        async with self._investigation_lock(investigation_id):
            return await self._run_until_checkpoint_locked(investigation_id)

    async def record_live_confirmation(
        self,
        investigation_id: str,
        confirmation: DecisionAttempt,
    ) -> InvestigationRecord:
        """Persist a fresh A approval before resuming paid work."""

        if (
            confirmation.error is not None
            or confirmation.selection is None
            or confirmation.prompt.kind is not DecisionKind.LIVE_CONFIRMATION
            or confirmation.prompt.id != f"{investigation_id}-live-confirmation-v1"
            or confirmation.selection.letter is not ChoiceLetter.A
        ):
            raise ValueError("resuming live execution requires an A confirmation")
        async with self._investigation_lock(investigation_id):
            record = self._store.load(investigation_id)
            updated = record.model_copy(
                update={
                    "decisions": (*record.decisions, confirmation),
                    "live_execution_approved": True,
                }
            )
            self._store.save(updated)
            return updated

    async def _run_until_checkpoint_locked(self, investigation_id: str) -> OrchestrationView:
        record = self._store.load(investigation_id)
        while record.workflow.status is WorkflowStatus.ACTIVE:
            if record.workflow.stage is WorkflowStage.COMPLETED:
                return OrchestrationView(record=record, prompt=None)
            if record.pending_decision is not None:
                return OrchestrationView(record=record, prompt=record.pending_decision)
            try:
                record = await self._advance_one_stage(record)
            except SpecialistExecutionError as error:
                recovery = record.model_copy(
                    update={
                        "model_receipts": (*record.model_receipts, error.receipt),
                        "pending_decision": _recovery_prompt(
                            record.id,
                            record.workflow.stage,
                            failure_kind=error.failure_kind,
                        ),
                    }
                )
                self._store.save(recovery)
                return OrchestrationView(
                    record=recovery,
                    prompt=recovery.pending_decision,
                    error=str(error),
                )
            except BudgetExceeded as error:
                stopped = record.model_copy(
                    update={
                        "pending_decision": _budget_exhausted_prompt(
                            record.id, record.workflow.stage
                        )
                    }
                )
                self._store.save(stopped)
                return OrchestrationView(
                    record=stopped,
                    prompt=stopped.pending_decision,
                    error=str(error),
                )
        return OrchestrationView(record=record, prompt=record.pending_decision)

    async def submit_decision(
        self,
        investigation_id: str,
        *,
        prompt_id: str,
        raw_choice: str,
        custom_answer: str | None = None,
    ) -> OrchestrationView:
        async with self._investigation_lock(investigation_id):
            return await self._submit_decision_locked(
                investigation_id,
                prompt_id=prompt_id,
                raw_choice=raw_choice,
                custom_answer=custom_answer,
            )

    async def _submit_decision_locked(
        self,
        investigation_id: str,
        *,
        prompt_id: str,
        raw_choice: str,
        custom_answer: str | None,
    ) -> OrchestrationView:
        record = self._store.load(investigation_id)
        prompt = record.pending_decision
        expected_kind = (
            prompt.kind
            if prompt is not None
            and prompt.kind in {DecisionKind.RECOVERY, DecisionKind.BUDGET_EXHAUSTED}
            else self._expected_decision_kind(record.workflow.stage)
        )
        if record.workflow.status is WorkflowStatus.PAUSED:
            return OrchestrationView(
                record=record,
                prompt=prompt,
                error="Resume this investigation before choosing.",
            )
        if prompt is None or prompt.id != prompt_id or prompt.kind is not expected_kind:
            return OrchestrationView(
                record=record,
                prompt=prompt,
                error="That choice belongs to an older or different question.",
            )
        attempt = submit_decision(prompt, raw_choice, custom_answer=custom_answer)
        if attempt.error is not None:
            return OrchestrationView(record=record, prompt=prompt, error=attempt.error)
        assert attempt.selection is not None

        if prompt.kind is DecisionKind.BUDGET_EXHAUSTED:
            stopped_updates: dict[str, object] = {
                "decisions": (*record.decisions, attempt),
                "pending_decision": None,
                "workflow": record.workflow.pause(at=self._at(record)),
            }
            if attempt.custom_answer:
                stopped_updates["unresolved_questions"] = (
                    *record.unresolved_questions,
                    attempt.custom_answer,
                )
            record = record.model_copy(update=stopped_updates)
            self._store.save(record)
            return OrchestrationView(record=record, prompt=None)

        if prompt.kind is DecisionKind.RECOVERY:
            recovery_updates: dict[str, object] = {
                "decisions": (*record.decisions, attempt),
                "pending_decision": None,
            }
            if attempt.selection.letter is not ChoiceLetter.A:
                recovery_updates["workflow"] = record.workflow.pause(at=self._at(record))
                recovery_updates["pending_decision"] = prompt
                if attempt.custom_answer:
                    recovery_updates["unresolved_questions"] = (
                        *record.unresolved_questions,
                        attempt.custom_answer,
                    )
            record = record.model_copy(update=recovery_updates)
            self._store.save(record)
            if attempt.selection.letter is not ChoiceLetter.A:
                return OrchestrationView(record=record, prompt=None)
            return await self._run_until_checkpoint_locked(investigation_id)

        updates: dict[str, object] = {
            "decisions": (*record.decisions, attempt),
            "pending_decision": None,
        }
        stage = record.workflow.stage
        letter = attempt.selection.letter
        action_deferred = stage is WorkflowStage.ACTION_CHECKPOINT and letter in {
            ChoiceLetter.B,
            ChoiceLetter.D,
        }
        source_paused = stage is WorkflowStage.SOURCE_CONSENT and letter is ChoiceLetter.D
        should_pause = (
            (stage is WorkflowStage.EVIDENCE_CHECKPOINT and letter is ChoiceLetter.D)
            or action_deferred
            or source_paused
        )
        if should_pause:
            updates["workflow"] = record.workflow.pause(at=self._at(record))
        if action_deferred or source_paused:
            # Deferring is not acceptance: keep the question open so resume
            # re-asks it instead of falling through to COMPLETED.
            updates["pending_decision"] = prompt

        if stage is WorkflowStage.SOURCE_CONSENT:
            updates["source_transmission_approved"] = letter is ChoiceLetter.A
            if letter in {ChoiceLetter.B, ChoiceLetter.C}:
                updates["unresolved_questions"] = (
                    *record.unresolved_questions,
                    "Local source transmission declined; add premises or evidence manually.",
                )
                if letter is ChoiceLetter.C:
                    updates["epistemic_items"] = (
                        *record.epistemic_items,
                        *_manual_source_evidence(record),
                    )
            elif letter is ChoiceLetter.E:
                updates["unresolved_questions"] = (
                    *record.unresolved_questions,
                    attempt.custom_answer,
                )
        elif stage is WorkflowStage.FOCUS_CHECKPOINT:
            updates["selected_focus"] = attempt.custom_answer or attempt.selection.label
        elif stage is WorkflowStage.EVIDENCE_CHECKPOINT and attempt.custom_answer:
            updates["unresolved_questions"] = (
                *record.unresolved_questions,
                attempt.custom_answer,
            )
        elif stage is WorkflowStage.ACTION_CHECKPOINT:
            if letter is ChoiceLetter.C:
                updates["selected_action"] = None
            elif letter is ChoiceLetter.E and record.selected_action is not None:
                updates["selected_action"] = record.selected_action.model_copy(
                    update={"statement": attempt.custom_answer}
                )
        record = record.model_copy(update=updates)
        self._store.save(record)
        if should_pause:
            return OrchestrationView(record=record, prompt=None)
        return await self._run_until_checkpoint_locked(investigation_id)

    async def pause(self, investigation_id: str) -> OrchestrationView:
        async with self._investigation_lock(investigation_id):
            record = self._store.load(investigation_id)
            if record.workflow.status is WorkflowStatus.ACTIVE:
                record = record.model_copy(
                    update={"workflow": record.workflow.pause(at=self._at(record))}
                )
                self._store.save(record)
            return OrchestrationView(record=record, prompt=record.pending_decision)

    async def resume(self, investigation_id: str) -> OrchestrationView:
        async with self._investigation_lock(investigation_id):
            record = self._store.load(investigation_id)
            if record.workflow.status is WorkflowStatus.PAUSED:
                record = record.model_copy(
                    update={"workflow": record.workflow.resume(at=self._at(record))}
                )
                self._store.save(record)
            return await self._run_until_checkpoint_locked(investigation_id)

    async def _advance_one_stage(self, record: InvestigationRecord) -> InvestigationRecord:
        stage = record.workflow.stage
        if stage is WorkflowStage.SEEDED:
            if record.source_references:
                return self._persist_checkpoint(record, WorkflowStage.SOURCE_CONSENT)
            return await self._persist_focus_checkpoint(record)
        if stage is WorkflowStage.SOURCE_CONSENT:
            return await self._persist_focus_checkpoint(record)
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
        contribution = await self._specialists.run(role, record)
        record = self._apply_contribution(record, role, contribution)
        if (
            role is ModelRole.SKEPTIC
            and any(
                challenge.disposition is ChallengeDisposition.REJECT
                for challenge in contribution.skeptical_challenges
            )
            and record.skeptical_revision_cycles < _MAX_SKEPTICAL_REVISIONS[record.workflow.depth]
        ):
            record = record.model_copy(
                update={"skeptical_revision_cycles": record.skeptical_revision_cycles + 1}
            )
            return self._persist_checkpoint(record, WorkflowStage.EVIDENCE_CHECKPOINT)
        return self._persist_transition(record, next_stage)

    async def _persist_focus_checkpoint(
        self,
        record: InvestigationRecord,
    ) -> InvestigationRecord:
        if not record.live_execution_approved:
            return self._persist_checkpoint(record, WorkflowStage.FOCUS_CHECKPOINT)
        contribution = await self._specialists.run(ModelRole.LEAD, record)
        if contribution.decision_prompt is None:
            raise RuntimeError("live Lead did not return a focus decision")
        record = self._apply_contribution(record, ModelRole.LEAD, contribution)
        advanced = record.workflow.advance(WorkflowStage.FOCUS_CHECKPOINT, at=self._at(record))
        checkpoint = record.model_copy(
            update={
                "workflow": advanced,
                "pending_decision": contribution.decision_prompt,
            }
        )
        self._store.save(checkpoint)
        return checkpoint

    def _persist_checkpoint(
        self,
        record: InvestigationRecord,
        stage: WorkflowStage,
    ) -> InvestigationRecord:
        advanced = record.workflow.advance(stage, at=self._at(record))
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
            update={"workflow": record.workflow.advance(stage, at=self._at(record))}
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
            "model_receipts": (*record.model_receipts, *contribution.model_receipts),
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
            WorkflowStage.SOURCE_CONSENT: DecisionKind.SOURCE_CONSENT,
            WorkflowStage.FOCUS_CHECKPOINT: DecisionKind.FOCUS_CHECKPOINT,
            WorkflowStage.EVIDENCE_CHECKPOINT: DecisionKind.EVIDENCE_CHECKPOINT,
            WorkflowStage.ACTION_CHECKPOINT: DecisionKind.ACTION_CHECKPOINT,
        }.get(stage)

    def _at(self, record: InvestigationRecord) -> datetime:
        """Keep persisted workflow time monotonic across restarts and clock skew."""

        return max(self._clock(), record.workflow.updated_at)

    @asynccontextmanager
    async def _investigation_lock(self, investigation_id: str):
        try:
            safe_id = _INVESTIGATION_ID_ADAPTER.validate_python(investigation_id)
        except ValidationError:
            raise ValueError("invalid investigation identifier") from None
        lock_root_existed = self._lock_root.exists()
        self._lock_root.mkdir(parents=True, exist_ok=True)
        if not lock_root_existed:
            os.chmod(self._lock_root, 0o700)
        lock_path = self._lock_root / f"{safe_id}.lock"
        flags = os.O_RDWR | os.O_CREAT
        flags |= getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except OSError as error:
            raise ValueError("unable to open investigation lock safely") from error
        acquired = False
        try:
            os.fchmod(descriptor, 0o600)
            while not acquired:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                except BlockingIOError:
                    await asyncio.sleep(0.01)
            yield
        finally:
            if acquired:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)


# Checkpoint copy: (question, options as (label, description), recommended letter or None).
# Descriptions state what actually happens next; a recommendation appears only
# where one choice is the defensible default rather than a real judgment call.
_CHECKPOINT_COPY: dict[
    WorkflowStage,
    tuple[str, tuple[tuple[str, str], ...], ChoiceLetter | None],
] = {
    WorkflowStage.SOURCE_CONSENT: (
        "May this local source be sent to the configured OpenRouter role models?",
        (
            ("Approve transmission", "Send the source text to the role models with the seed."),
            (
                "Continue without source",
                "Investigate without it; nothing from the source leaves this machine.",
            ),
            (
                "Use manual evidence",
                "Keep the source local and record it as evidence to review by hand.",
            ),
            (
                "Pause before deciding",
                "Save everything and stop; this question is asked again on resume.",
            ),
            ("Custom answer", "Record a concern or instruction; the source is not transmitted."),
        ),
        None,
    ),
    WorkflowStage.FOCUS_CHECKPOINT: (
        "Which focus should guide this investigation?",
        (
            ("Trace constraints", "Follow what physically or logically limits the system."),
            ("Challenge assumptions", "Probe the premises that are easiest to take for granted."),
            ("Seek connections", "Look for structure shared with better-understood problems."),
            ("Keep broad", "Defer narrowing until premises and evidence are on the table."),
            ("Custom answer", "State the focus in your own words; it becomes the recorded focus."),
        ),
        None,
    ),
    WorkflowStage.EVIDENCE_CHECKPOINT: (
        "How should we proceed with these premises and evidence?",
        (
            ("Accept", "Treat the premises and evidence above as the working base and continue."),
            (
                "Emphasize uncertainty",
                "Continue, recording that the low-confidence items deserve extra weight.",
            ),
            (
                "Proceed cautiously",
                "Continue, recording that every later claim should be read as provisional.",
            ),
            ("Pause here", "Save the record and stop; resuming continues from this point."),
            (
                "Custom answer",
                "Add a question or caveat to the record; the investigation continues.",
            ),
        ),
        ChoiceLetter.A,
    ),
    WorkflowStage.ACTION_CHECKPOINT: (
        "What should we do with the proposed test or action?",
        (
            ("Accept action", "Adopt this proposal as the investigation's outcome and finish."),
            ("Defer action", "Pause with the action undecided; resume asks this question again."),
            ("Reject action", "Discard the proposal and finish without a selected action."),
            ("Pause here", "Save everything and stop; resume returns to this question."),
            ("Custom answer", "Rewrite the action in your own words and finish with it."),
        ),
        ChoiceLetter.A,
    ),
}


def _decision_prompt(investigation_id: str, stage: WorkflowStage) -> DecisionPrompt:
    kind = InvestigationOrchestrator._expected_decision_kind(stage)
    if kind is None:
        raise ValueError("only checkpoint stages have decision prompts")
    question, copy, recommended = _CHECKPOINT_COPY[stage]
    options = tuple(
        DecisionOption(
            letter=letter,
            label=label,
            description=description,
            is_recommended=letter is recommended,
            accepts_custom_input=letter is ChoiceLetter.E,
        )
        for letter, (label, description) in zip(ChoiceLetter, copy, strict=True)
    )
    return DecisionPrompt(
        id=f"{investigation_id}-{kind.value}-v1",
        kind=kind,
        question=question,
        options=options,
    )


def _manual_source_evidence(record: InvestigationRecord) -> tuple[Evidence, ...]:
    """Retain inspectable source identities without copying or transmitting content."""

    return tuple(
        Evidence(
            id=f"epi_manual_source_{index}",
            statement=f"Local primary source retained for manual review: {Path(source.path).name}",
            uncertainty=Confidence(
                level=ConfidenceLevel.LOW,
                rationale="The source content has not been interpreted or transmitted.",
            ),
            provenance=Provenance(
                origin="User-supplied local primary source",
                locator=source.path,
            ),
            details=PrimarySourceDetails(
                source_reference=source.path,
                content_hash=source.sha256,
            ),
        )
        for index, source in enumerate(record.source_references, start=1)
    )


def _recovery_prompt(
    investigation_id: str,
    stage: WorkflowStage,
    *,
    failure_kind: FailureKind | None = None,
) -> DecisionPrompt:
    question = (
        "The model returned a response, but Forge quarantined it because it did not satisfy "
        "the role contract. Review it below, then choose what should happen next."
        if failure_kind is FailureKind.MALFORMED_OUTPUT
        else "The live model call failed. What should happen next?"
    )
    return DecisionPrompt(
        id=f"{investigation_id}-recovery-{stage.value}-v1",
        kind=DecisionKind.RECOVERY,
        question=question,
        options=(
            DecisionOption(
                letter=ChoiceLetter.A,
                label="Retry now",
                description="Retry the same unfinished stage within the remaining call budget.",
                is_recommended=True,
            ),
            DecisionOption(
                letter=ChoiceLetter.B,
                label="Resume later",
                description="Pause and keep this recovery question for the next session.",
            ),
            DecisionOption(
                letter=ChoiceLetter.C,
                label="Change model",
                description="Pause so the role model can be changed in local configuration.",
            ),
            DecisionOption(
                letter=ChoiceLetter.D,
                label="Stop here",
                description="Pause without discarding completed work or the failed receipt.",
            ),
            DecisionOption(
                letter=ChoiceLetter.E,
                label="Custom answer",
                description="Add only as much detail as desired and pause safely.",
                accepts_custom_input=True,
            ),
        ),
    )


def _budget_exhausted_prompt(investigation_id: str, stage: WorkflowStage) -> DecisionPrompt:
    return DecisionPrompt(
        id=f"{investigation_id}-budget-exhausted-{stage.value}-v1",
        kind=DecisionKind.BUDGET_EXHAUSTED,
        question="The approved model-call budget is exhausted. How should this run stop?",
        options=(
            DecisionOption(
                letter=ChoiceLetter.A,
                label="Stop safely",
                description="Pause without making another provider call.",
                is_recommended=True,
            ),
            DecisionOption(
                letter=ChoiceLetter.B,
                label="Review receipts",
                description="Pause so saved call usage and cost can be inspected.",
            ),
            DecisionOption(
                letter=ChoiceLetter.C,
                label="Review depth",
                description="Pause before starting a separately approved investigation.",
            ),
            DecisionOption(
                letter=ChoiceLetter.D,
                label="Stop here",
                description="Pause and preserve all completed work.",
            ),
            DecisionOption(
                letter=ChoiceLetter.E,
                label="Custom answer",
                description="Add only as much detail as desired and pause safely.",
                accepts_custom_input=True,
            ),
        ),
    )


__all__ = [
    "InvestigationOrchestrator",
    "OrchestrationView",
    "SpecialistContribution",
    "SpecialistExecutionError",
    "SpecialistRunner",
]
