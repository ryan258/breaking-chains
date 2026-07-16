from datetime import UTC, datetime
from pathlib import Path

from forge.gateways.model import (
    ModelReceipt,
    ModelResult,
    ModelRole,
    ModelUsage,
)
from forge.smoke_report import render_smoke_report


def test_renders_successful_model_smoke_as_readable_markdown() -> None:
    moment = datetime(2026, 7, 16, tzinfo=UTC)
    result = ModelResult(
        output={
            "observation": "Constraints reveal structure.",
            "connection": "Scarcity links design and biology.",
            "uncertainty": "Needs testing.",
        },
        receipt=ModelReceipt(
            role=ModelRole.LEAD,
            model="vendor/free-model",
            started_at=moment,
            finished_at=moment,
            duration_ms=25,
            attempts=1,
            usage=ModelUsage(prompt_tokens=10, completion_tokens=8, total_tokens=18, cost=0),
            prompt_contract_version="smoke-v1",
            artifact_path=Path("outputs/model-calls/smoke/call.json"),
        ),
    )

    markdown = render_smoke_report(result)

    assert "# OpenRouter Smoke Investigation" in markdown
    assert "Constraints reveal structure." in markdown
    assert "Scarcity links design and biology." in markdown
    assert "Needs testing." in markdown
    assert "vendor/free-model" in markdown
    assert "outputs/model-calls/smoke/call.json" in markdown
