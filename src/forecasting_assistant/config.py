from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    elicitation_db_path: str = "elicitation.db"
    elicitation_log_path: str = "logs/elicitation_pipeline.jsonl"
    dataset_store_path: str = "dataset_store"
    schema_version: str = "1.0.0"
    prompt_version: str = "llmrei-long-forecasting-v1"
    registry_api_url: str = ""
    registry_api_key: str = ""
    registry_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    registry_max_retries: int = Field(default=2, ge=0, le=5)
    registry_min_relevance: float = Field(default=0.80, ge=0, le=1)
    registry_min_companion_strength: float = Field(default=0.60, ge=0, le=1)
    registry_max_dependency_depth: int = Field(default=2, ge=1, le=5)
    registry_max_sources: int = Field(default=12, ge=1, le=100)
    registry_include_pending: bool = False
    registry_required: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
