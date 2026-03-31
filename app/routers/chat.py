"""Chat endpoint — demo AI runtime.

POST /agents/{agent_id}/chat
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.engine import get_session
from app.db.queries import agents as agents_q
from app.llm import graph as llm_graph
from app.tools import composio_session

router = APIRouter(prefix="/agents", tags=["chat"])


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    user_id: uuid.UUID
    messages: List[ChatMessage]
    model: Optional[str] = "claude-sonnet-4-6"


class ChatResponse(BaseModel):
    reply: str
    messages: List[ChatMessage]


@router.post("/{agent_id}/chat", response_model=ChatResponse)
async def chat(
    agent_id: uuid.UUID,
    body: ChatRequest,
    session: AsyncSession = Depends(get_session),
):
    settings = get_settings()

    agent = await agents_q.get_agent(session, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Collect toolkit slugs configured on this agent
    toolkits = [i["integration_id"] for i in (agent.get("integrations") or [])]

    # Get Composio Tool Router meta-tools for this end user
    tools = await composio_session.get_tools(
        api_key=settings.composio_api_key,
        user_id=str(body.user_id),
        toolkits=toolkits,
    )

    # Convert to LangChain message format
    lc_messages = []
    for m in body.messages:
        if m.role == "user":
            lc_messages.append(HumanMessage(content=m.content))
        else:
            lc_messages.append(AIMessage(content=m.content))

    # Run LangGraph
    result_messages = await llm_graph.run(lc_messages, tools, model=body.model)

    # Convert back to response format (skip ToolMessages)
    response_messages = [
        ChatMessage(
            role="assistant" if isinstance(m, AIMessage) else "user",
            content=m.content if isinstance(m.content, str) else "",
        )
        for m in result_messages
        if isinstance(m, (HumanMessage, AIMessage)) and isinstance(m.content, str)
    ]

    last_ai = next((m for m in reversed(result_messages) if isinstance(m, AIMessage)), None)
    reply = last_ai.content if last_ai and isinstance(last_ai.content, str) else ""

    return ChatResponse(reply=reply, messages=response_messages)
