"""Validated, secret-safe application configuration."""

from pathlib import Path
from typing import Annotated

from pydantic import (
    Field,
    HttpUrl,
    PositiveInt,
    SecretStr,
    StringConstraints,
    ValidationError,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from forge.domain.investigation import DepthMode

ModelIdentifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

_ENVIRONMENT_NAMES = {
    "openrouter_api_key": "OPENROUTER_API_KEY",
    "openrouter_base_url": "FORGE_OPENROUTER_BASE_URL",
    "model_lead": "FORGE_MODEL_LEAD",
    "model_researcher": "FORGE_MODEL_RESEARCHER",
    "model_connection_finder": "FORGE_MODEL_CONNECTION_FINDER",
    "model_synthesizer": "FORGE_MODEL_SYNTHESIZER",
    "model_skeptic": "FORGE_MODEL_SKEPTIC",
    "model_experiment_designer": "FORGE_MODEL_EXPERIMENT_DESIGNER",
    "default_depth": "FORGE_DEFAULT_DEPTH",
    "data_dir": "FORGE_DATA_DIR",
    "quick_max_calls": "FORGE_QUICK_MAX_CALLS",
    "standard_max_calls": "FORGE_STANDARD_MAX_CALLS",
    "deep_max_calls": "FORGE_DEEP_MAX_CALLS",
    "quick_max_output_tokens_per_call": "FORGE_QUICK_MAX_OUTPUT_TOKENS_PER_CALL",
    "standard_max_output_tokens_per_call": "FORGE_STANDARD_MAX_OUTPUT_TOKENS_PER_CALL",
    "deep_max_output_tokens_per_call": "FORGE_DEEP_MAX_OUTPUT_TOKENS_PER_CALL",
}


class ForgeSettings(BaseSettings):
    """Environment-backed settings for the discovery forge."""

    # Source: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="FORGE_",
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
        populate_by_name=True,
    )

    openrouter_api_key: SecretStr = Field(validation_alias="OPENROUTER_API_KEY")
    openrouter_base_url: HttpUrl = HttpUrl("https://openrouter.ai/api/v1")

    model_lead: ModelIdentifier
    model_researcher: ModelIdentifier
    model_connection_finder: ModelIdentifier
    model_synthesizer: ModelIdentifier
    model_skeptic: ModelIdentifier
    model_experiment_designer: ModelIdentifier

    default_depth: DepthMode = DepthMode.STANDARD
    data_dir: Path = Path("data")

    quick_max_calls: PositiveInt = 6
    standard_max_calls: PositiveInt = 10
    deep_max_calls: PositiveInt = 24
    quick_max_output_tokens_per_call: PositiveInt = 1200
    standard_max_output_tokens_per_call: PositiveInt = 2400
    deep_max_output_tokens_per_call: PositiveInt = 4800

    @field_validator("openrouter_api_key", mode="before")
    @classmethod
    def reject_blank_api_key(cls, value: object) -> object:
        raw_value = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        if not raw_value.strip():
            raise ValueError("OpenRouter API key must not be blank")
        return raw_value.strip()

    @field_validator("openrouter_base_url")
    @classmethod
    def require_https_openrouter_url(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https":
            raise ValueError("OpenRouter base URL must use HTTPS")
        return value


class ConfigurationError(RuntimeError):
    """A sanitized aggregate of invalid application settings."""

    def __init__(self, problems: tuple[str, ...]) -> None:
        self.problems = problems
        details = "\n".join(f"- {problem}" for problem in problems)
        super().__init__(f"Invalid configuration:\n{details}")


def load_settings(env_file: str | Path | None = ".env") -> ForgeSettings:
    """Load settings or raise one secret-safe error containing every problem."""

    try:
        return ForgeSettings(_env_file=env_file)
    except ValidationError as error:
        problems = tuple(_format_problem(item) for item in error.errors(include_input=False))
        raise ConfigurationError(problems) from None


def _format_problem(error: dict[str, object]) -> str:
    location = error.get("loc", ())
    field_name = str(location[0]) if isinstance(location, tuple) and location else "configuration"
    environment_name = _ENVIRONMENT_NAMES.get(field_name, field_name.upper())
    message = str(error.get("msg", "is invalid"))
    return f"{environment_name}: {message}"
