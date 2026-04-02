"""
CustomProvider — placeholder for future MCP server integrations.

Will support connecting to arbitrary remote MCP servers, fetching schemas
via the MCP protocol, and forwarding OAuth tokens.
"""

import logging
from typing import List, Optional

from langchain_core.tools import BaseTool

from app.models.tools import Integration
from app.integrations.providers import ToolProvider

logger = logging.getLogger(__name__)


class CustomProvider(ToolProvider):
    async def load_tools(
        self,
        integration: Integration,
        enabled_tool_ids: Optional[List[str]],
        user_id: str,
    ) -> List[BaseTool]:
        logger.warning("CustomProvider is not yet implemented (integration: %s)", integration.id)
        return []
