from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    # Append-only message history via add_messages reducer
    messages: Annotated[list[AnyMessage], add_messages]

    # Running summary of compacted older messages (persists across turns)
    summary: str

    # Per-turn loop protection counters (reset to 0 on each new turn)
    llm_call_count: int
    tool_call_count: int
