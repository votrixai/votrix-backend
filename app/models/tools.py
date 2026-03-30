"""
Domain model types for the tool registry.

Matches the schema in docs/tools.md §1 (registry.proto).
Pure type definitions — no static data, no business logic.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ToolResult(BaseModel):
    status: bool
    message: str


class ProviderType(str, Enum):
    UNSPECIFIED = "unspecified"
    COMPOSIO = "composio"
    CUSTOM = "custom"
    PLATFORM = "platform"


class Provider(BaseModel):
    id: str
    name: str
    type: ProviderType
    endpoint: str = ""


class Tool(BaseModel):
    id: str
    name: str
    description: str
    input_schema: Dict[str, Any]
    # None = inherit routing from parent Integration
    provider_id: Optional[str] = None
    provider_config: Optional[Dict[str, Any]] = None


class Integration(BaseModel):
    id: str
    display_name: str
    description: str
    provider_id: str
    provider_config: Dict[str, Any] = {}
    tools: List[Tool] = []
    deferred: bool = False

    def get_tool(self, tool_id: str) -> Optional[Tool]:
        for t in self.tools:
            if t.id == tool_id:
                return t
        return None

    def effective_provider_id(self, tool: Tool) -> str:
        return tool.provider_id if tool.provider_id is not None else self.provider_id

    def effective_provider_config(self, tool: Tool) -> Dict[str, Any]:
        return tool.provider_config if tool.provider_config is not None else self.provider_config
