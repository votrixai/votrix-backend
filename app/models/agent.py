"""Blueprint agent and integration models."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AgentIntegration(BaseModel):
    integration_slug: str
    deferred: bool
    enabled_tool_slugs: List[str] = []


class UpsertAgentIntegrationRequest(BaseModel):
    deferred: bool
    enabled_tool_slugs: List[str] = []


class CreateAgentRequest(BaseModel):
    """Create a new blueprint agent within an org."""
    display_name: str = Field("", description="Human-friendly agent name")
    model: str = Field("gemini-3-flash-preview", description="LLM model identifier")
    integrations: Optional[List[AgentIntegration]] = Field(
        None, description="Integrations to enable"
    )


class UpdateAgentRequest(BaseModel):
    """Update agent profile/integrations."""
    display_name: Optional[str] = Field(None, description="Agent display name")
    model: Optional[str] = Field(None, description="LLM model identifier")
    integrations: Optional[List[AgentIntegration]] = Field(
        None, description="Full integrations replacement"
    )


class AgentSummaryResponse(BaseModel):
    """Lightweight agent info for list responses."""
    id: str
    display_name: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgentDetailResponse(BaseModel):
    """Full agent detail."""
    id: str
    org_id: str
    display_name: str = ""
    model: str = "gemini-2.0-flash"
    integrations: List[AgentIntegration] = Field(default_factory=list)
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
