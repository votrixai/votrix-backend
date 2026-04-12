from pydantic import BaseModel


class AgentConfig(BaseModel):
    slug: str
    name: str
    model: str
    skills: list[str]
    integrations: list[str]


class AgentCache(BaseModel):
    agent_id: str
    env_id: str
    version: int


class AgentDetail(BaseModel):
    config: AgentConfig
    provisioned: bool
    cache: AgentCache | None = None
