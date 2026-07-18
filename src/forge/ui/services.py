"""Streamlit-facing calls into shared application services."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from forge.application.decisions import (
    ChoiceLetter,
    DecisionAttempt,
    DecisionPrompt,
    submit_decision,
)
from forge.application.orchestrator import OrchestrationView
from forge.application.runtime import orchestrator_context
from forge.application.source_ingestion import SourceImportError, import_local_source
from forge.config import ForgeSettings
from forge.domain.investigation import DepthMode
from forge.gateways.model import ModelReceipt
from forge.persistence.metadata import InvestigationRecord, LocalSourceReference

_MAX_QUARANTINE_ARTIFACT_BYTES = 1_000_000


def run(awaitable) -> OrchestrationView:
    """Run one bounded application operation for a Streamlit interaction."""

    return asyncio.run(awaitable)


def load_quarantined_model_response(
    *,
    output_dir: Path,
    investigation_id: str,
    receipt: ModelReceipt,
) -> str | None:
    """Read only a rejected assistant response from its private local artifact."""

    artifact_root = (output_dir / "model-calls" / investigation_id).resolve()
    artifact_path = receipt.artifact_path.resolve()
    try:
        artifact_path.relative_to(artifact_root)
    except ValueError:
        return None
    try:
        if (
            not artifact_path.is_file()
            or artifact_path.stat().st_size > _MAX_QUARANTINE_ARTIFACT_BYTES
        ):
            return None
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        choices = artifact["response"]["choices"]
        content = choices[0]["message"]["content"]
    except (OSError, json.JSONDecodeError, KeyError, IndexError, TypeError):
        return None
    return content if isinstance(content, str) and content else None


async def start_investigation(
    settings: ForgeSettings,
    *,
    investigation_id: str,
    seed: str,
    depth: DepthMode,
    source_reference: LocalSourceReference | None,
    prior_investigation_ids: tuple[str, ...],
    preflight_decisions: tuple[DecisionAttempt, ...],
    prompt: DecisionPrompt,
    choice: ChoiceLetter,
) -> OrchestrationView:
    live = choice is ChoiceLetter.A
    async with orchestrator_context(settings, live=live) as orchestrator:
        return await orchestrator.start(
            investigation_id=investigation_id,
            seed=seed,
            depth=depth,
            at=datetime.now(UTC),
            source_reference=source_reference,
            prior_investigation_ids=prior_investigation_ids,
            preflight_decisions=preflight_decisions,
            live_confirmation=submit_decision(prompt, choice),
        )


async def submit_record_decision(
    settings: ForgeSettings,
    record: InvestigationRecord,
    choice: ChoiceLetter,
    custom: str | None = None,
) -> OrchestrationView:
    assert record.pending_decision is not None
    async with orchestrator_context(settings, live=record.live_execution_approved) as orchestrator:
        return await orchestrator.submit_decision(
            record.id,
            prompt_id=record.pending_decision.id,
            raw_choice=choice,
            custom_answer=custom,
        )


async def resume_investigation(
    settings: ForgeSettings,
    record: InvestigationRecord,
) -> OrchestrationView:
    async with orchestrator_context(settings, live=record.live_execution_approved) as orchestrator:
        return await orchestrator.resume(record.id)


async def confirm_and_resume_live(
    settings: ForgeSettings,
    record: InvestigationRecord,
    prompt: DecisionPrompt,
) -> OrchestrationView:
    confirmation = submit_decision(prompt, ChoiceLetter.A)
    async with orchestrator_context(settings, live=True) as orchestrator:
        await orchestrator.record_live_confirmation(record.id, confirmation)
        return await orchestrator.resume(record.id)


def cache_uploaded_source(settings: ForgeSettings, uploaded) -> LocalSourceReference | None:
    """Persist an uploaded local source privately so later consent remains resumable."""

    if uploaded is None:
        return None
    suffix = Path(uploaded.name).suffix.lower()
    upload_root = settings.data_dir / "sources"
    upload_root.mkdir(parents=True, exist_ok=True)
    target = upload_root / f"source_{uuid4().hex}{suffix}"
    target.write_bytes(uploaded.getvalue())
    target.chmod(0o600)
    try:
        return import_local_source(target).reference
    except SourceImportError:
        target.unlink(missing_ok=True)
        raise


__all__ = [
    "cache_uploaded_source",
    "confirm_and_resume_live",
    "load_quarantined_model_response",
    "resume_investigation",
    "run",
    "start_investigation",
    "submit_record_decision",
]
