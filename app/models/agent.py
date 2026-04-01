"""Blueprint agent Pydantic models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateAgentRequest(BaseModel):
    """Create a new blueprint agent within an org."""
    display_name: str = Field("", description="Human-friendly agent name")
    seed_from: Optional[str] = Field(None, description="Copy integrations and files from this agent ID")
    skip_defaults: bool = Field(False, description="Skip populating default template files")


class UpdateAgentRequest(BaseModel):
    """Update agent profile."""
    display_name: Optional[str] = Field(None, description="Agent display name")


class AgentSummary(BaseModel):
    """Lightweight agent info for list responses."""
    id: str
    display_name: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AgentDetail(BaseModel):
    """Full agent detail."""
    id: str
    org_id: str
    display_name: str = ""
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
