"""OpenRouter implementation of the provider-neutral model gateway."""

from __future__ import annotations

import asyncio
import copy
import json
from datetime import UTC, datetime
from time import monotonic
from typing import Any

import httpx
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from pydantic import BaseModel, ConfigDict, Field
from pydantic import ValidationError as PydanticValidationError

from forge.gateways.model import (
    FailureKind,
    ModelReceipt,
    ModelRequest,
    ModelResult,
    ModelUsage,
)
from forge.observability.trace import TraceWriter


class _ProviderMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    content: str


class _ProviderChoice(BaseModel):
    model_config = ConfigDict(extra="ignore")
    message: _ProviderMessage


class _ProviderUsage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float | None = None


class _ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    model: str
    choices: list[_ProviderChoice]
    usage: _ProviderUsage = Field(default_factory=_ProviderUsage)


class OpenRouterGateway:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        trace: TraceWriter,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 60,
        max_retries: int = 2,
        retry_delay_seconds: float = 0.5,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds cannot be negative")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._trace = trace
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None
        self._timeout = httpx.Timeout(timeout_seconds)
        self._max_retries = max_retries
        self._retry_delay_seconds = retry_delay_seconds
        self._trace.register_secret(api_key)

    async def __aenter__(self) -> OpenRouterGateway:
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def complete(self, request: ModelRequest) -> ModelResult:
        started_at = datetime.now(UTC)
        started_clock = monotonic()
        payload = self._payload(request)
        base_metadata = self._metadata(request)
        self._trace.record_event(
            investigation_id=request.investigation_id,
            call_id=request.call_id,
            event="model_call_started",
            metadata=base_metadata,
        )

        last_response: dict[str, Any] = {}
        failure_kind = FailureKind.PROVIDER_ERROR
        failure_message = "Model provider call failed"
        attempts = 0
        usage = ModelUsage()

        try:
            provider_schema = payload["response_format"]["json_schema"]["schema"]
            Draft202012Validator.check_schema(provider_schema)
            json.dumps(payload)
        except (SchemaError, TypeError, ValueError):
            rejected_request = {
                "model": request.model,
                "output_schema_name": request.output_schema_name,
                "request_rejected": "output schema is not valid JSON Schema",
            }
            return self._failure_result(
                request=request,
                payload=rejected_request,
                response_body={"error": {"kind": "invalid_request"}},
                attempts=0,
                started_at=started_at,
                started_clock=started_clock,
                usage=usage,
                failure_kind=FailureKind.INVALID_REQUEST,
                failure_message="Model request contains an invalid output schema",
            )

        try:
            for attempts in range(1, self._max_retries + 2):
                try:
                    self._trace.record_event(
                        investigation_id=request.investigation_id,
                        call_id=request.call_id,
                        event="model_call_attempt_started",
                        metadata={**base_metadata, "attempt": attempts},
                    )
                    response = await self._client.post(
                        f"{self._base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self._api_key}"},
                        json=payload,
                        timeout=self._timeout,
                    )
                    last_response = self._response_body(response)
                    if response.is_success:
                        if "error" in last_response:
                            return self._failure_result(
                                request=request,
                                payload=payload,
                                response_body=last_response,
                                attempts=attempts,
                                started_at=started_at,
                                started_clock=started_clock,
                                usage=ModelUsage(),
                                failure_kind=FailureKind.PROVIDER_ERROR,
                                failure_message="Provider failed during generation",
                            )
                        return self._success_result(
                            request=request,
                            payload=payload,
                            response_body=last_response,
                            attempts=attempts,
                            started_at=started_at,
                            started_clock=started_clock,
                        )
                    failure_kind = self._http_failure_kind(response.status_code)
                    failure_message = f"Provider returned HTTP {response.status_code}"
                    transient = response.status_code in {408, 429} or response.status_code >= 500
                except httpx.TimeoutException:
                    failure_kind = FailureKind.TIMEOUT
                    failure_message = "Model provider timed out"
                    transient = True
                    last_response = {"error": {"kind": "timeout"}}
                except httpx.TransportError:
                    failure_kind = FailureKind.NETWORK
                    failure_message = "Model provider network failure"
                    transient = True
                    last_response = {"error": {"kind": "network"}}

                if transient and attempts <= self._max_retries:
                    self._trace.record_event(
                        investigation_id=request.investigation_id,
                        call_id=request.call_id,
                        event="model_call_retrying",
                        metadata={**base_metadata, "attempt": attempts, "reason": failure_kind},
                    )
                    await asyncio.sleep(self._retry_delay_seconds)
                    continue
                break
        except asyncio.CancelledError:
            return self._failure_result(
                request=request,
                payload=payload,
                response_body={"error": {"kind": "cancelled"}},
                attempts=max(attempts, 1),
                started_at=started_at,
                started_clock=started_clock,
                usage=usage,
                failure_kind=FailureKind.CANCELLED,
                failure_message="Model call was cancelled",
                event="model_call_cancelled",
            )

        return self._failure_result(
            request=request,
            payload=payload,
            response_body=last_response,
            attempts=attempts,
            started_at=started_at,
            started_clock=started_clock,
            usage=usage,
            failure_kind=failure_kind,
            failure_message=failure_message,
        )

    def _success_result(
        self,
        *,
        request: ModelRequest,
        payload: dict[str, Any],
        response_body: dict[str, Any],
        attempts: int,
        started_at: datetime,
        started_clock: float,
    ) -> ModelResult:
        usage = ModelUsage()
        try:
            provider = _ProviderResponse.model_validate(response_body)
            usage = ModelUsage(**provider.usage.model_dump())
            if not provider.choices:
                raise ValueError("missing choices")
            output = json.loads(provider.choices[0].message.content)
            Draft202012Validator(request.output_schema).validate(output)
            if not isinstance(output, dict):
                raise ValueError("structured output must be an object")
        except (
            PydanticValidationError,
            json.JSONDecodeError,
            SchemaError,
            ValidationError,
            ValueError,
        ):
            return self._failure_result(
                request=request,
                payload=payload,
                response_body=response_body,
                attempts=attempts,
                started_at=started_at,
                started_clock=started_clock,
                usage=usage,
                failure_kind=FailureKind.MALFORMED_OUTPUT,
                failure_message="Provider returned invalid structured output",
            )

        receipt = self._receipt_and_artifact(
            request=request,
            payload=payload,
            response_body=response_body,
            attempts=attempts,
            started_at=started_at,
            started_clock=started_clock,
            usage=usage,
            event="model_call_succeeded",
        )
        return ModelResult(output=output, receipt=receipt)

    def _failure_result(
        self,
        *,
        request: ModelRequest,
        payload: dict[str, Any],
        response_body: dict[str, Any],
        attempts: int,
        started_at: datetime,
        started_clock: float,
        usage: ModelUsage,
        failure_kind: FailureKind,
        failure_message: str,
        event: str = "model_call_failed",
    ) -> ModelResult:
        receipt = self._receipt_and_artifact(
            request=request,
            payload=payload,
            response_body=response_body,
            attempts=attempts,
            started_at=started_at,
            started_clock=started_clock,
            usage=usage,
            event=event,
            extra={"failure_kind": failure_kind},
        )
        return ModelResult(
            failure_kind=failure_kind,
            failure_message=failure_message,
            receipt=receipt,
        )

    def _receipt_and_artifact(
        self,
        *,
        request: ModelRequest,
        payload: dict[str, Any],
        response_body: dict[str, Any],
        attempts: int,
        started_at: datetime,
        started_clock: float,
        usage: ModelUsage,
        event: str,
        extra: dict[str, Any] | None = None,
    ) -> ModelReceipt:
        finished_at = datetime.now(UTC)
        duration_ms = round((monotonic() - started_clock) * 1000)
        metadata = {
            **self._metadata(request),
            "attempts": attempts,
            "duration_ms": duration_ms,
            "usage": usage.model_dump(),
            **(extra or {}),
        }
        artifact_path = self._trace.record_model_call(
            investigation_id=request.investigation_id,
            call_id=request.call_id,
            event=event,
            metadata=metadata,
            request=payload,
            response=response_body,
        )
        return ModelReceipt(
            role=request.role,
            model=request.model,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            attempts=attempts,
            usage=usage,
            prompt_contract_version=request.prompt_contract_version,
            artifact_path=artifact_path,
        )

    @staticmethod
    def _metadata(request: ModelRequest) -> dict[str, Any]:
        return {
            "role": request.role,
            "model": request.model,
            "prompt_contract_version": request.prompt_contract_version,
        }

    @staticmethod
    def _http_failure_kind(status_code: int) -> FailureKind:
        if status_code == 400:
            return FailureKind.INVALID_REQUEST
        if status_code == 429:
            return FailureKind.RATE_LIMIT
        if status_code == 408:
            return FailureKind.TIMEOUT
        return FailureKind.PROVIDER_ERROR

    @staticmethod
    def _response_body(response: httpx.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except json.JSONDecodeError:
            return {"http_status": response.status_code, "error": "non-json response"}
        return body if isinstance(body, dict) else {"body": body}

    @staticmethod
    def _payload(request: ModelRequest) -> dict[str, Any]:
        return {
            "model": request.model,
            "messages": [message.model_dump() for message in request.messages],
            "max_completion_tokens": request.max_output_tokens,
            "provider": {"require_parameters": True},
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": request.output_schema_name,
                    "strict": True,
                    "schema": _strict_output_schema(request.output_schema),
                },
            },
        }


def _strict_output_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return the strict JSON Schema subset expected by structured-output providers."""

    # Mirrors the official OpenAI SDK's Pydantic schema transformation:
    # https://github.com/openai/openai-python/blob/main/src/openai/lib/_pydantic.py
    strict_schema = copy.deepcopy(schema)

    def normalize(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                normalize(item)
            return
        if not isinstance(node, dict):
            return
        one_of = node.pop("oneOf", None)
        if isinstance(one_of, list):
            # OpenAI's strict structured-output subset accepts anyOf but rejects
            # the oneOf/discriminator form emitted for Pydantic tagged unions.
            node["anyOf"] = one_of
        node.pop("discriminator", None)
        properties = node.get("properties")
        if isinstance(properties, dict):
            node["required"] = list(properties)
            node["additionalProperties"] = False
        if node.get("default", object()) is None:
            node.pop("default")
        for value in node.values():
            normalize(value)

    normalize(strict_schema)
    return strict_schema
