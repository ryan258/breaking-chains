"""Live specialist execution behind approval, budgets, and role contracts."""

from collections.abc import Mapping
from dataclasses import replace

from pydantic import ValidationError

from forge.application.budgets import BudgetExceeded, BudgetPolicy
from forge.application.decisions import ChoiceLetter, DecisionKind
from forge.application.orchestrator import SpecialistContribution, SpecialistExecutionError
from forge.domain.identifiers import new_call_id
from forge.gateways.model import FailureKind, ModelGateway, ModelReceipt, ModelRole
from forge.persistence.metadata import ActionProposal, InvestigationRecord
from forge.roles.connection_finder import build_connection_request, parse_connection_output
from forge.roles.experiment_designer import build_experiment_request, parse_experiment_output
from forge.roles.lead import build_lead_request, parse_lead_output
from forge.roles.researcher import build_researcher_request, parse_researcher_output
from forge.roles.skeptic import build_skeptic_request, parse_skeptic_output
from forge.roles.synthesizer import build_synthesizer_request, parse_synthesizer_output


class LiveSpecialistRunError(SpecialistExecutionError):
    """A sanitized provider failure with its durable call receipt."""

    def __init__(
        self,
        message: str,
        *,
        failure_kind: FailureKind,
        receipt: ModelReceipt,
        prior_receipts: tuple[ModelReceipt, ...] = (),
    ) -> None:
        super().__init__(
            message,
            failure_kind=failure_kind,
            receipt=receipt,
            prior_receipts=prior_receipts,
        )


class LiveSpecialistRunner:
    """Execute one configured role only after approval and hard-budget checks."""

    def __init__(
        self,
        *,
        gateway: ModelGateway,
        models: Mapping[ModelRole, str],
        budgets: BudgetPolicy,
    ) -> None:
        missing_roles = set(ModelRole) - set(models)
        if missing_roles:
            raise ValueError("every model role requires a configured model")
        self._gateway = gateway
        self._models = dict(models)
        self._budgets = budgets

    async def run(
        self,
        role: ModelRole,
        record: InvestigationRecord,
    ) -> SpecialistContribution:
        if not record.live_execution_approved:
            raise PermissionError("live model execution is not approved for this investigation")
        budget = self._budgets.for_depth(record.workflow.depth)
        approved_batches = sum(
            1
            for decision in record.decisions
            if decision.prompt.kind is DecisionKind.LIVE_CONFIRMATION
            and decision.selection is not None
            and decision.selection.letter is ChoiceLetter.A
        )
        calls_used_in_current_batch = max(
            0,
            len(record.model_receipts) - budget.max_calls * (approved_batches - 1),
        )
        # One silent retry per stage: a single flaky call should not cost the
        # user a recovery question, but every attempt stays budgeted on record.
        last_error: LiveSpecialistRunError | None = None
        failed_receipts: tuple[ModelReceipt, ...] = ()
        for attempt_offset in range(2):
            try:
                budget.assert_call_allowed(
                    calls_used=calls_used_in_current_batch + attempt_offset,
                    requested_output_tokens=budget.max_output_tokens_per_call,
                )
            except BudgetExceeded:
                if last_error is not None:
                    raise last_error from None
                raise
            request = self._build_request(
                role,
                record,
                call_id=new_call_id(),
                max_output_tokens=budget.max_output_tokens_per_call,
            )
            result = await self._gateway.complete(request)
            if not result.is_success:
                assert result.failure_kind is not None
                last_error = LiveSpecialistRunError(
                    result.failure_message or "Live specialist call failed",
                    failure_kind=result.failure_kind,
                    receipt=result.receipt,
                    prior_receipts=failed_receipts,
                )
                if result.failure_kind is FailureKind.INVALID_REQUEST:
                    raise last_error
                failed_receipts = (*failed_receipts, result.receipt)
                continue
            assert result.output is not None
            try:
                contribution = self._parse_contribution(role, result.output, record, result.receipt)
            except (ValidationError, ValueError) as error:
                last_error = LiveSpecialistRunError(
                    f"Model provider {role.value} output failed validation.",
                    failure_kind=FailureKind.MALFORMED_OUTPUT,
                    receipt=result.receipt,
                    prior_receipts=failed_receipts,
                )
                last_error.__cause__ = error
                failed_receipts = (*failed_receipts, result.receipt)
                continue
            if failed_receipts:
                contribution = replace(
                    contribution,
                    model_receipts=(*failed_receipts, *contribution.model_receipts),
                )
            return contribution
        assert last_error is not None
        raise last_error

    def _build_request(
        self,
        role: ModelRole,
        record: InvestigationRecord,
        *,
        call_id: str,
        max_output_tokens: int,
    ):
        builders = {
            ModelRole.LEAD: build_lead_request,
            ModelRole.RESEARCHER: build_researcher_request,
            ModelRole.CONNECTION_FINDER: build_connection_request,
            ModelRole.SYNTHESIZER: build_synthesizer_request,
            ModelRole.SKEPTIC: build_skeptic_request,
            ModelRole.EXPERIMENT_DESIGNER: build_experiment_request,
        }
        return builders[role](
            record,
            model=self._models[role],
            call_id=call_id,
            max_output_tokens=max_output_tokens,
        )

    @staticmethod
    def _parse_contribution(
        role: ModelRole,
        output: object,
        record: InvestigationRecord,
        receipt: ModelReceipt,
    ) -> SpecialistContribution:
        receipts = (receipt,)
        if role is ModelRole.LEAD:
            return SpecialistContribution(
                decision_prompt=parse_lead_output(output, investigation_id=record.id),
                model_receipts=receipts,
            )
        if role is ModelRole.RESEARCHER:
            parsed = parse_researcher_output(output, record=record)
            return SpecialistContribution(
                epistemic_items=parsed.epistemic_items,
                unresolved_questions=parsed.unsupported_assumptions,
                model_receipts=receipts,
            )
        if role is ModelRole.CONNECTION_FINDER:
            parsed = parse_connection_output(output, record=record)
            return SpecialistContribution(
                epistemic_items=parsed.connections,
                model_receipts=receipts,
            )
        if role is ModelRole.SYNTHESIZER:
            parsed = parse_synthesizer_output(output, record=record)
            return SpecialistContribution(
                epistemic_items=(*parsed.hypotheses, *parsed.alternative_explanations),
                model_receipts=receipts,
            )
        if role is ModelRole.SKEPTIC:
            parsed = parse_skeptic_output(output, record=record)
            return SpecialistContribution(
                skeptical_challenges=parsed.challenges,
                model_receipts=receipts,
            )
        parsed = parse_experiment_output(output)
        action = None
        unresolved = ()
        if parsed.proposal is not None:
            action = ActionProposal(**parsed.proposal.model_dump())
        else:
            unresolved = (parsed.no_responsible_test_reason,)
        return SpecialistContribution(
            selected_action=action,
            unresolved_questions=unresolved,
            model_receipts=receipts,
        )


__all__ = ["LiveSpecialistRunError", "LiveSpecialistRunner"]
