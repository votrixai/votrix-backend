"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# LangSmith / LangChain read tracing flags from os.environ, not from Pydantic.
# pydantic-settings only maps declared fields; it does not export the whole .env.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Settings(BaseSettings):
    # Database
    database_url: str = ""
    langgraph_database_url: str = ""  # psycopg3 DSN for LangGraph checkpointer (postgresql://...)

    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""  # Gemini (tool_search deferred-tool ranking)

    # Composio
    composio_api_key: str = ""
    # Composio entity id for the votrix official connected account (shared org key, not per end-user).
    # All API-key-backed toolkits (Tavily search/extract/crawl, etc.) run under this entity.
    composio_official_user_id: str = "votrix-ai-official"

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
