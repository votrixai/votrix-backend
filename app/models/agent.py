from pydantic import BaseModel


class AgentConfig(BaseModel):
    slug: str
    name: str
    model: str
    skills: list[str]
    integrations: list[str]
