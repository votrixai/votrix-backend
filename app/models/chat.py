import uuid
from typing import Literal

from pydantic import BaseModel, Field


class FileAttachment(BaseModel):
    file_id: str
    content_type: Literal["document", "image"]
    filename: str | None = None


class ChatRequest(BaseModel):
    session_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    message: str
    attachments: list[FileAttachment] = []
