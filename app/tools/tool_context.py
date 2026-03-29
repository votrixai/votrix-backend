"""Tool context — ContextVar for passing AssistantContext to tools."""

from contextvars import ContextVar
from typing import Any, Optional

_tool_context: ContextVar[Optional[Any]] = ContextVar("tool_context", default=None)


def set_tool_context(ctx: Any):
    return _tool_context.set(ctx)


def reset_tool_context(token) -> None:
    _tool_context.reset(token)


def get_tool_context() -> Optional[Any]:
    return _tool_context.get()
