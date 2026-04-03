"""
Custom handler — placeholder for future MCP server integrations.

Will support connecting to arbitrary remote MCP servers, fetching schemas
via the MCP protocol, and forwarding OAuth tokens.
"""

import logging
from typing import List, Optional

from langchain_core.tools import BaseTool

from app.models.integration import Integration

logger = logging.getLogger(__name__)


async def load_tools(
    integration: Integration,
    enabled_tool_slugs: Optional[List[str]],
    user_id: str,
) -> List[BaseTool]:
    logger.warning("custom handler not yet implemented (integration: %s)", integration.slug)
    return []
