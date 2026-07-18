from pathlib import Path

import pytest

from forge.config import ConfigurationError, load_settings
from forge.domain.investigation import DepthMode

REQUIRED_ENVIRONMENT = {
    "OPENROUTER_API_KEY": "not-a-real-key",
    "FORGE_MODEL_LEAD": "vendor/lead-model",
    "FORGE_MODEL_RESEARCHER": "vendor/research-model",
    "FORGE_MODEL_CONNECTION_FINDER": "vendor/connection-model",
    "FORGE_MODEL_SYNTHESIZER": "vendor/synthesis-model",
    "FORGE_MODEL_SKEPTIC": "vendor/skeptic-model",
    "FORGE_MODEL_EXPERIMENT_DESIGNER": "vendor/experiment-model",
}


def set_required_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in REQUIRED_ENVIRONMENT.items():
        monkeypatch.setenv(name, value)


def clear_required_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in REQUIRED_ENVIRONMENT:
        monkeypatch.delenv(name, raising=False)


def test_loads_required_values_with_approved_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_required_environment(monkeypatch)

    settings = load_settings(env_file=None)

    assert settings.openrouter_api_key.get_secret_value() == "not-a-real-key"
    assert settings.model_lead == "vendor/lead-model"
    assert settings.model_researcher == "vendor/research-model"
    assert settings.model_connection_finder == "vendor/connection-model"
    assert settings.model_synthesizer == "vendor/synthesis-model"
    assert settings.model_skeptic == "vendor/skeptic-model"
    assert settings.model_experiment_designer == "vendor/experiment-model"
    assert settings.default_depth is DepthMode.STANDARD
    assert settings.data_dir == Path("data")
    assert settings.output_dir == Path("outputs")
    assert settings.log_dir == Path("logs")
    assert settings.quick_max_calls == 8
    assert settings.standard_max_calls == 10
    assert settings.deep_max_calls == 24
    assert settings.quick_max_output_tokens_per_call == 2400
    assert settings.standard_max_output_tokens_per_call == 2400
    assert settings.deep_max_output_tokens_per_call == 4800


def test_reports_all_missing_required_settings_together(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_required_environment(monkeypatch)

    with pytest.raises(ConfigurationError) as captured:
        load_settings(env_file=None)

    message = str(captured.value)
    for name in REQUIRED_ENVIRONMENT:
        assert name in message


def test_redacts_secret_when_other_configuration_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_required_environment(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "do-not-leak-this-value")
    monkeypatch.setenv("FORGE_OPENROUTER_BASE_URL", "http://insecure.example.test/v1")

    with pytest.raises(ConfigurationError) as captured:
        load_settings(env_file=None)

    message = str(captured.value)
    assert "FORGE_OPENROUTER_BASE_URL" in message
    assert "do-not-leak-this-value" not in message


def test_rejects_blank_role_names_and_nonpositive_budgets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_required_environment(monkeypatch)
    monkeypatch.setenv("FORGE_MODEL_SKEPTIC", "   ")
    monkeypatch.setenv("FORGE_QUICK_MAX_CALLS", "0")

    with pytest.raises(ConfigurationError) as captured:
        load_settings(env_file=None)

    message = str(captured.value)
    assert "FORGE_MODEL_SKEPTIC" in message
    assert "FORGE_QUICK_MAX_CALLS" in message


def test_secret_is_masked_in_display_and_serialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_required_environment(monkeypatch)

    settings = load_settings(env_file=None)

    assert "not-a-real-key" not in repr(settings)
    assert "not-a-real-key" not in settings.model_dump_json()
    assert str(settings.openrouter_api_key) == "**********"


def test_loads_utf8_dotenv_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    clear_required_environment(monkeypatch)
    env_file = tmp_path / "forge.env"
    env_file.write_text(
        "\n".join(f"{name}={value}" for name, value in REQUIRED_ENVIRONMENT.items()),
        encoding="utf-8",
    )

    settings = load_settings(env_file=env_file)

    assert settings.model_lead == "vendor/lead-model"
    assert settings.openrouter_api_key.get_secret_value() == "not-a-real-key"
