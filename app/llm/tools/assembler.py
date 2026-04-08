"""
ToolAssembler — per-chat-session tool assembly.

Single entry point for loader.py. Resolves integrations, delegates to the
correct handler, and splits tools into active vs deferred buckets.

Usage:
    assembler = ToolAssembler(api_key=settings.composio_api_key)
    await assembler.initialize(
        agent_integrations=agent.get("integrations") or [],
        user_id=str(body.user_id),
        agent_id=agent_id,
        session=session,
    )
    base_tools        = assembler.get_active_tools()
    deferred_tools    = assembler.get_deferred_tools_map()
"""

import logging
import uuid
from typing import Dict, List, Optional, Union

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentIntegration
from app.models.integration import Integration
from app.integrations.catalog import REGISTRY
from app.integrations.handlers import platform as platform_handler
from app.integrations.handlers import composio as composio_handler
from app.integrations.handlers import custom as custom_handler

logger = logging.getLogger(__name__)


class ToolAssembler:
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
        agent_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None,
        session_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Load all tools. Must be called before get_active_tools()."""
        for item in agent_integrations:
            ai = AgentIntegration(**item) if isinstance(item, dict) else item

            integration = self._resolve_integration(ai.integration_slug, REGISTRY)
            # Empty list = no tools enabled (explicit); do not coerce to None.
            enabled = list(ai.enabled_tool_slugs or [])

            if integration.provider_slug == "platform":
                # Platform handler splits active/deferred at the tool level
                # (web_search, web_fetch are always deferred regardless of ai.deferred).
                active, deferred = await platform_handler.load_tools(
                    integration=integration,
                    enabled_tool_slugs=enabled,
                    user_id=user_id,
                    agent_id=agent_id,
                    session=session,
                    session_id=session_id,
                    api_key=self._api_key,
                )
                if ai.deferred:
                    self._deferred_tools.extend(active + deferred)
                else:
                    self._active_tools.extend(active)
                    self._deferred_tools.extend(deferred)

            elif integration.provider_slug == "composio":
                tools = await composio_handler.load_tools_cached(
                    api_key=self._api_key,
                    user_id=user_id,
                    slugs=list(enabled),
                )
                if ai.deferred:
                    self._deferred_tools.extend(tools)
                else:
                    self._active_tools.extend(tools)

            elif integration.provider_slug == "custom":
                tools = await custom_handler.load_tools(
                    integration=integration,
                    enabled_tool_slugs=enabled,
                    user_id=user_id,
                )
                if ai.deferred:
                    self._deferred_tools.extend(tools)
                else:
                    self._active_tools.extend(tools)

            else:
                logger.warning(
                    "Unknown provider '%s' for integration '%s' — skipping",
                    integration.provider_slug, ai.integration_slug,
                )
                continue

        # Inject tool_search into active tools whenever there are deferred tools.
        if self._deferred_tools:
            self._active_tools.append(
                platform_handler.make_tool_search(self._deferred_tools)
            )

    def get_active_tools(self) -> List[BaseTool]:
        """Base tools bound to the LLM from turn 1 (includes tool_search if deferred tools exist)."""
        return list(self._active_tools)

    def get_deferred_tools_map(self) -> Dict[str, BaseTool]:
        """Deferred tools keyed by name — activated at runtime via tool_search."""
        return {t.name: t for t in self._deferred_tools}

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
