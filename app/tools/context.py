"""
ToolContext — per-chat-session tool assembly.

Single entry point for chat.py. Resolves integrations, delegates to the
correct provider, and splits tools into active vs deferred buckets.

Usage:
    ctx = ToolContext(api_key=settings.composio_api_key)
    await ctx.initialize(
        integration_slugs=["google-calendar", "platform"],
        enabled_tool_slugs={"google-calendar": ["create-event"]},
        user_id=str(body.user_id),
    )
    tools = ctx.get_active_tools()
"""

import logging
from typing import Dict, List, Optional

from langchain_core.tools import BaseTool

from app.models.tools import Integration

logger = logging.getLogger(__name__)


class ToolContext:
    def __init__(self, api_key: str = ""):
        self._api_key = api_key
        self._active_tools:   List[BaseTool] = []
        self._deferred_tools: List[BaseTool] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def initialize(
        self,
        integration_slugs: List[str],
        enabled_tool_slugs: Optional[Dict[str, List[str]]] = None,
        user_id: str = "",
    ) -> None:
        """Load all tools. Must be called before get_active_tools()."""
        from app.tools.registry import REGISTRY
        from app.tools.providers.platform import PlatformProvider
        from app.tools.providers.composio import ComposioProvider
        from app.tools.providers.custom import CustomProvider

        providers = {
            "platform": PlatformProvider(api_key=self._api_key),
            "composio": ComposioProvider(api_key=self._api_key),
            "custom":   CustomProvider(),
        }

        enabled_tool_slugs = enabled_tool_slugs or {}

        for slug in integration_slugs:
            integration = self._resolve_integration(slug, REGISTRY)
            provider = providers.get(integration.provider_id)
            if provider is None:
                logger.warning("Unknown provider '%s' for integration '%s' — skipping",
                               integration.provider_id, slug)
                continue

            enabled = enabled_tool_slugs.get(slug) or None
            tools = await provider.load_tools(
                integration=integration,
                enabled_tool_ids=enabled,
                user_id=user_id,
            )
            self._active_tools.extend(tools)

    def get_active_tools(self) -> List[BaseTool]:
        """Non-deferred tools — passed to LLM on turn 1."""
        return list(self._active_tools)

    def get_all_tools(self) -> List[BaseTool]:
        """All tools including deferred (for debugging)."""
        return list(self._active_tools) + list(self._deferred_tools)

    def get_tool_by_name(self, name: str) -> Optional[BaseTool]:
        for t in self._active_tools + self._deferred_tools:
            if t.name == name:
                return t
        return None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_integration(integration_id: str, registry: Dict[str, Integration]) -> Integration:
        """Return from static registry, or build a dynamic composio Integration."""
        if integration_id in registry:
            return registry[integration_id]

        # Unknown slug → assume it's a Composio-backed toolkit
        return Integration(
            id=integration_id,
            display_name=integration_id.replace("_", " ").title(),
            description="",
            provider_id="composio",
            provider_config={},
        )
