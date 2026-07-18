"""Typer command adapter over the shared application core."""

import asyncio
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

import typer

from forge.application.orchestrator import InvestigationOrchestrator, OrchestrationView
from forge.config import ConfigurationError, ForgeSettings, load_settings
from forge.domain.investigation import DepthMode, WorkflowStatus
from forge.gateways.fake import DeterministicSpecialistRunner
from forge.persistence.markdown import MarkdownInvestigationRepository
from forge.persistence.sqlite import SQLiteProjection
from forge.persistence.unit_of_work import InvestigationUnitOfWork

app = typer.Typer(add_completion=False, help="First-principles discovery forge.")


def _settings() -> ForgeSettings:
    try:
        return load_settings()
    except ConfigurationError as error:
        typer.echo(str(error))
        raise typer.Exit(1) from None


def _repository(settings: ForgeSettings) -> MarkdownInvestigationRepository:
    return MarkdownInvestigationRepository(settings.output_dir / "investigations")


def _orchestrator(settings: ForgeSettings) -> InvestigationOrchestrator:
    unit_of_work = InvestigationUnitOfWork(
        _repository(settings),
        SQLiteProjection(settings.data_dir / "forge.sqlite3"),
    )
    # ponytail: deterministic specialists until the OpenRouter runner and
    # budget enforcement land together; no paid calls happen through the CLI yet.
    return InvestigationOrchestrator(
        store=unit_of_work,
        specialists=DeterministicSpecialistRunner(),
        clock=lambda: datetime.now(UTC),
        lock_root=settings.data_dir / "locks",
    )


def _drive(orchestrator: InvestigationOrchestrator, view: OrchestrationView) -> None:
    """Present each pending A-E question until the investigation stops."""

    while view.prompt is not None:
        prompt = view.prompt
        typer.echo(f"\n{prompt.question}")
        for option in prompt.options:
            marker = " (recommended)" if option.is_recommended else ""
            typer.echo(f"  {option.letter.value}. {option.label}{marker}")
        raw_choice = typer.prompt("Choose A-E")
        custom_answer = None
        if raw_choice.strip().upper() == "E":
            custom_answer = typer.prompt("Custom answer")
        view = asyncio.run(
            orchestrator.submit_decision(
                view.record.id,
                prompt_id=prompt.id,
                raw_choice=raw_choice,
                custom_answer=custom_answer,
            )
        )
        if view.error is not None:
            typer.echo(view.error)

    record = view.record
    typer.echo(f"\n{record.id}: {record.workflow.stage.value} ({record.workflow.status.value})")
    if record.workflow.status is WorkflowStatus.PAUSED:
        typer.echo(f"Resume later with: forge resume {record.id}")


@app.command()
def investigate(
    seed: Annotated[str, typer.Option("--seed", prompt="Investigation seed")],
    mode: Annotated[DepthMode | None, typer.Option("--mode")] = None,
) -> None:
    """Start a new investigation from a short seed."""

    settings = _settings()
    depth = mode or settings.default_depth
    investigation_id = f"inv_{uuid4().hex}"
    typer.echo(f"Starting {investigation_id} in {depth.value} mode.")
    orchestrator = _orchestrator(settings)
    view = asyncio.run(
        orchestrator.start(
            investigation_id=investigation_id,
            seed=seed,
            depth=depth,
            at=datetime.now(UTC),
        )
    )
    _drive(orchestrator, view)


@app.command()
def resume(investigation_id: str) -> None:
    """Resume a paused investigation from its last saved state."""

    settings = _settings()
    orchestrator = _orchestrator(settings)
    view = asyncio.run(orchestrator.resume(investigation_id))
    _drive(orchestrator, view)


@app.command("list")
def list_investigations(
    status: Annotated[WorkflowStatus | None, typer.Option("--status")] = None,
) -> None:
    """List saved investigations from the canonical Markdown records."""

    settings = _settings()
    records = _repository(settings).list_records()
    shown = 0
    for record in records:
        workflow = record.workflow
        if status is not None and workflow.status is not status:
            continue
        shown += 1
        typer.echo(
            f"{record.id}  {workflow.depth.value}  {workflow.stage.value}  "
            f"{workflow.status.value}  {record.seed[:60]}"
        )
    if shown == 0:
        typer.echo("No investigations found.")


@app.command("config-check")
def config_check() -> None:
    """Validate configuration without revealing secrets."""

    _settings()
    typer.echo("Configuration OK.")


if __name__ == "__main__":
    app()
