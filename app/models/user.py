import uuid
from datetime import datetime

from pydantic import BaseModel


class CreateUserRequest(BaseModel):
    display_name: str


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    display_name: str
    role: str
    created_at: datetime


class UserResponse(BaseModel):
    id: uuid.UUID
    display_name: str
    created_at: datetime
    workspaces: list[WorkspaceResponse] = []
