"""
Composio toolkit catalog cache.

Fetches all available toolkits from the Composio SDK on startup and keeps them
in a module-level dict. Falls back gracefully when no API key is set.

Used exclusively by management-side API endpoints (browsing the full catalog).
NOT used for runtime tool execution or per-slug detail lookups.

Usage:
    await cache.refresh(api_key)   # call once at startup
    items = cache.get_all(search="gmail", category="productivity")
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_cache: dict[str, dict] = {}
_last_refreshed: Optional[datetime] = None
_TTL = timedelta(hours=24)


def _normalise(item) -> dict:
    """Flatten Composio SDK toolkit object into a simple dict."""
    meta = getattr(item, "meta", None)
    categories = []
    if meta and getattr(meta, "categories", None):
        categories = [getattr(c, "id", "") for c in meta.categories]
    return {
        "slug":         getattr(item, "slug", "") or "",
        "name":         getattr(item, "name", "") or "",
        "description":  getattr(meta, "description", "") if meta else "",
        "tool_count":   int(getattr(meta, "tools_count", 0) or 0) if meta else 0,
        "categories":   categories,
        "no_auth":      getattr(item, "no_auth", False) or False,
        "auth_schemes": list(getattr(item, "auth_schemes", None) or []),
        "logo":         getattr(meta, "logo", "") if meta else "",
    }


async def refresh(api_key: str) -> None:
    """Fetch all Composio toolkits via SDK and populate the in-memory cache."""
    global _cache, _last_refreshed

    if not api_key:
        logger.warning("COMPOSIO_API_KEY not set — integration catalog will be empty")
        return

    try:
        from composio import Composio
        from composio_langchain import LangchainProvider

        composio = Composio(provider=LangchainProvider(), api_key=api_key)
        items = await asyncio.to_thread(composio.toolkits.get)

        _cache = {
            _normalise(i)["slug"]: _normalise(i)
            for i in items
            if getattr(i, "slug", None)
        }
        _last_refreshed = datetime.now(timezone.utc)
        logger.info("Composio cache refreshed: %d toolkits", len(_cache))

    except Exception as exc:
        logger.error("Composio cache refresh failed: %s", exc)


def is_stale() -> bool:
    if _last_refreshed is None:
        return True
    return datetime.now(timezone.utc) - _last_refreshed > _TTL


def is_ready() -> bool:
    return len(_cache) > 0


def get_all(
    search: str = "",
    category: str = "",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Return (page, total) filtered by search/category."""
    items = list(_cache.values())

    if search:
        q = search.lower()
        items = [i for i in items if q in i["name"].lower() or q in i["slug"].lower()]

    if category:
        items = [i for i in items if category in i["categories"]]

    total = len(items)
    return items[offset : offset + limit], total
