from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str
    openai_model: str
    elicitation_db_path: str = "elicitation.db"
    schema_version: str = "1.0.0"
    prompt_version: str = "llmrei-long-forecasting-v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
