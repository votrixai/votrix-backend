"""
Composio toolkit catalog cache.

Fetches all available toolkits from the Composio API on startup and keeps them
in a module-level dict. Falls back gracefully when no API key is set.

Usage:
    await composio_cache.refresh(api_key)   # call once at startup
    items = composio_cache.get_all(search="gmail", category="productivity")
    item  = composio_cache.get_by_slug("gmail")
    exists = composio_cache.slug_exists("gmail")
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_cache: dict[str, dict] = {}           # slug → raw toolkit dict
_last_refreshed: Optional[datetime] = None
_TTL = timedelta(hours=24)

_COMPOSIO_BASE = "https://backend.composio.dev"
_LIST_PATH = "/api/v3/toolkits"
_PAGE_SIZE = 100


# ---------------------------------------------------------------------------
# Internal fetch
# ---------------------------------------------------------------------------

async def _fetch_page(client: httpx.AsyncClient, api_key: str, cursor: Optional[str]) -> tuple[list[dict], Optional[str]]:
    params: dict = {"limit": _PAGE_SIZE, "sort_by": "usage", "managed_by": "composio"}
    if cursor:
        params["cursor"] = cursor

    resp = await client.get(
        _COMPOSIO_BASE + _LIST_PATH,
        headers={"x-api-key": api_key},
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    items = data.get("items", [])
    next_cursor = data.get("next_cursor") or data.get("nextCursor")
    return items, next_cursor


def _normalise(item: dict) -> dict:
    """Flatten Composio toolkit object into a simple dict."""
    meta = item.get("meta") or {}
    return {
        "slug":        item.get("slug", ""),
        "name":        item.get("name", ""),
        "description": meta.get("description", ""),
        "tool_count":  meta.get("tools_count", 0),
        "categories":  meta.get("categories") or [],
        "no_auth":     item.get("no_auth", False),
        "auth_schemes": item.get("auth_schemes") or [],
        "logo":        meta.get("logo", ""),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def refresh(api_key: str) -> None:
    """Fetch all Composio toolkits and populate the in-memory cache."""
    global _cache, _last_refreshed

    if not api_key:
        logger.warning("COMPOSIO_API_KEY not set — integration catalog will be empty")
        return

    collected: list[dict] = []
    cursor: Optional[str] = None

    try:
        async with httpx.AsyncClient() as client:
            while True:
                items, cursor = await _fetch_page(client, api_key, cursor)
                collected.extend(items)
                if not cursor or not items:
                    break

        _cache = {_normalise(i)["slug"]: _normalise(i) for i in collected if i.get("slug")}
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


def slug_exists(slug: str) -> bool:
    return slug in _cache


def get_by_slug(slug: str) -> Optional[dict]:
    return _cache.get(slug)


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
