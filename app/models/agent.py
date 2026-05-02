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


class AgentEmployeeResponse(BaseModel):
    id: str
    workspace_id: str
    agent_blueprint_id: str
    display_name: str
    slug: str
    model: str
    created_at: str


class AgentEmployeeCreateRequest(BaseModel):
    agent_slug: str


class AgentBlueprintResponse(BaseModel):
    id: str
    display_name: str
    provider: str
    slug: str
    skills: list[str]
    model: str
    is_hired: bool
    employee_id: str | None
