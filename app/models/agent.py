"""Agent and registry models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentPrompts(BaseModel):
    identity: str = ""
    soul: str = ""
    agents: str = ""
    user: str = ""
    tools: str = ""
    bootstrap: str = ""


class AgentRegistry(BaseModel):
    bootstrap_complete: bool = False
    modules: Dict[str, Any] = {}
    connections: Dict[str, Any] = {}
    timezone: str = "UTC"


class Agent(BaseModel):
    org_id: str
    agent_id: str = "default"
    prompts: AgentPrompts = AgentPrompts()
    registry: AgentRegistry = AgentRegistry()


# ── Request models ────────────────────────────────────────────

class CreateAgentRequest(BaseModel):
    """Create a new agent within an org."""
    agent_id: str = Field(..., description="Unique agent ID within the org", examples=["default", "sales-bot"])
    prompts: Optional[AgentPrompts] = Field(None, description="Initial prompt sections. Omit to start empty.")
    registry: Optional[Dict[str, Any]] = Field(None, description="Initial registry. Omit for defaults.")
    seed_from: Optional[str] = Field(None, description="Copy prompts and files from this agent_id instead of starting empty")


class UpdateAgentRequest(BaseModel):
    """Update agent prompt sections and/or registry."""
    prompts: Optional[AgentPrompts] = Field(None, description="Prompt sections to update. Only provided fields are overwritten.")
    registry: Optional[Dict[str, Any]] = Field(None, description="Full registry replacement")


class UpdatePromptSectionRequest(BaseModel):
    """Update a single prompt section."""
    content: str = Field(..., description="New content for the prompt section")


# ── Response models ───────────────────────────────────────────

class AgentSummary(BaseModel):
    """Lightweight agent info for list responses."""
    agent_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgentDetail(BaseModel):
    """Full agent detail."""
    org_id: str
    agent_id: str
    prompts: AgentPrompts
    registry: Dict[str, Any]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
