from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    anthropic_api_key: str

    # Composio — org-level credentials
    composio_api_key: str = ""

    # Supabase Storage — for generated images
    supabase_url: str = ""
    supabase_service_key: str = ""


    # Gemini — for image generation
    gemini_api_key: str = ""

    # Debug mode — enables verbose frontend event logging
    debug: bool = False

    # Force-reprovision Anthropic agent + Composio MCP server on every new session.
    # Set to true only when you need to refresh credentials or reset agent config.
    force_reprovision: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
