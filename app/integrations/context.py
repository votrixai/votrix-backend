"""
ToolContext — per-chat-session tool assembly.

Single entry point for chat.py. Resolves integrations, delegates to the
correct provider, and splits tools into active vs deferred buckets.

Usage:
    ctx = ToolContext(api_key=settings.composio_api_key)
    await ctx.initialize(
        agent_integrations=agent.get("integrations") or [],
        user_id=str(body.user_id),
    )
    tools = ctx.get_active_tools()
"""

import logging
from typing import Dict, List, Optional, Union

from langchain_core.tools import BaseTool

from app.models.agent import AgentIntegration
from app.models.integration import Integration
from app.integrations.registry import REGISTRY
from app.integrations.providers.platform import PlatformProvider
from app.integrations.providers.composio import ComposioProvider
from app.integrations.providers.custom import CustomProvider

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
        agent_integrations: List[Union[AgentIntegration, dict]],
        user_id: str,
    ) -> None:
        """Load all tools. Must be called before get_active_tools()."""
        providers = {
            "platform": PlatformProvider(api_key=self._api_key),
            "composio": ComposioProvider(api_key=self._api_key),
            "custom":   CustomProvider(),
        }

        for item in agent_integrations:
            ai = AgentIntegration(**item) if isinstance(item, dict) else item

            integration = self._resolve_integration(ai.integration_slug, REGISTRY)
            provider = providers.get(integration.provider_slug)
            if provider is None:
                logger.warning("Unknown provider '%s' for integration '%s' — skipping",
                               integration.provider_slug, ai.integration_slug)
                continue

            enabled = ai.enabled_mcp_tool_slugs if ai.enabled_mcp_tool_slugs else None
            tools = await provider.load_tools(
                integration=integration,
                enabled_mcp_tool_slugs=enabled,
                user_id=user_id,
            )

            if ai.deferred:
                self._deferred_tools.extend(tools)
            else:
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
    def _resolve_integration(integration_slug: str, registry: Dict[str, Integration]) -> Integration:
        """Return from static registry, or build a dynamic composio Integration."""
        if integration_slug in registry:
            return registry[integration_slug]

        # Unknown slug → assume it's a Composio-backed toolkit
        return Integration(
            slug=integration_slug,
            display_name=integration_slug.replace("_", " ").title(),
            description="",
            provider_slug="composio",
            provider_config={},
        )
