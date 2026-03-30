"""Blueprint agent and integration models."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AgentIntegration(BaseModel):
    integration_id: str
    enabled_tool_ids: List[str] = Field(default_factory=list)


class Agent(BaseModel):
    org_id: str
    slug: str = "default"
    name: str = ""
    integrations: List[AgentIntegration] = Field(default_factory=list)


# ── Request models ────────────────────────────────────────────

class CreateAgentRequest(BaseModel):
    """Create a new blueprint agent within an org."""
    slug: str = Field(..., description="Unique agent slug within the org", examples=["default", "sales-bot"])
    name: Optional[str] = Field(None, description="Human-friendly agent name")
    integrations: Optional[List[AgentIntegration]] = Field(
        None, description="Enabled integration tool allowlists"
    )
    seed_from: Optional[str] = Field(None, description="Copy integrations and files from this agent slug instead of starting empty")


class UpdateAgentRequest(BaseModel):
    """Update agent profile/integrations."""
    name: Optional[str] = Field(None, description="Agent display name")
    integrations: Optional[List[AgentIntegration]] = Field(
        None, description="Full integrations replacement"
    )


# ── Response models ───────────────────────────────────────────

class AgentSummary(BaseModel):
    """Lightweight agent info for list responses."""
    id: str
    slug: str
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgentDetail(BaseModel):
    """Full agent detail."""
    id: str
    org_id: str
    slug: str
    name: str = ""
    integrations: List[AgentIntegration] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
