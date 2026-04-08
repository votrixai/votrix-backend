"""
Integration catalog — static registry + live Composio cache.

Static registry (REGISTRY, PROVIDERS) is read-only at compile time.
Composio cache is fetched from the SDK at startup and refreshed every 24h.

To add a new static integration:
  1. Define it in app/integrations/handlers/<provider>.py
  2. Import it here and add to REGISTRY.

Usage:
    # startup
    await refresh_cache(settings.composio_api_key)

    # registry lookups
    integration = get_integration("gmail")
    provider    = get_provider("composio")
    integrations = list_integrations()

    # composio catalog browsing
    items, total = get_cached(search="gmail", category="productivity")
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.models.integration import Integration, Provider, ProviderType
from app.integrations.handlers.platform import PLATFORM_INTEGRATION

logger = logging.getLogger(__name__)


# ── Providers ─────────────────────────────────────────────────────────────────

PROVIDERS: Dict[str, Provider] = {
    "platform": Provider(slug="platform", name="Platform", type=ProviderType.PLATFORM),
    "composio": Provider(slug="composio", name="Composio", type=ProviderType.COMPOSIO),
    "custom":   Provider(slug="custom",   name="Custom",   type=ProviderType.CUSTOM),
}


# ── Default integrations pre-activated for every new org ──────────────────────
# platform is always available and not included here.

DEFAULT_ORG_INTEGRATIONS: List[str] = [
    # Google (all verified on composio.dev/toolkits/*)
    "gmail",
    "googlecalendar",
    "googlesheets",
    "googledocs",
    "googledrive",
    "googleads",
    "googlemeet",
    # Google My Business — slug unconfirmed, TODO verify
    # "googlemybusiness",
    # Meta (facebook slug is "facebook", covers Pages; instagram & whatsapp verified)
    "facebook",
    "instagram",
    "whatsapp",
    # Social (both verified)
    "twitter",
    "reddit",
    # SMB (all verified)
    "yelp",
    "notion",
    "stripe",
    "shopify",
]


# ── Static registry ───────────────────────────────────────────────────────────

REGISTRY: Dict[str, Integration] = {
    PLATFORM_INTEGRATION.slug: PLATFORM_INTEGRATION,
    # Add Composio-backed integrations below as you write them:
    # from app.integrations.handlers.composio import GITHUB_INTEGRATION
    # GITHUB_INTEGRATION.slug: GITHUB_INTEGRATION,
}


def get_integration(slug: str) -> Optional[Integration]:
    return REGISTRY.get(slug)


def list_integrations() -> List[Integration]:
    return list(REGISTRY.values())


def get_provider(slug: str) -> Optional[Provider]:
    return PROVIDERS.get(slug)


# ── Composio live catalog (app-level cache) ───────────────────────────────────

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


async def refresh_cache(api_key: str) -> None:
    """Fetch all Composio toolkits via SDK and populate the in-memory cache."""
    global _cache, _last_refreshed

    if not api_key:
        logger.warning("COMPOSIO_API_KEY not set — integration catalog will be empty")
        return

    try:
        from composio import Composio
        from composio_langchain import LangchainProvider

        composio = Composio(provider=LangchainProvider(), api_key=api_key)

        # Composio toolkits list is paginated; fetch all pages via cursor.
        all_items = []
        cursor = None
        page_count = 0
        while True:
            page = await asyncio.to_thread(
                composio.toolkits.list,
                cursor=cursor,
                limit=1000,
                managed_by="all",
            )
            page_count += 1
            all_items.extend(page.items or [])
            cursor = page.next_cursor
            if not cursor:
                break

        _cache = {
            _normalise(i)["slug"]: _normalise(i)
            for i in all_items
            if getattr(i, "slug", None)
        }
        _last_refreshed = datetime.now(timezone.utc)
        logger.info(
            "Composio cache refreshed: %d toolkits (%d page(s))",
            len(_cache),
            page_count,
        )

    except Exception as exc:
        logger.error("Composio cache refresh failed: %s", exc)


def cache_is_stale() -> bool:
    if _last_refreshed is None:
        return True
    return datetime.now(timezone.utc) - _last_refreshed > _TTL


def cache_is_ready() -> bool:
    return len(_cache) > 0


def get_cached_toolkit_meta(slug: str) -> dict | None:
    """Return cached toolkit metadata for a single slug, or None if not yet loaded."""
    return _cache.get(slug)


def get_cached(
    search: str = "",
    category: str = "",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Return (page, total) from the Composio catalog, filtered by search/category."""
    items = list(_cache.values())

    if search:
        q = search.lower()
        items = [i for i in items if q in i["name"].lower() or q in i["slug"].lower()]

    if category:
        items = [i for i in items if category in i["categories"]]

    total = len(items)
    return items[offset : offset + limit], total
