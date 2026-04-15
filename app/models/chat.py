import uuid

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    message: str
