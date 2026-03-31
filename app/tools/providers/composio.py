"""
ComposioProvider — loads tools via the Composio SDK.

Singleton pattern: one ComposioToolSet per process, lazily initialized.
Composio SDK is synchronous; all calls are offloaded to a thread pool.
"""

import asyncio
import logging
from typing import List, Optional

from langchain_core.tools import BaseTool

from app.models.tools import Integration
from app.tools.providers import ToolProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_toolset = None
_lock = asyncio.Lock()


async def _get_toolset(api_key: str):
    global _toolset
    async with _lock:
        if _toolset is None:
            from composio_langchain import ComposioToolSet
            _toolset = ComposioToolSet(api_key=api_key)
    return _toolset


async def load_by_actions(api_key: str, user_id: str, actions: List[str]) -> List[BaseTool]:
    """Load specific Composio tools by action slug (e.g. TAVILY_SEARCH).

    Used by PlatformProvider for composio-routed platform tools.
    """
    if not api_key or not actions:
        return []
    try:
        toolset = await _get_toolset(api_key)
        return await asyncio.to_thread(
            toolset.get_tools, actions=actions, entity_id=user_id
        )
    except Exception as exc:
        logger.error("load_by_actions failed %s: %s", actions, exc)
        return []


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------

class ComposioProvider(ToolProvider):
    def __init__(self, api_key: str = ""):
        self._api_key = api_key

    async def load_tools(
        self,
        integration: Integration,
        enabled_tool_ids: Optional[List[str]],
        user_id: str,
    ) -> List[BaseTool]:
        if not self._api_key:
            logger.warning("No Composio API key — skipping integration: %s", integration.id)
            return []
        try:
            toolset = await _get_toolset(self._api_key)

            if enabled_tool_ids:
                return await asyncio.to_thread(
                    toolset.get_tools,
                    actions=enabled_tool_ids,
                    entity_id=user_id,
                )
            else:
                return await asyncio.to_thread(
                    toolset.get_tools,
                    apps=[integration.id.upper()],
                    entity_id=user_id,
                )
        except Exception as exc:
            logger.error("ComposioProvider.load_tools failed (%s): %s", integration.id, exc)
            return []
