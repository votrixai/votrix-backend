"""Pydantic models for chat API endpoints."""

import uuid

from pydantic import BaseModel


class ChatRequest(BaseModel):
    user_id: uuid.UUID
    session_id: uuid.UUID
    message: str
