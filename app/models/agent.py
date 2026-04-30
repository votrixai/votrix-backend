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


class AgentBlueprintResponse(BaseModel):
    id: str
    display_name: str
    provider: str
    slug: str
    skills: list[str]
    model: str
    is_hired: bool
    employee_id: str | None
