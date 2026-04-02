"""Pydantic models for agent integrations and tools."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Integration catalog
# ---------------------------------------------------------------------------

class CreateIntegrationRequest(BaseModel):
    slug: str = Field(..., description="Unique slug, e.g. 'google-calendar'")
    display_name: str = Field("", description="Human-readable name")
    description: str = ""
    provider_slug: str = Field("", description="Provider identifier, e.g. 'google'")
    provider_config: dict = Field(default_factory=dict, description="Connection settings")


class UpdateIntegrationRequest(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    provider_slug: Optional[str] = None
    provider_config: Optional[dict] = None


class IntegrationDetail(BaseModel):
    id: str
    slug: str
    display_name: str = ""
    description: str = ""
    provider_slug: str = ""
    provider_config: dict = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Integration tool catalog
# ---------------------------------------------------------------------------

class CreateToolRequest(BaseModel):
    slug: str = Field(..., description="Tool slug unique within integration, e.g. 'create-event'")
    display_name: str = ""
    description: str = ""


class UpdateToolRequest(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None


class ToolDetail(BaseModel):
    id: str
    agent_integration_id: str
    slug: str
    display_name: str = ""
    description: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Blueprint agent ↔ integration links
# ---------------------------------------------------------------------------

class BlueprintAgentIntegrationDetail(BaseModel):
    id: str
    blueprint_agent_id: str
    agent_integration_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BlueprintAgentIntegrationToolDetail(BaseModel):
    id: str
    blueprint_agent_integration_id: str
    agent_integration_tool_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
