import asyncio
import json
from pathlib import Path

import httpx
import pytest

from forge.gateways.model import FailureKind, ModelMessage, ModelRequest, ModelRole
from forge.gateways.openrouter import OpenRouterGateway
from forge.observability.trace import TraceWriter


def request() -> ModelRequest:
    return ModelRequest(
        investigation_id="inv_gateway",
        call_id="call_01",
        role=ModelRole.SKEPTIC,
        model="vendor/free-model",
        messages=(ModelMessage(role="user", content="Test the claim"),),
        output_schema={
            "type": "object",
            "properties": {"verdict": {"type": "string"}},
            "required": ["verdict"],
            "additionalProperties": False,
        },
        output_schema_name="skeptic_result",
        max_output_tokens=100,
        prompt_contract_version="1",
    )


def gateway(tmp_path: Path, handler: httpx.AsyncBaseTransport, *, retries: int = 1):
    trace = TraceWriter(
        log_root=tmp_path / "logs",
        output_root=tmp_path / "outputs",
        secret_values=("test-secret",),
    )
    client = httpx.AsyncClient(transport=handler)
    return OpenRouterGateway(
        api_key="test-secret",
        base_url="https://openrouter.test/api/v1",
        trace=trace,
        client=client,
        max_retries=retries,
        retry_delay_seconds=0,
    ), client


@pytest.mark.asyncio
async def test_maps_success_and_writes_trace_artifact(tmp_path: Path) -> None:
    async def handler(incoming: httpx.Request) -> httpx.Response:
        assert incoming.headers["authorization"] == "Bearer test-secret"
        body = json.loads(incoming.content)
        assert body["response_format"]["json_schema"]["strict"] is True
        return httpx.Response(
            200,
            json={
                "id": "gen_01",
                "model": "vendor/free-model",
                "choices": [{"message": {"role": "assistant", "content": '{"verdict":"weak"}'}}],
                "usage": {
                    "prompt_tokens": 11,
                    "completion_tokens": 4,
                    "total_tokens": 15,
                    "cost": 0,
                },
            },
        )

    transport, client = gateway(tmp_path, httpx.MockTransport(handler))
    try:
        result = await transport.complete(request())
    finally:
        await client.aclose()

    assert result.is_success
    assert result.output == {"verdict": "weak"}
    assert result.receipt.attempts == 1
    assert result.receipt.usage.total_tokens == 15
    assert result.receipt.usage.cost == 0
    assert result.receipt.prompt_contract_version == "1"
    assert result.receipt.finished_at >= result.receipt.started_at
    assert result.receipt.duration_ms >= 0
    assert result.receipt.artifact_path.is_file()
    assert "test-secret" not in result.receipt.artifact_path.read_text(encoding="utf-8")
    events = (tmp_path / "logs/forge.jsonl").read_text(encoding="utf-8")
    assert "model_call_started" in events
    assert "model_call_attempt_started" in events
    assert "model_call_succeeded" in events
    assert "Test the claim" not in events
    assert "test-secret" not in events
    assert (result.receipt.artifact_path.stat().st_mode & 0o777) == 0o600
    assert ((tmp_path / "logs/forge.jsonl").stat().st_mode & 0o777) == 0o600


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            httpx.Response(
                200,
                json={
                    "id": "gen_bad",
                    "model": "vendor/free-model",
                    "choices": [{"message": {"role": "assistant", "content": "not-json"}}],
                },
            ),
            FailureKind.MALFORMED_OUTPUT,
        ),
        (
            httpx.Response(400, json={"error": {"code": 400, "message": "bad request"}}),
            FailureKind.PROVIDER_ERROR,
        ),
        (
            httpx.Response(
                200,
                json={
                    "error": {
                        "code": 503,
                        "message": "provider unavailable",
                        "metadata": {"error_type": "provider_unavailable"},
                    }
                },
            ),
            FailureKind.PROVIDER_ERROR,
        ),
    ],
)
async def test_maps_nontransient_failures(
    tmp_path: Path, response: httpx.Response, expected: FailureKind
) -> None:
    transport, client = gateway(tmp_path, httpx.MockTransport(lambda _: response))
    try:
        result = await transport.complete(request())
    finally:
        await client.aclose()

    assert not result.is_success
    assert result.failure_kind is expected
    assert result.receipt.attempts == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("first", "expected"),
    [
        (httpx.ReadTimeout("late"), FailureKind.TIMEOUT),
        (httpx.ConnectError("offline"), FailureKind.NETWORK),
        (
            httpx.Response(429, json={"error": {"code": 429, "message": "slow"}}),
            FailureKind.RATE_LIMIT,
        ),
        (
            httpx.Response(503, json={"error": {"code": 503, "message": "down"}}),
            FailureKind.PROVIDER_ERROR,
        ),
    ],
)
async def test_retries_transient_failures(
    tmp_path: Path, first: Exception | httpx.Response, expected: FailureKind
) -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if isinstance(first, Exception):
            raise first
        return first

    transport, client = gateway(tmp_path, httpx.MockTransport(handler), retries=1)
    try:
        result = await transport.complete(request())
    finally:
        await client.aclose()

    assert not result.is_success
    assert result.failure_kind is expected
    assert result.receipt.attempts == 2
    assert attempts == 2
    assert "model_call_retrying" in (tmp_path / "logs/forge.jsonl").read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_maps_cancellation_to_durable_result(tmp_path: Path) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise asyncio.CancelledError

    transport, client = gateway(tmp_path, httpx.MockTransport(handler))
    try:
        result = await transport.complete(request())
    finally:
        await client.aclose()

    assert result.failure_kind is FailureKind.CANCELLED
    assert result.receipt.attempts == 1
    assert result.receipt.artifact_path.is_file()
    assert "model_call_cancelled" in (tmp_path / "logs/forge.jsonl").read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_rejects_invalid_schema_before_http_call(tmp_path: Path) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    transport, client = gateway(tmp_path, httpx.MockTransport(handler))
    invalid = request().model_copy(update={"output_schema": {"type": "not-a-json-type"}})
    try:
        result = await transport.complete(invalid)
    finally:
        await client.aclose()

    assert result.failure_kind is FailureKind.INVALID_REQUEST
    assert result.receipt.attempts == 0
    assert calls == 0


@pytest.mark.asyncio
async def test_rejects_non_json_schema_without_crashing_or_calling_http(tmp_path: Path) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    transport, client = gateway(tmp_path, httpx.MockTransport(handler))
    invalid = request().model_copy(update={"output_schema": {"x": {1}}})
    try:
        result = await transport.complete(invalid)
    finally:
        await client.aclose()

    assert result.failure_kind is FailureKind.INVALID_REQUEST
    assert result.receipt.attempts == 0
    assert result.receipt.artifact_path.is_file()
    assert calls == 0


@pytest.mark.asyncio
async def test_retains_usage_when_structured_output_is_malformed(tmp_path: Path) -> None:
    response = httpx.Response(
        200,
        json={
            "id": "gen_billable_bad",
            "model": "vendor/free-model",
            "choices": [{"message": {"role": "assistant", "content": "not-json"}}],
            "usage": {
                "prompt_tokens": 9,
                "completion_tokens": 3,
                "total_tokens": 12,
                "cost": 0.001,
            },
        },
    )
    transport, client = gateway(tmp_path, httpx.MockTransport(lambda _: response))
    try:
        result = await transport.complete(request())
    finally:
        await client.aclose()

    assert result.failure_kind is FailureKind.MALFORMED_OUTPUT
    assert result.receipt.usage.total_tokens == 12
    assert result.receipt.usage.cost == 0.001


@pytest.mark.asyncio
async def test_gateway_registers_api_key_for_echo_redaction(tmp_path: Path) -> None:
    trace = TraceWriter(log_root=tmp_path / "logs", output_root=tmp_path / "outputs")
    response = httpx.Response(
        400,
        json={"error": {"code": 400, "message": "echo test-secret here"}},
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: response))
    transport = OpenRouterGateway(
        api_key="test-secret",
        base_url="https://openrouter.test/api/v1",
        trace=trace,
        client=client,
        max_retries=0,
    )
    try:
        result = await transport.complete(request())
    finally:
        await client.aclose()

    assert "test-secret" not in result.receipt.artifact_path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"timeout_seconds": 0},
        {"max_retries": -1},
        {"retry_delay_seconds": -0.1},
    ],
)
def test_rejects_invalid_transport_bounds(tmp_path: Path, kwargs: dict[str, float | int]) -> None:
    with pytest.raises(ValueError):
        OpenRouterGateway(
            api_key="test-secret",
            base_url="https://openrouter.test/api/v1",
            trace=TraceWriter(log_root=tmp_path / "logs", output_root=tmp_path / "outputs"),
            **kwargs,
        )
