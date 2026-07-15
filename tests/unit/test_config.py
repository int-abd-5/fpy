import pytest
from pydantic import ValidationError

from forecasting_assistant.config import Settings


def test_settings_require_a_model_name() -> None:
    settings = Settings(
        openai_api_key="test-key",
        openai_model="test-model",
        elicitation_db_path=":memory:",
    )

    assert settings.openai_model == "test-model"
    assert settings.schema_version == "1.0.0"
    assert settings.prompt_version == "llmrei-long-forecasting-v1"


def test_settings_reject_omitted_model_name(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    with pytest.raises(ValidationError):
        Settings(openai_api_key="test-key", _env_file=None)
