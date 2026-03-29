"""Chat state for LangGraph."""

from typing import Any, Awaitable, Callable, Dict, List, Optional

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

from app.context.assistant_context import AssistantContext


class SystemAgentState(TypedDict):
    system_messages: List[BaseMessage]
    user_message: List[BaseMessage]
    chat_history: List[BaseMessage]
    intermediate_steps: List[BaseMessage]


class ChatState(TypedDict):
    request_id: int
    assistant_context: AssistantContext
    user_text: str
    system_agent_state: SystemAgentState
    next_node: Optional[str]
    reply_text: Optional[str]
    on_partial_reply: Optional[Callable[[str], Awaitable[None]]]
    on_tool_event: Optional[Callable[[str, str, str], Awaitable[None]]]
