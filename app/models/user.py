import uuid
from datetime import datetime

from pydantic import BaseModel


class CreateUserRequest(BaseModel):
    display_name: str
    agent_slug: str


class UserResponse(BaseModel):
    id: uuid.UUID
    display_name: str
    agent_slug: str
    anthropic_agent_id: str | None = None
    created_at: datetime


class ProvisionResponse(BaseModel):
    anthropic_agent_id: str
    provisioned: bool  # False = already existed, True = newly created
