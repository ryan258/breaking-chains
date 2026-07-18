"""Shared local runtime assembly for the CLI and Streamlit adapters."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from forge.application.budgets import BudgetPolicy, DepthBudget
from forge.application.orchestrator import InvestigationOrchestrator
from forge.application.specialists import LiveSpecialistRunner
from forge.config import ForgeSettings
from forge.gateways.fake import DeterministicSpecialistRunner
from forge.gateways.model import ModelRole
from forge.gateways.openrouter import OpenRouterGateway
from forge.observability.trace import TraceWriter
from forge.persistence.markdown import MarkdownInvestigationRepository
from forge.persistence.sqlite import SQLiteProjection
from forge.persistence.unit_of_work import InvestigationUnitOfWork


def repository(settings: ForgeSettings) -> MarkdownInvestigationRepository:
    """Return the canonical record repository used by every local adapter."""

    return MarkdownInvestigationRepository(settings.output_dir / "investigations")


def budget_policy(settings: ForgeSettings) -> BudgetPolicy:
    """Build immutable depth budgets from validated configuration."""

    return BudgetPolicy(
        quick=DepthBudget(
            max_calls=settings.quick_max_calls,
            max_output_tokens_per_call=settings.quick_max_output_tokens_per_call,
        ),
        standard=DepthBudget(
            max_calls=settings.standard_max_calls,
            max_output_tokens_per_call=settings.standard_max_output_tokens_per_call,
        ),
        deep=DepthBudget(
            max_calls=settings.deep_max_calls,
            max_output_tokens_per_call=settings.deep_max_output_tokens_per_call,
        ),
    )


def _models(settings: ForgeSettings) -> dict[ModelRole, str]:
    return {
        ModelRole.LEAD: settings.model_lead,
        ModelRole.RESEARCHER: settings.model_researcher,
        ModelRole.CONNECTION_FINDER: settings.model_connection_finder,
        ModelRole.SYNTHESIZER: settings.model_synthesizer,
        ModelRole.SKEPTIC: settings.model_skeptic,
        ModelRole.EXPERIMENT_DESIGNER: settings.model_experiment_designer,
    }


def _orchestrator(settings: ForgeSettings, specialists) -> InvestigationOrchestrator:
    unit_of_work = InvestigationUnitOfWork(
        repository(settings),
        SQLiteProjection(settings.data_dir / "forge.sqlite3"),
    )
    return InvestigationOrchestrator(
        store=unit_of_work,
        specialists=specialists,
        clock=lambda: datetime.now(UTC),
        lock_root=settings.data_dir / "locks",
    )


@asynccontextmanager
async def orchestrator_context(
    settings: ForgeSettings,
    *,
    live: bool,
) -> AsyncIterator[InvestigationOrchestrator]:
    """Open the shared deterministic or live local application runtime."""

    if not live:
        yield _orchestrator(settings, DeterministicSpecialistRunner())
        return
    trace = TraceWriter(
        log_root=settings.log_dir,
        output_root=settings.output_dir,
        secret_values=(settings.openrouter_api_key.get_secret_value(),),
    )
    async with OpenRouterGateway(
        api_key=settings.openrouter_api_key.get_secret_value(),
        base_url=str(settings.openrouter_base_url),
        trace=trace,
    ) as gateway:
        specialists = LiveSpecialistRunner(
            gateway=gateway,
            models=_models(settings),
            budgets=budget_policy(settings),
        )
        yield _orchestrator(settings, specialists)


__all__ = ["budget_policy", "orchestrator_context", "repository"]
