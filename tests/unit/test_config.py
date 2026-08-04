from forecasting_assistant.config import Settings


def test_settings_accept_an_explicit_model_name() -> None:
    settings = Settings(
        openai_api_key="test-key",
        openai_model="test-model",
        elicitation_db_path=":memory:",
    )

    assert settings.openai_model == "test-model"
    assert settings.dataset_store_path == "dataset_store"
    assert settings.schema_version == "1.0.0"
    assert settings.prompt_version == "llmrei-long-forecasting-v1"


def test_settings_default_model_allows_dataset_only_commands(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.openai_api_key == ""
    assert settings.openai_model == "gpt-4.1-mini"
