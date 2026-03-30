"""Agent and AgentIntegration models."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AgentIntegration(BaseModel):
    agent_id: str = "default"
    integration_id: str
    enabled_tool_ids: List[str] = Field(default_factory=list)


class Agent(BaseModel):
    org_id: str
    agent_id: str = "default"
    agent_name: str = ""
    integrations: List[AgentIntegration] = Field(default_factory=list)


# ── Request models ────────────────────────────────────────────

class CreateAgentRequest(BaseModel):
    """Create a new agent within an org."""
    agent_id: str = Field(..., description="Unique agent ID within the org", examples=["default", "sales-bot"])
    agent_name: Optional[str] = Field(None, description="Human-friendly agent name")
    integrations: Optional[List[AgentIntegration]] = Field(
        None, description="Enabled integration tool allowlists"
    )
    seed_from: Optional[str] = Field(None, description="Copy integrations and files from this agent_id instead of starting empty")


class UpdateAgentRequest(BaseModel):
    """Update agent profile/integrations."""
    agent_name: Optional[str] = Field(None, description="Agent name")
    integrations: Optional[List[AgentIntegration]] = Field(
        None, description="Full integrations replacement"
    )


# ── Response models ───────────────────────────────────────────

class AgentSummary(BaseModel):
    """Lightweight agent info for list responses."""
    agent_id: str
    agent_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgentDetail(BaseModel):
    """Full agent detail."""
    org_id: str
    agent_id: str
    agent_name: str = ""
    integrations: List[AgentIntegration] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
