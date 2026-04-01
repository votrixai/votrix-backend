"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = ""
    langgraph_database_url: str = ""  # psycopg3 DSN for LangGraph checkpointer (postgresql://...)

    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Composio
    composio_api_key: str = ""

    # Supabase Storage
    supabase_url: str = ""
    supabase_service_key: str = ""

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
