"""Conditional routing logic between graph nodes."""

from typing import Literal

from langgraph.graph import END

from app.llm.state import AgentState

MAX_LLM_CALLS = 25
MAX_TOOL_CALLS = 50


def route_after_llm(state: AgentState) -> Literal["tool_executor", "__end__"]:
    """Decide next step after the LLM node runs.

    - Loop limit exceeded → END (safety guard)
    - Last message has tool_calls → "tool_executor"
    - Otherwise → END (final response, no tool use)
    """
    if (state.get("llm_call_count") or 0) >= MAX_LLM_CALLS:
        return END
    if (state.get("tool_call_count") or 0) >= MAX_TOOL_CALLS:
        return END

    last_message = state["messages"][-1] if state["messages"] else None
    if last_message and getattr(last_message, "tool_calls", None):
        return "tool_executor"

    return END
