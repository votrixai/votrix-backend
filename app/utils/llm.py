"""Build LangChain chat models from blueprint model ids and app settings."""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.config import Settings, get_settings


def _is_gemini_model(model_name: str) -> bool:
    m = model_name.strip().lower()
    return m.startswith("gemini") or m.startswith("models/gemini") or "/gemini" in m


def build_chat_model(model_name: str, settings: Settings | None = None) -> BaseChatModel:
    """
    Dispatch on model id: Anthropic (claude*), Google (gemini* / models/gemini*), else OpenAI-compatible.

    Keys are read from Settings (env: ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY).
    """
    s = settings or get_settings()
    name = model_name.strip()
    lower = name.lower()
    if lower.startswith("claude"):
        return ChatAnthropic(model=name, api_key=s.anthropic_api_key)
    if _is_gemini_model(name):
        return ChatGoogleGenerativeAI(model=name, api_key=s.google_api_key)
    return ChatOpenAI(model=name, api_key=s.openai_api_key)
