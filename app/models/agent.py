from pydantic import BaseModel


class AgentConfig(BaseModel):
    name: str
    model: str
    skills: list[str]
    integrations: list[str]
