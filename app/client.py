from functools import lru_cache

import anthropic

from app.config import get_settings


@lru_cache
def get_async_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(
        api_key=get_settings().anthropic_api_key,
    )
