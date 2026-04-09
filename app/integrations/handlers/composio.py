"""
Composio handler — tool schema cache + LangChain tool assembly.

Singleton pattern: one Composio instance per process, lazily initialized.
Composio SDK is synchronous; all calls are offloaded to a thread pool.

Schema cache (process-level, 24h TTL):
    _tool_schema_cache   action_slug  → raw Tool object
    _toolkit_to_slugs    toolkit_slug → [action_slugs]   (secondary index)

On cache miss, warm_toolkit() fetches all tools for a toolkit at once and
populates both dicts. load_tools_cached() uses the cache to build
LangChain StructuredTool objects without re-hitting the Composio API.
"""

import asyncio
import functools
import logging
import time
from typing import Any, Dict, List, Optional

from composio import Composio
from composio_langchain import LangchainProvider
from langchain_core.tools import BaseTool

from app.models.integration import Integration

logger = logging.getLogger(__name__)


# ── Singleton ──────────────────────────────────────────────────────────────────

_composio = None
_lock = asyncio.Lock()


async def _get_composio(api_key: str):
    global _composio
    async with _lock:
        if _composio is None:
            _composio = Composio(provider=LangchainProvider(), api_key=api_key)
    return _composio


# ── Schema cache ───────────────────────────────────────────────────────────────

_tool_schema_cache: Dict[str, Any] = {}       # action_slug → Tool object
_toolkit_to_slugs: Dict[str, List[str]] = {}  # toolkit_slug → [action_slugs]
_fetched_at: Dict[str, float] = {}            # action_slug → timestamp
_TOOL_SCHEMA_TTL = 86400                       # 24 h


def _is_stale(slug: str) -> bool:
    t = _fetched_at.get(slug)
    return t is None or (time.time() - t) > _TOOL_SCHEMA_TTL


def _populate_cache(tool_objects: list) -> None:
    """Write a batch of raw Tool objects into both cache dicts."""
    now = time.time()
    for tool in tool_objects:
        slug = getattr(tool, "slug", None)
        if not slug:
            continue
        toolkit_slug = ""
        toolkit = getattr(tool, "toolkit", None)
        if toolkit:
            toolkit_slug = getattr(toolkit, "slug", "") or ""

        _tool_schema_cache[slug] = tool
        _fetched_at[slug] = now

        if toolkit_slug:
            if toolkit_slug not in _toolkit_to_slugs:
                _toolkit_to_slugs[toolkit_slug] = []
            if slug not in _toolkit_to_slugs[toolkit_slug]:
                _toolkit_to_slugs[toolkit_slug].append(slug)


# ── Public cache helpers ───────────────────────────────────────────────────────

async def warm_toolkit(api_key: str, toolkit_slug: str) -> None:
    """
    Fetch all tool schemas for a toolkit and populate the cache.
    Called on GET /integrations/{slug} miss or load_tools_cached miss.
    """
    if not api_key:
        return
    composio = await _get_composio(api_key)
    t0 = time.perf_counter()
    try:
        raw_tools = await asyncio.to_thread(
            composio.tools.get_raw_composio_tools,
            toolkits=[toolkit_slug],
        )
        _populate_cache(raw_tools)
        logger.info(
            "warm_toolkit toolkit=%s tools=%d fetch_ms=%.0f",
            toolkit_slug, len(raw_tools), (time.perf_counter() - t0) * 1000,
        )
    except Exception as exc:
        logger.error(
            "warm_toolkit failed toolkit=%s fetch_ms=%.0f error=%s",
            toolkit_slug, (time.perf_counter() - t0) * 1000, exc,
        )


def get_cached_toolkit_schemas(toolkit_slug: str) -> List[Any]:
    """
    Return cached raw Tool objects for a toolkit.
    Returns empty list if toolkit has not been warmed yet.
    """
    slugs = _toolkit_to_slugs.get(toolkit_slug, [])
    return [_tool_schema_cache[s] for s in slugs if s in _tool_schema_cache]


async def load_tools_cached(
    api_key: str,
    user_id: str,
    slugs: List[str],
) -> List[BaseTool]:
    """
    Cache-aware replacement for composio.tools.get(user_id, tools=slugs).

    - All cache hits  → zero network, just wrap schemas with user_id closure.
    - Any cache miss  → fetch missing slugs from Composio, populate cache, wrap.
    """
    if not api_key or not slugs:
        return []

    missing = [s for s in slugs if _is_stale(s)]

    if missing:
        composio = await _get_composio(api_key)
        try:
            fetched = await asyncio.to_thread(
                composio.tools.get_raw_composio_tools,
                tools=missing,
            )
            _populate_cache(fetched)
        except Exception as exc:
            logger.error("load_tools_cached fetch_failed slugs=%s error=%s", missing, exc)

    tool_objects = [_tool_schema_cache[s] for s in slugs if s in _tool_schema_cache]
    if not tool_objects:
        logger.warning("load_tools_cached no_schemas slugs=%s", slugs)
        return []

    composio = await _get_composio(api_key)
    execute_fn = functools.partial(
        composio.tools.execute,
        user_id=user_id,
        dangerously_skip_version_check=True,
    )
    try:
        result = await asyncio.to_thread(
            composio.tools.provider.wrap_tools,
            tools=tool_objects,
            execute_tool=execute_fn,
        )
    except Exception as exc:
        logger.error("load_tools_cached wrap_failed error=%s", exc)
        return []
    return result


def _partition_tavily_slugs(slugs: List[str]) -> tuple[List[str], List[str]]:
    """Tavily actions use a shared Composio user; other tools use the session user."""
    tavily: List[str] = []
    rest: List[str] = []
    for s in slugs:
        (tavily if s.upper().startswith("TAVILY") else rest).append(s)
    return tavily, rest


async def load_tools_cached_for_session(
    api_key: str,
    user_id: str,
    slugs: List[str],
    *,
    composio_official_user_id: str = "",
) -> List[BaseTool]:
    """
    Like load_tools_cached, but routes Tavily action slugs to composio_official_user_id
    when non-empty so a single Composio connected account can back all users.

    Composio wraps one execute_user_id per batch; mixing Tavily with other apps
    requires two load_tools_cached calls.
    """
    tid = composio_official_user_id.strip()
    if not tid:
        return await load_tools_cached(api_key, user_id, slugs)
    tavily_slugs, other_slugs = _partition_tavily_slugs(slugs)
    merged: List[BaseTool] = []
    if tavily_slugs:
        merged.extend(await load_tools_cached(api_key, tid, tavily_slugs))
    if other_slugs:
        merged.extend(await load_tools_cached(api_key, user_id, other_slugs))
    return merged


async def initiate_connection(api_key: str, toolkit_slug: str, user_id: str) -> dict:
    """
    Initiate a Composio managed OAuth connection for a toolkit.

    Uses composio-managed auth (auto-creates auth config if one doesn't exist).
    Returns { connection_id, redirect_url } on success.
    Returns { already_connected: True } if the user already has an active connection.
    Returns { error } on failure.
    """
    if not api_key:
        return {"error": "No Composio API key configured"}
    composio = await _get_composio(api_key)
    try:
        req = await asyncio.to_thread(
            composio.toolkits.authorize,
            user_id=user_id,
            toolkit=toolkit_slug,
        )
        return {
            "connection_id": req.id,
            "redirect_url": req.redirect_url,
        }
    except Exception as exc:
        msg = str(exc)
        if "Multiple connected" in msg:
            # Already has an active connection — not an error
            return {"already_connected": True, "connection_id": None, "redirect_url": None}
        if "NoAuthApp" in msg or "does not require authentication" in msg:
            # Toolkit works without auth (e.g. yelp) — tell agent to use it directly
            return {"no_auth_required": True}
        if "DefaultAuthConfigNotFound" in msg or "does not have managed credentials" in msg:
            # Toolkit needs custom OAuth credentials (e.g. twitter) — can't use managed auth
            return {"custom_auth_required": True}
        logger.error("initiate_connection toolkit=%s user=%s error=%s", toolkit_slug, user_id, exc)
        return {"error": msg}


async def execute_action(api_key: str, user_id: str, action: str, params: dict) -> dict:
    """Execute a single Composio action and return its raw result."""
    if not api_key:
        return {"error": "No Composio API key configured"}
    composio = await _get_composio(api_key)
    try:
        result = await asyncio.to_thread(
            composio.tools.execute,
            action,
            params,
            user_id=user_id,
            dangerously_skip_version_check=True,
        )
        return result if isinstance(result, dict) else {"result": result}
    except Exception as exc:
        logger.error("execute_action action=%s error=%s", action, exc)
        return {"error": str(exc)}


# ── toolkit_exists (still used by agent integration validation routes) ─────────

async def toolkit_exists(api_key: str, slug: str) -> bool:
    """Check whether a Composio toolkit slug is valid."""
    if not api_key:
        return False
    # Fast path: if the toolkit is already in our index it definitely exists.
    if slug in _toolkit_to_slugs:
        return True
    try:
        composio = await _get_composio(api_key)
        result = await asyncio.to_thread(composio.toolkits.get, slug)
        return result is not None
    except Exception:
        return False
