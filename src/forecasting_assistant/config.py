from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    elicitation_db_path: str = "elicitation.db"
    dataset_store_path: str = "dataset_store"
    schema_version: str = "1.0.0"
    prompt_version: str = "llmrei-long-forecasting-v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
