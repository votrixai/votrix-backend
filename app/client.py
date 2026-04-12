from functools import lru_cache

import anthropic
import httpx

from app.config import get_settings


@lru_cache
def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(
        api_key=get_settings().anthropic_api_key,
        http_client=httpx.Client(trust_env=False),
    )
