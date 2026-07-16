"""Provider-neutral contracts for model calls."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveInt,
    field_validator,
    model_validator,
)

from forge.domain.identifiers import CallId, InvestigationId


class ModelRole(StrEnum):
    LEAD = "lead"
    RESEARCHER = "researcher"
    CONNECTION_FINDER = "connection_finder"
    SYNTHESIZER = "synthesizer"
    SKEPTIC = "skeptic"
    EXPERIMENT_DESIGNER = "experiment_designer"


class FailureKind(StrEnum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    NETWORK = "network"
    PROVIDER_ERROR = "provider_error"
    MALFORMED_OUTPUT = "malformed_output"
    INVALID_REQUEST = "invalid_request"
    CANCELLED = "cancelled"


class ModelMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: str
    content: str


class ModelRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    investigation_id: InvestigationId
    call_id: CallId
    role: ModelRole
    model: str = Field(min_length=1)
    messages: tuple[ModelMessage, ...] = Field(min_length=1)
    output_schema: dict[str, Any]
    output_schema_name: str = Field(min_length=1)
    max_output_tokens: PositiveInt
    prompt_contract_version: str = Field(min_length=1)


class ModelUsage(BaseModel):
    model_config = ConfigDict(frozen=True)

    prompt_tokens: NonNegativeInt = 0
    completion_tokens: NonNegativeInt = 0
    total_tokens: NonNegativeInt = 0
    cost: NonNegativeFloat | None = None


class ModelReceipt(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: ModelRole
    model: str
    started_at: datetime
    finished_at: datetime
    duration_ms: NonNegativeInt
    attempts: NonNegativeInt
    usage: ModelUsage
    prompt_contract_version: str
    artifact_path: Path

    @field_validator("started_at", "finished_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("receipt timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_monotonic_time(self) -> ModelReceipt:
        if self.finished_at < self.started_at:
            raise ValueError("receipt finish cannot precede start")
        return self


class ModelResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    output: dict[str, Any] | None = None
    failure_kind: FailureKind | None = None
    failure_message: str | None = None
    receipt: ModelReceipt

    @model_validator(mode="after")
    def require_consistent_outcome(self) -> ModelResult:
        if self.output is not None:
            if self.failure_kind is not None or self.failure_message is not None:
                raise ValueError("successful results cannot contain failure fields")
        elif self.failure_kind is None or not self.failure_message:
            raise ValueError("failed results require a kind and message")
        return self

    @property
    def is_success(self) -> bool:
        return self.failure_kind is None


class ModelGateway(Protocol):
    async def complete(self, request: ModelRequest) -> ModelResult: ...
