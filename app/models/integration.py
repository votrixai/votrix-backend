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
    name: str                              # unique identifier + LangChain tool name
    description: str
    input_schema: Dict[str, Any]           # JSON Schema, for API display only
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


# ---------------------------------------------------------------------------
# Public API response models
# ---------------------------------------------------------------------------

class PropertyDef(BaseModel):
    """Single input parameter definition, as seen by the frontend."""
    type: str                          # "string" | "integer" | "number" | "boolean" | "array" | "object"
    description: str = ""
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    items_type: Optional[str] = None   # element type when type == "array"


class InputSchemaDef(BaseModel):
    """Flattened, frontend-friendly representation of a tool's input schema."""
    properties: Dict[str, PropertyDef]


class ToolSchemaResponse(BaseModel):
    """Single tool as seen by the frontend."""
    name: str
    description: str
    input_schema: Optional[InputSchemaDef] = None


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
