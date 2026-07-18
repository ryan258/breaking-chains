import json
from datetime import UTC, datetime
from pathlib import Path

from forge.gateways.model import ModelReceipt, ModelRole, ModelUsage
from forge.ui.services import load_quarantined_model_response


def receipt(artifact_path: Path) -> ModelReceipt:
    at = datetime(2026, 7, 18, tzinfo=UTC)
    return ModelReceipt(
        role=ModelRole.CONNECTION_FINDER,
        model="vendor/model",
        started_at=at,
        finished_at=at,
        duration_ms=0,
        attempts=1,
        usage=ModelUsage(),
        prompt_contract_version="connection-finder-v1",
        artifact_path=artifact_path,
    )


def test_loads_only_the_quarantined_assistant_response(tmp_path: Path) -> None:
    output_dir = tmp_path / "outputs"
    artifact_path = output_dir / "model-calls/inv_review/call_invalid.json"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text(
        json.dumps(
            {
                "request": {"messages": [{"content": "private prompt"}]},
                "response": {"choices": [{"message": {"content": '<script>alert("no")</script>'}}]},
            }
        ),
        encoding="utf-8",
    )

    response = load_quarantined_model_response(
        output_dir=output_dir,
        investigation_id="inv_review",
        receipt=receipt(artifact_path),
    )

    assert response == '<script>alert("no")</script>'
    assert "private prompt" not in response


def test_rejects_quarantine_artifact_outside_the_investigation_directory(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "outputs"
    outside = tmp_path / "other-investigation.json"
    outside.write_text(
        json.dumps({"response": {"choices": [{"message": {"content": "do not show"}}]}}),
        encoding="utf-8",
    )

    response = load_quarantined_model_response(
        output_dir=output_dir,
        investigation_id="inv_review",
        receipt=receipt(outside),
    )

    assert response is None
