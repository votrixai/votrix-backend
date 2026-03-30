"""Chat request/response models."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ChatStreamMessage(BaseModel):
    """A single message in the conversation."""

    role: str = Field(..., description="Message role: 'user', 'assistant', or 'tool'")
    content: str = Field(..., description="Message content")

    model_config = {"json_schema_extra": {"examples": [{"role": "user", "content": "Hello"}]}}


class ChatStreamRequest(BaseModel):
    """Request body for POST /chat/stream.

    The last message with role='user' is sent to the LLM.
    Response is streamed in Vercel AI SDK data stream protocol (text/plain, code:json lines).
    """

    session_id: str = Field(..., description="Chat session ID (created if not exists)")
    agent_id: str = Field(..., description="Agent ID within the org", examples=["default"])
    org_id: str = Field(..., description="Organization/tenant ID")
    messages: List[ChatStreamMessage] = Field(..., description="Conversation messages (last user message is sent to LLM)")
    channel_type: Optional[str] = Field("web", description="Channel type: 'web', 'whatsapp', 'phone', etc.")
    user_name: Optional[str] = Field(None, description="Display name of the user")
