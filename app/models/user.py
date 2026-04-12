import uuid
from datetime import datetime

from pydantic import BaseModel


class CreateUserRequest(BaseModel):
    display_name: str


class UserResponse(BaseModel):
    id: uuid.UUID
    display_name: str
    agent_id: str | None = None
    created_at: datetime


class ProvisionResponse(BaseModel):
    agent_id: str
    provisioned: bool  # False = already existed, True = newly created
