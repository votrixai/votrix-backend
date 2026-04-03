"""User runtime inspection endpoints.

GET /agents/{agent_id}/user-runtime/prompt?user_id={user_id}

Returns the runtime context assembled for a specific user + agent pair,
exactly as it would be sent to the LLM. Useful for debugging.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import agents as agents_q
from app.llm.prompt.builder import build_system_prompt

router = APIRouter(prefix="/agents", tags=["user-runtime"])


class UserRuntimePromptResponse(BaseModel):
    agent_id: uuid.UUID
    user_id: uuid.UUID
    messages: list[str]


@router.get(
    "/{agent_id}/user-runtime/prompt",
    response_model=UserRuntimePromptResponse,
    summary="Preview the runtime system prompt for a user",
)
async def get_user_runtime_prompt(
    agent_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """Return the system prompt messages that would be sent to the LLM for this agent + user pair.

    Each entry in `messages` corresponds to one file under `/system-prompts/`,
    ordered by filename.
    """
    agent = await agents_q.get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    messages = await build_system_prompt(agent_id, user_id, db)
    return UserRuntimePromptResponse(agent_id=agent_id, user_id=user_id, messages=messages)
