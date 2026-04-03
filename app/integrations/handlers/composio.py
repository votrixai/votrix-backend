"""
Composio handler — loads tools via the Composio SDK (v3).

Singleton pattern: one Composio instance per process, lazily initialized.
Composio SDK is synchronous; all calls are offloaded to a thread pool.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool

from app.models.integration import Integration

logger = logging.getLogger(__name__)


# ── Singleton ─────────────────────────────────────────────────────────────────

_composio = None
_lock = asyncio.Lock()

# Per-slug tool schema cache: slug → (schemas, fetched_at)
_schema_cache: Dict[str, tuple] = {}
_SCHEMA_TTL = 86400  # 24h


async def _get_composio(api_key: str):
    global _composio
    async with _lock:
        if _composio is None:
            from composio import Composio
            from composio_langchain import LangchainProvider
            _composio = Composio(provider=LangchainProvider(), api_key=api_key)
    return _composio


# ── Helpers (used by routers and platform handler) ────────────────────────────

async def load_by_tools(api_key: str, user_id: str, tools: List[str]) -> List[BaseTool]:
    """Load specific Composio tools by action slug (e.g. GMAIL_SEND_EMAIL)."""
    if not api_key or not tools:
        return []
    try:
        composio = await _get_composio(api_key)
        return await asyncio.to_thread(
            composio.tools.get, user_id=user_id, tools=tools
        )
    except Exception as exc:
        logger.error("load_by_tools failed %s: %s", tools, exc)
        return []


async def get_toolkit_detail(api_key: str, slug: str) -> Optional[Dict[str, Any]]:
    """Fetch metadata for a single toolkit slug. Returns None if not found."""
    if not api_key:
        return None
    try:
        composio = await _get_composio(api_key)
        item = await asyncio.to_thread(composio.toolkits.get, slug)
        if item is None:
            return None
        meta = getattr(item, "meta", None)
        categories = []
        if meta and getattr(meta, "categories", None):
            categories = [getattr(c, "slug", "") for c in meta.categories]
        return {
            "slug":         getattr(item, "slug", "") or "",
            "name":         getattr(item, "name", "") or "",
            "description":  getattr(meta, "description", "") if meta else "",
            "tool_count":   int(getattr(meta, "tools_count", 0) or 0) if meta else 0,
            "categories":   categories,
            "no_auth":      getattr(item, "no_auth", False) or False,
            "auth_schemes": list(getattr(item, "auth_schemes", None) or []),
        }
    except Exception:
        return None


async def get_tool_schemas(api_key: str, toolkit_slug: str) -> List[Dict[str, Any]]:
    """Fetch tool schemas for a toolkit. Results cached per slug for 24h."""
    cached = _schema_cache.get(toolkit_slug)
    if cached:
        schemas, fetched_at = cached
        if time.time() - fetched_at < _SCHEMA_TTL:
            return schemas
    try:
        composio = await _get_composio(api_key)
        raw_tools = await asyncio.to_thread(
            composio.tools.get_raw_composio_tools,
            toolkits=[toolkit_slug],
        )
        schemas = [
            {
                "name":         getattr(t, "slug", ""),
                "description":  getattr(t, "description", ""),
                "input_schema": getattr(t, "input_parameters", None),
            }
            for t in raw_tools
        ]
        _schema_cache[toolkit_slug] = (schemas, time.time())
        return schemas
    except Exception as exc:
        logger.error("get_tool_schemas failed (%s): %s", toolkit_slug, exc)
        return []


async def toolkit_exists(api_key: str, slug: str) -> bool:
    """Check whether a Composio toolkit slug is valid."""
    if not api_key:
        return False
    try:
        composio = await _get_composio(api_key)
        result = await asyncio.to_thread(composio.toolkits.get, slug)
        return result is not None
    except Exception:
        return False


# ── Entry point ───────────────────────────────────────────────────────────────

async def load_tools(
    integration: Integration,
    enabled_tool_slugs: Optional[List[str]],
    user_id: str,
    api_key: str = "",
) -> List[BaseTool]:
    if not api_key:
        logger.warning("No Composio API key — skipping integration: %s", integration.slug)
        return []
    try:
        composio = await _get_composio(api_key)
        if enabled_tool_slugs:
            return await asyncio.to_thread(
                composio.tools.get,
                user_id=user_id,
                tools=enabled_tool_slugs,
            )
        else:
            return await asyncio.to_thread(
                composio.tools.get,
                user_id=user_id,
                toolkits=[integration.slug],
            )
    except Exception as exc:
        logger.error("composio load_tools failed (%s): %s", integration.slug, exc)
        return []
