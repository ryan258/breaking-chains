from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from forge.application.budgets import (
    BudgetExceeded,
    BudgetPolicy,
    DepthBudget,
    live_run_confirmation_prompt,
)
from forge.application.decisions import DecisionKind, submit_decision
from forge.application.orchestrator import InvestigationOrchestrator
from forge.application.specialists import LiveSpecialistRunError, LiveSpecialistRunner
from forge.domain.investigation import DepthMode, InvestigationWorkflow
from forge.gateways.model import FailureKind, ModelReceipt, ModelResult, ModelRole, ModelUsage
from forge.persistence.markdown import MarkdownInvestigationRepository
from forge.persistence.metadata import InvestigationRecord
from forge.persistence.sqlite import SQLiteProjection
from forge.persistence.unit_of_work import InvestigationUnitOfWork

STARTED = datetime(2026, 7, 17, 12, 0, tzinfo=UTC)


class RecordingGateway:
    def __init__(self, output: dict[str, object]) -> None:
        self.output = output
        self.requests = []

    async def complete(self, request):
        self.requests.append(request)
        return ModelResult(output=self.output, receipt=receipt(request.role))


def receipt(role: ModelRole = ModelRole.RESEARCHER) -> ModelReceipt:
    return ModelReceipt(
        role=role,
        model=f"vendor/{role.value}",
        started_at=STARTED,
        finished_at=STARTED + timedelta(seconds=1),
        duration_ms=1000,
        attempts=1,
        usage=ModelUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15, cost=0.01),
        prompt_contract_version=f"{role.value}-v1",
        artifact_path=Path(f"outputs/model-calls/inv_live/call_{role.value}.json"),
    )


def approved_record(*, receipts: tuple[ModelReceipt, ...] = ()) -> InvestigationRecord:
    prompt = live_run_confirmation_prompt(
        investigation_id="inv_live",
        depth=DepthMode.QUICK,
        budget=DepthBudget(max_calls=6, max_output_tokens_per_call=1200),
        source_attached=False,
    )
    approval = submit_decision(prompt, "A")
    return InvestigationRecord(
        id="inv_live",
        seed="A sample weighed 2.4 kilograms.",
        workflow=InvestigationWorkflow.start(depth=DepthMode.QUICK, at=STARTED),
        decisions=(approval,),
        live_execution_approved=True,
        model_receipts=receipts,
    )


def runner(gateway) -> LiveSpecialistRunner:
    return LiveSpecialistRunner(
        gateway=gateway,
        models={role: f"vendor/{role.value}" for role in ModelRole},
        budgets=BudgetPolicy(
            quick=DepthBudget(max_calls=6, max_output_tokens_per_call=1200),
            standard=DepthBudget(max_calls=10, max_output_tokens_per_call=2400),
            deep=DepthBudget(max_calls=24, max_output_tokens_per_call=4800),
        ),
    )


@pytest.mark.asyncio
async def test_live_runner_rejects_unapproved_execution_before_gateway_call() -> None:
    gateway = RecordingGateway({})
    unapproved = approved_record().model_copy(
        update={"live_execution_approved": False, "decisions": ()}
    )

    with pytest.raises(PermissionError, match="not approved"):
        await runner(gateway).run(ModelRole.RESEARCHER, unapproved)

    assert gateway.requests == []


@pytest.mark.asyncio
async def test_live_runner_enforces_call_budget_before_gateway_call() -> None:
    gateway = RecordingGateway({})
    exhausted = approved_record(receipts=tuple(receipt() for _ in range(6)))

    with pytest.raises(BudgetExceeded, match="call limit"):
        await runner(gateway).run(ModelRole.RESEARCHER, exhausted)

    assert gateway.requests == []


@pytest.mark.asyncio
async def test_fresh_live_approval_grants_another_bounded_call_batch() -> None:
    confidence = {"level": "medium", "rationale": "Requires independent review."}
    gateway = RecordingGateway(
        {
            "epistemic_items": [
                {
                    "id": "epi_second_batch_premise",
                    "category": "premise",
                    "statement": "A fresh approval starts another bounded batch.",
                    "uncertainty": confidence,
                    "origin": "Researcher",
                }
            ],
            "unsupported_assumptions": [],
        }
    )
    exhausted = approved_record(receipts=tuple(receipt() for _ in range(6)))
    renewed = exhausted.model_copy(
        update={"decisions": (*exhausted.decisions, exhausted.decisions[0])}
    )

    contribution = await runner(gateway).run(ModelRole.RESEARCHER, renewed)

    assert contribution.epistemic_items[0].id == "epi_second_batch_premise"
    assert len(gateway.requests) == 1


@pytest.mark.asyncio
async def test_orchestrator_turns_exhausted_budget_into_an_ae_stop_prompt(
    tmp_path: Path,
) -> None:
    gateway = RecordingGateway({})
    exhausted = approved_record(receipts=tuple(receipt() for _ in range(6)))
    store = InvestigationUnitOfWork(
        MarkdownInvestigationRepository(tmp_path / "outputs" / "investigations"),
        SQLiteProjection(tmp_path / "data" / "forge.sqlite3"),
    )
    store.save(exhausted)
    orchestrator = InvestigationOrchestrator(
        store=store,
        specialists=runner(gateway),
        clock=lambda: STARTED,
        lock_root=tmp_path / "data" / "locks",
    )

    stopped = await orchestrator.run_until_checkpoint(exhausted.id)

    assert stopped.prompt.kind is DecisionKind.BUDGET_EXHAUSTED
    assert "call limit" in stopped.error
    assert gateway.requests == []


@pytest.mark.asyncio
async def test_researcher_result_becomes_a_typed_contribution_with_receipt() -> None:
    confidence = {"level": "medium", "rationale": "Requires independent review."}
    gateway = RecordingGateway(
        {
            "epistemic_items": [
                {
                    "id": "epi_initial_premise",
                    "category": "premise",
                    "statement": "The scale reading is relevant.",
                    "uncertainty": confidence,
                    "origin": "Researcher",
                }
            ],
            "unsupported_assumptions": ["The scale is calibrated."],
        }
    )

    contribution = await runner(gateway).run(ModelRole.RESEARCHER, approved_record())

    assert contribution.epistemic_items[0].id == "epi_initial_premise"
    assert contribution.unresolved_questions == ("The scale is calibrated.",)
    assert contribution.model_receipts == (gateway.requests and receipt(),)
    assert gateway.requests[0].max_output_tokens == 1200


@pytest.mark.asyncio
async def test_lead_result_becomes_an_ae_decision_prompt() -> None:
    gateway = RecordingGateway(
        {
            "question": "Which constraint should guide the investigation?",
            "options": [
                {"label": "Energy", "description": "Trace conservation."},
                {"label": "Time", "description": "Inspect timing."},
                {"label": "Information", "description": "Find bottlenecks."},
                {"label": "Materials", "description": "Inspect resource limits."},
            ],
            "recommended_index": 0,
        }
    )

    contribution = await runner(gateway).run(ModelRole.LEAD, approved_record())

    assert contribution.decision_prompt is not None
    assert contribution.decision_prompt.options[-1].accepts_custom_input is True


@pytest.mark.asyncio
async def test_live_orchestrator_uses_lead_for_focus_and_persists_its_receipt(
    tmp_path: Path,
) -> None:
    gateway = RecordingGateway(
        {
            "question": "Which constraint should guide the investigation?",
            "options": [
                {"label": "Energy", "description": "Trace conservation."},
                {"label": "Time", "description": "Inspect timing."},
                {"label": "Information", "description": "Find bottlenecks."},
                {"label": "Materials", "description": "Inspect resource limits."},
            ],
            "recommended_index": 0,
        }
    )
    store = InvestigationUnitOfWork(
        MarkdownInvestigationRepository(tmp_path / "outputs" / "investigations"),
        SQLiteProjection(tmp_path / "data" / "forge.sqlite3"),
    )
    orchestrator = InvestigationOrchestrator(
        store=store,
        specialists=runner(gateway),
        clock=lambda: STARTED,
        lock_root=tmp_path / "data" / "locks",
    )
    confirmation = approved_record().decisions[0]

    focus = await orchestrator.start(
        investigation_id="inv_live",
        seed="Let the Lead frame this question.",
        depth=DepthMode.QUICK,
        at=STARTED,
        live_confirmation=confirmation,
    )

    assert gateway.requests[0].role is ModelRole.LEAD
    assert focus.prompt.question == "Which constraint should guide the investigation?"
    assert focus.record.model_receipts == (receipt(ModelRole.LEAD),)


@pytest.mark.parametrize(
    "failure_kind",
    [
        FailureKind.TIMEOUT,
        FailureKind.RATE_LIMIT,
        FailureKind.MALFORMED_OUTPUT,
        FailureKind.CANCELLED,
    ],
)
@pytest.mark.asyncio
async def test_recoverable_provider_failures_expose_sanitized_failure_and_receipt(
    failure_kind: FailureKind,
) -> None:
    class FailingGateway:
        async def complete(self, request):
            return ModelResult(
                failure_kind=failure_kind,
                failure_message="Model provider call did not complete",
                receipt=receipt(request.role),
            )

    with pytest.raises(LiveSpecialistRunError, match="did not complete") as failure:
        await runner(FailingGateway()).run(ModelRole.RESEARCHER, approved_record())

    assert failure.value.failure_kind is failure_kind
    assert failure.value.receipt.role is ModelRole.RESEARCHER


@pytest.mark.asyncio
async def test_semantically_invalid_provider_output_becomes_a_recoverable_failure() -> None:
    confidence = {"level": "medium", "rationale": "Requires independent review."}
    gateway = RecordingGateway(
        {
            "connections": [
                {
                    "id": "epi_invalid_connection",
                    "category": "exploratory_item",
                    "statement": "A possible connection with an invalid local basis.",
                    "uncertainty": confidence,
                    "provenance": {"origin": "Connection Finder"},
                    "exploratory_type": "connection",
                    "based_on": ["epi_missing_basis"],
                }
            ]
        }
    )

    with pytest.raises(
        LiveSpecialistRunError,
        match="connection_finder output failed validation",
    ) as failure:
        await runner(gateway).run(ModelRole.CONNECTION_FINDER, approved_record())

    assert failure.value.failure_kind is FailureKind.MALFORMED_OUTPUT
    assert failure.value.receipt.role is ModelRole.CONNECTION_FINDER
    assert "epi_missing_basis" not in str(failure.value)


@pytest.mark.asyncio
async def test_live_failure_persists_receipt_and_retries_from_an_ae_recovery_prompt(
    tmp_path: Path,
) -> None:
    lead_output = {
        "question": "Which constraint should guide the investigation?",
        "options": [
            {"label": "Energy", "description": "Trace conservation."},
            {"label": "Time", "description": "Inspect timing."},
            {"label": "Information", "description": "Find bottlenecks."},
            {"label": "Materials", "description": "Inspect resource limits."},
        ],
        "recommended_index": 0,
    }

    class FlakyGateway:
        def __init__(self) -> None:
            self.calls = 0

        async def complete(self, request):
            self.calls += 1
            if self.calls == 1:
                return ModelResult(
                    failure_kind=FailureKind.TIMEOUT,
                    failure_message="Model provider timed out",
                    receipt=receipt(request.role),
                )
            return ModelResult(output=lead_output, receipt=receipt(request.role))

    gateway = FlakyGateway()
    store = InvestigationUnitOfWork(
        MarkdownInvestigationRepository(tmp_path / "outputs" / "investigations"),
        SQLiteProjection(tmp_path / "data" / "forge.sqlite3"),
    )
    orchestrator = InvestigationOrchestrator(
        store=store,
        specialists=runner(gateway),
        clock=lambda: STARTED,
        lock_root=tmp_path / "data" / "locks",
    )
    failed = await orchestrator.start(
        investigation_id="inv_live",
        seed="Retry without losing the failed receipt.",
        depth=DepthMode.QUICK,
        at=STARTED,
        live_confirmation=approved_record().decisions[0],
    )

    assert failed.prompt.kind is DecisionKind.RECOVERY
    assert failed.record.workflow.stage.value == "seeded"
    assert failed.record.model_receipts == (receipt(ModelRole.LEAD),)
    assert "timed out" in failed.error

    focus = await orchestrator.submit_decision(
        failed.record.id,
        prompt_id=failed.prompt.id,
        raw_choice="A",
    )

    assert focus.prompt.kind is DecisionKind.FOCUS_CHECKPOINT
    assert len(focus.record.model_receipts) == 2
    assert gateway.calls == 2


@pytest.mark.asyncio
async def test_quick_live_orchestration_completes_with_six_bounded_role_calls(
    tmp_path: Path,
) -> None:
    confidence = {"level": "medium", "rationale": "Requires independent verification."}
    outputs = {
        ModelRole.LEAD: {
            "question": "Which constraint should guide the investigation?",
            "options": [
                {"label": "Energy", "description": "Trace conservation."},
                {"label": "Time", "description": "Inspect timing."},
                {"label": "Information", "description": "Find bottlenecks."},
                {"label": "Materials", "description": "Inspect resource limits."},
            ],
            "recommended_index": 0,
        },
        ModelRole.RESEARCHER: {
            "epistemic_items": [
                {
                    "id": "epi_constraint_premise",
                    "category": "premise",
                    "statement": "The system has a binding constraint.",
                    "uncertainty": confidence,
                    "origin": "Researcher",
                }
            ],
            "unsupported_assumptions": [],
        },
        ModelRole.CONNECTION_FINDER: {
            "connections": [
                {
                    "id": "epi_constraint_connection",
                    "category": "exploratory_item",
                    "statement": "Queues may share the same saturation structure.",
                    "uncertainty": confidence,
                    "provenance": {"origin": "Connection Finder"},
                    "exploratory_type": "connection",
                    "based_on": ["epi_constraint_premise"],
                }
            ]
        },
        ModelRole.SYNTHESIZER: {
            "hypotheses": [
                {
                    "id": "epi_variance_hypothesis",
                    "category": "exploratory_item",
                    "statement": "Lower variance may delay saturation.",
                    "uncertainty": confidence,
                    "provenance": {"origin": "Synthesizer"},
                    "exploratory_type": "hypothesis",
                    "based_on": ["epi_constraint_connection"],
                }
            ],
            "alternative_explanations": [
                {
                    "id": "epi_capacity_alternative",
                    "category": "exploratory_item",
                    "statement": "Absolute capacity may dominate variance.",
                    "uncertainty": confidence,
                    "provenance": {"origin": "Synthesizer"},
                    "exploratory_type": "interpretation",
                    "based_on": ["epi_constraint_connection"],
                }
            ],
        },
        ModelRole.SKEPTIC: {
            "challenges": [
                {
                    "target_id": "epi_variance_hypothesis",
                    "challenge": "Capacity provides a competing explanation.",
                    "disposition": "revise",
                    "rationale": "Hold capacity constant in the test.",
                }
            ]
        },
        ModelRole.EXPERIMENT_DESIGNER: {
            "proposal": {
                "statement": "Compare equal-load queues with different variance.",
                "procedure": "Run two bounded simulations while holding capacity constant.",
                "expected_observation": "Lower variance delays saturation.",
                "disconfirming_observation": "Saturation timing remains unchanged.",
                "cost": "Two simulations.",
                "risk": "The simulation may not generalize.",
                "stopping_condition": "Stop after three stable seeded runs.",
                "reproducibility_needs": "Record code, inputs, seeds, and outputs.",
            },
            "no_responsible_test_reason": None,
        },
    }

    class RoleGateway:
        def __init__(self) -> None:
            self.requests = []

        async def complete(self, request):
            self.requests.append(request)
            return ModelResult(output=outputs[request.role], receipt=receipt(request.role))

    gateway = RoleGateway()
    store = InvestigationUnitOfWork(
        MarkdownInvestigationRepository(tmp_path / "outputs" / "investigations"),
        SQLiteProjection(tmp_path / "data" / "forge.sqlite3"),
    )
    orchestrator = InvestigationOrchestrator(
        store=store,
        specialists=runner(gateway),
        clock=lambda: STARTED,
        lock_root=tmp_path / "data" / "locks",
    )
    focus = await orchestrator.start(
        investigation_id="inv_live",
        seed="Trace saturation from first principles.",
        depth=DepthMode.QUICK,
        at=STARTED,
        live_confirmation=approved_record().decisions[0],
    )
    evidence = await orchestrator.submit_decision(
        focus.record.id, prompt_id=focus.prompt.id, raw_choice="A"
    )
    action = await orchestrator.submit_decision(
        evidence.record.id, prompt_id=evidence.prompt.id, raw_choice="A"
    )
    completed = await orchestrator.submit_decision(
        action.record.id, prompt_id=action.prompt.id, raw_choice="A"
    )

    assert completed.record.workflow.stage.value == "completed"
    assert [request.role for request in gateway.requests] == list(ModelRole)
    assert len(completed.record.model_receipts) == 6
    assert completed.record.selected_action.procedure
    assert completed.record.selected_action.reproducibility_needs
