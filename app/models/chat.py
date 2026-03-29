"""Chat request/response models."""

from typing import List, Optional

from pydantic import BaseModel


class ChatStreamMessage(BaseModel):
    role: str
    content: str


class ChatStreamRequest(BaseModel):
    session_id: str
    agent_id: str
    org_id: str
    messages: List[ChatStreamMessage]
    channel_type: Optional[str] = "web"
    user_name: Optional[str] = None
