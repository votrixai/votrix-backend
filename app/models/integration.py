"""
Domain model types for the integration registry and public API.

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
    slug: str
    name: str
    type: ProviderType
    endpoint: str = ""


class Tool(BaseModel):
    slug: str
    name: str
    description: str
    input_schema: Dict[str, Any]
    # None = inherit routing from parent Integration
    provider_slug: Optional[str] = None
    provider_config: Optional[Dict[str, Any]] = None


class Integration(BaseModel):
    slug: str
    display_name: str
    description: str
    provider_slug: str
    provider_config: Dict[str, Any] = {}
    tools: List[Tool] = []
    deferred: bool = False

    def get_tool(self, tool_slug: str) -> Optional[Tool]:
        for t in self.tools:
            if t.slug == tool_slug:
                return t
        return None

    def effective_provider_slug(self, tool: Tool) -> str:
        return tool.provider_slug if tool.provider_slug is not None else self.provider_slug

    def effective_provider_config(self, tool: Tool) -> Dict[str, Any]:
        return tool.provider_config if tool.provider_config is not None else self.provider_config


# ---------------------------------------------------------------------------
# Public API response models
# ---------------------------------------------------------------------------

class ToolSchemaResponse(BaseModel):
    """Single tool as seen by the frontend."""
    slug: str
    name: str
    description: str
    input_schema: Optional[Dict[str, Any]] = None


class IntegrationSummaryResponse(BaseModel):
    """Lightweight integration row for list endpoints."""
    slug: str
    display_name: str
    description: str
    provider_type: ProviderType
    deferred: bool
    tool_count: int


class IntegrationDetailResponse(BaseModel):
    """Full integration with tool list."""
    slug: str
    display_name: str
    description: str
    provider_type: ProviderType
    deferred: bool
    tools: List[ToolSchemaResponse]
