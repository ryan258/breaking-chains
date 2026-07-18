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


def _environment_name(field_name: str) -> str:
    # The API key is the only setting without the FORGE_ prefix.
    if field_name == "openrouter_api_key":
        return "OPENROUTER_API_KEY"
    return f"FORGE_{field_name.upper()}"


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
    output_dir: Path = Path("outputs")
    log_dir: Path = Path("logs")

    quick_max_calls: PositiveInt = 8
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
    environment_name = _environment_name(field_name)
    message = str(error.get("msg", "is invalid"))
    return f"{environment_name}: {message}"
