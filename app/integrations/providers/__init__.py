"""
ToolProvider ABC — all providers implement this interface.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from langchain_core.tools import BaseTool

from app.models.integration import Integration


class ToolProvider(ABC):
    @abstractmethod
    async def load_tools(
        self,
        integration: Integration,
        enabled_tool_slugs: Optional[List[str]],
        user_id: str,
    ) -> List[BaseTool]:
        """Load tools for an integration.

        Contract:
        - enabled_tool_slugs non-empty  → return only those tools
        - enabled_tool_slugs None/empty → return ALL tools for the integration
        - Never raises; returns [] on failure
        """
        ...
