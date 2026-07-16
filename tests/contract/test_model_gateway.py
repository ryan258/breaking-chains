from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from forge.domain.identifiers import new_call_id
from forge.gateways.model import (
    FailureKind,
    ModelMessage,
    ModelReceipt,
    ModelRequest,
    ModelResult,
    ModelRole,
    ModelUsage,
)


def receipt() -> ModelReceipt:
    started = datetime(2026, 7, 16, tzinfo=UTC)
    return ModelReceipt(
        role=ModelRole.LEAD,
        model="vendor/model",
        started_at=started,
        finished_at=started + timedelta(milliseconds=5),
        duration_ms=5,
        attempts=1,
        usage=ModelUsage(),
        prompt_contract_version="1",
        artifact_path=Path("outputs/call.json"),
    )


def test_result_requires_exactly_one_success_or_failure_state() -> None:
    with pytest.raises(ValidationError):
        ModelResult(output={"answer": "yes"}, failure_kind=FailureKind.TIMEOUT, receipt=receipt())
    with pytest.raises(ValidationError):
        ModelResult(receipt=receipt())


def test_usage_rejects_negative_values() -> None:
    with pytest.raises(ValidationError):
        ModelUsage(total_tokens=-1)
    with pytest.raises(ValidationError):
        ModelUsage(cost=-0.01)


def test_receipt_rejects_naive_or_reversed_timestamps() -> None:
    valid = receipt()
    with pytest.raises(ValidationError):
        ModelReceipt(**{**valid.model_dump(), "started_at": datetime(2026, 7, 16)})
    with pytest.raises(ValidationError):
        ModelReceipt(
            **{**valid.model_dump(), "finished_at": valid.started_at - timedelta(seconds=1)}
        )


def test_request_uses_safe_ids_and_contains_no_provider_wire_fields() -> None:
    request = ModelRequest(
        investigation_id="inv_contract",
        call_id="call_contract",
        role=ModelRole.LEAD,
        model="vendor/model",
        messages=(ModelMessage(role="user", content="test"),),
        output_schema={"type": "object"},
        output_schema_name="result",
        max_output_tokens=100,
        prompt_contract_version="1",
    )

    fields = request.model_dump()
    assert "authorization" not in fields
    assert "response_format" not in fields
    with pytest.raises(ValidationError):
        ModelRequest.model_validate({**fields, "investigation_id": "../../escape"})


def test_generated_call_id_satisfies_safe_request_contract() -> None:
    generated = new_call_id()

    assert generated.startswith("call_")
    assert generated == generated.lower()
    assert len(generated) <= 65
