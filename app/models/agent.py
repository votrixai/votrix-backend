from pydantic import BaseModel


class IntegrationConfig(BaseModel):
    slug: str
    tools: list[str] = []


class AgentConfig(BaseModel):
    slug: str
    name: str
    model: str
    skills: list[str] = []
    integrations: list[IntegrationConfig] = []
