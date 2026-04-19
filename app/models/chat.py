from typing import Literal

from pydantic import BaseModel


class FileAttachment(BaseModel):
    file_id: str
    content_type: Literal["document", "image"]
    filename: str | None = None


class ChatRequest(BaseModel):
    session_id: str
    message: str
    attachments: list[FileAttachment] = []
