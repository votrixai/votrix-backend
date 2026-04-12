import uuid

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: uuid.UUID
    session_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    message: str
