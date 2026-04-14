import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.session import SessionResponse


class CreateUserRequest(BaseModel):
    display_name: str


class UserResponse(BaseModel):
    id: uuid.UUID
    display_name: str
    created_at: datetime
    sessions: list[SessionResponse] = []
