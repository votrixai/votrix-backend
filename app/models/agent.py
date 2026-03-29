"""Agent and registry models."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


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
