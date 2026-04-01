"""Blueprint agent and integration models."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AgentIntegration(BaseModel):
    integration_id: str
    deferred: bool
    enabled_tool_ids: List[str] = []


class UpsertAgentIntegrationRequest(BaseModel):
    deferred: bool
    enabled_tool_ids: List[str] = []


class CreateAgentRequest(BaseModel):
    """Create a new blueprint agent within an org."""
    name: str = Field("", description="Human-friendly agent name")
    model: str = Field("claude-sonnet-4-6", description="LLM model identifier")
    integrations: Optional[List[AgentIntegration]] = Field(
        None, description="Integrations to enable"
    )
    seed_from: Optional[str] = Field(None, description="Copy integrations and files from this agent ID")


class UpdateAgentRequest(BaseModel):
    """Update agent profile/integrations."""
    name: Optional[str] = Field(None, description="Agent display name")
    model: Optional[str] = Field(None, description="LLM model identifier")
    integrations: Optional[List[AgentIntegration]] = Field(
        None, description="Full integrations replacement"
    )


class AgentSummary(BaseModel):
    """Lightweight agent info for list responses."""
    id: str
    name: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgentDetail(BaseModel):
    """Full agent detail."""
    id: str
    org_id: str
    name: str = ""
    model: str = "claude-sonnet-4-6"
    integrations: List[AgentIntegration] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
