"""Model string → BaseChatModel, with LRU cache.

Uses LangChain's init_chat_model() for provider-agnostic resolution.
API keys are read from env vars (ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.).

Supported model strings (examples):
  - "claude-sonnet-4-5-20250929"  → langchain-anthropic
  - "claude-haiku-4-5-20251001"   → langchain-anthropic
  - "gpt-4o", "gpt-4o-mini"       → langchain-openai (requires langchain-openai)
  - "gemini-2.5-pro"              → langchain-google-genai (requires langchain-google-genai)
"""

import logging
from functools import lru_cache

from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)

# Human-readable registry for validation and UI display.
# Provider values match init_chat_model() provider detection.
_SUPPORTED_MODELS: dict[str, str] = {
    "claude-sonnet-4-5-20250929": "anthropic",
    "claude-haiku-4-5-20251001": "anthropic",
    "claude-opus-4-5": "anthropic",
    "claude-sonnet-4-6": "anthropic",
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
}


@lru_cache(maxsize=32)
def get_model(model_name: str, temperature: float = 0.0) -> BaseChatModel:
    """Resolve a model identifier to a BaseChatModel.

    Results are cached by (model_name, temperature) — models are stateless objects.
    Raises ValueError for unsupported model strings, ImportError if the provider
    package is not installed.
    """
    from langchain.chat_models import init_chat_model

    logger.debug(f"Resolving model: {model_name}")
    return init_chat_model(model_name, temperature=temperature)


def list_supported_models() -> dict[str, str]:
    """Return {model_name: provider} mapping for validation and UI display."""
    return dict(_SUPPORTED_MODELS)
