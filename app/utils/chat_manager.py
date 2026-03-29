"""Minimal in-memory chat manager.

Simplified from ai-core — no votrix_schema dependency. Stores events as
plain dicts and builds LangChain messages for the LLM.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Dict, List, Optional, Union

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

logger = logging.getLogger(__name__)

HISTORY_TOKEN_BUDGET = 250_000
LAYER1_SINGLE_MAX_CHARS = 60_000
_HISTORY_CHAR_BUDGET = HISTORY_TOKEN_BUDGET * 3

LAYER2_SOFT_TRIM_RATIO = 0.30
LAYER2_HARD_CLEAR_RATIO = 0.50
LAYER2_SOFT_TRIM_THRESHOLD = 4_000
LAYER2_SOFT_TRIM_HEAD = 1_500
LAYER2_SOFT_TRIM_TAIL = 1_500
LAYER2_KEEP_LAST_ASSISTANTS = 3

CONTEXT_LIMIT_TRUNCATION_NOTICE = "[truncated: output exceeded context limit]"
CONTEXT_HARD_CLEAR_NOTICE = "[Old tool result content cleared]"


def _serialize_kwargs(ak: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in ak.items():
        if isinstance(v, bytes):
            out[k] = {"__b64__": base64.b64encode(v).decode("ascii")}
        else:
            out[k] = v
    return out


def _deserialize_kwargs(ak: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in ak.items():
        if isinstance(v, dict) and tuple(v) == ("__b64__",):
            out[k] = base64.b64decode(v["__b64__"])
        else:
            out[k] = v
    return out


def _estimate_tokens(msg: BaseMessage) -> int:
    """Rough token estimate: 1 token ≈ 4 chars."""
    content = msg.content if isinstance(msg.content, str) else str(msg.content)
    return len(content) // 4 + 1


def _trim_to_token_budget(messages: List[BaseMessage], token_budget: int) -> List[BaseMessage]:
    total = 0
    cut_at = 0
    for i in range(len(messages) - 1, -1, -1):
        total += _estimate_tokens(messages[i])
        if total > token_budget:
            cut_at = i + 1
            while cut_at < len(messages) and not isinstance(messages[cut_at], HumanMessage):
                cut_at += 1
            break
    return messages[cut_at:]


def _apply_layer1_guard(messages: List[BaseMessage]) -> List[BaseMessage]:
    result: List[BaseMessage] = []
    for msg in messages:
        if isinstance(msg, ToolMessage) and isinstance(msg.content, str):
            if len(msg.content) > LAYER1_SINGLE_MAX_CHARS:
                msg = ToolMessage(
                    content=msg.content[:LAYER1_SINGLE_MAX_CHARS] + "\n" + CONTEXT_LIMIT_TRUNCATION_NOTICE,
                    tool_call_id=msg.tool_call_id,
                )
        result.append(msg)
    return result


def _apply_layer2_pruning(messages: List[BaseMessage]) -> List[BaseMessage]:
    def _chars(m: BaseMessage) -> int:
        return len(m.content) if isinstance(m.content, str) else len(str(m.content))

    total = sum(_chars(m) for m in messages)
    soft_threshold = int(_HISTORY_CHAR_BUDGET * LAYER2_SOFT_TRIM_RATIO)
    hard_threshold = int(_HISTORY_CHAR_BUDGET * LAYER2_HARD_CLEAR_RATIO)

    if total <= soft_threshold:
        return messages

    ai_indices = [i for i, m in enumerate(messages) if isinstance(m, AIMessage)]
    protect_from = (
        ai_indices[-LAYER2_KEEP_LAST_ASSISTANTS]
        if len(ai_indices) >= LAYER2_KEEP_LAST_ASSISTANTS
        else 0
    )

    messages = list(messages)

    for i in range(protect_from):
        msg = messages[i]
        if not isinstance(msg, ToolMessage) or not isinstance(msg.content, str):
            continue
        if len(msg.content) > LAYER2_SOFT_TRIM_THRESHOLD:
            old_len = len(msg.content)
            head = msg.content[:LAYER2_SOFT_TRIM_HEAD]
            tail = msg.content[-LAYER2_SOFT_TRIM_TAIL:]
            new_content = (
                f"{head}\n...\n{tail}\n"
                f"[Tool result trimmed: kept first {LAYER2_SOFT_TRIM_HEAD} chars "
                f"and last {LAYER2_SOFT_TRIM_TAIL} chars of {old_len} chars.]"
            )
            messages[i] = ToolMessage(content=new_content, tool_call_id=msg.tool_call_id)
            total -= old_len - len(new_content)

    if total <= hard_threshold:
        return messages

    for i in range(protect_from):
        if total <= hard_threshold:
            break
        msg = messages[i]
        if not isinstance(msg, ToolMessage):
            continue
        old_len = _chars(msg)
        messages[i] = ToolMessage(content=CONTEXT_HARD_CLEAR_NOTICE, tool_call_id=msg.tool_call_id)
        total -= old_len - len(CONTEXT_HARD_CLEAR_NOTICE)

    return messages


# Event types stored as plain dicts
_USER = "user"
_AGENT = "agent"
_TOOL = "tool"


class ChatManager:
    """In-memory chat manager — stores events as plain dicts."""

    def __init__(self) -> None:
        self.history: List[Dict[str, Any]] = []

    def record_user_message(self, request_id: int, user_message: str) -> None:
        self.history.append({"type": _USER, "content": user_message})

    def record_agent_message(
        self,
        request_id: int,
        ai_message: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        additional_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry: Dict[str, Any] = {"type": _AGENT, "content": ai_message}
        if tool_calls:
            entry["tool_calls"] = tool_calls
        if additional_kwargs:
            entry["additional_kwargs"] = _serialize_kwargs(additional_kwargs)
        self.history.append(entry)

    def record_tool_message(
        self, request_id: int, tool_call_id: str, func_name: str, content: str
    ) -> None:
        self.history.append({
            "type": _TOOL,
            "content": content,
            "tool_call_id": tool_call_id,
            "func_name": func_name,
        })

    def clear(self) -> None:
        self.history = []

    def build_chat_history(self, token_budget: int = HISTORY_TOKEN_BUDGET) -> List[BaseMessage]:
        messages: List[BaseMessage] = []

        for event in self.history:
            etype = event["type"]

            if etype == _USER:
                messages.append(HumanMessage(content=event["content"]))

            elif etype == _AGENT:
                tool_calls = event.get("tool_calls") or []
                tc_dicts = []
                for tc in tool_calls:
                    args = tc.get("args", "")
                    if isinstance(args, str) and args:
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            pass
                    tc_dicts.append({
                        "name": tc.get("name", ""),
                        "args": args,
                        "id": tc.get("id", ""),
                        "type": "tool_call",
                    })

                stored_ak = event.get("additional_kwargs")
                if stored_ak:
                    additional_kwargs = _deserialize_kwargs(stored_ak)
                elif tc_dicts:
                    additional_kwargs = {"__gemini_function_call_thought_signatures__": {}}
                else:
                    additional_kwargs = {}

                # Sanitize: tool-call turns must follow user/tool turns for Gemini.
                if tc_dicts:
                    prev = messages[-1] if messages else None
                    if not isinstance(prev, (HumanMessage, ToolMessage)):
                        tc_dicts = []
                        additional_kwargs.pop("__gemini_function_call_thought_signatures__", None)

                messages.append(AIMessage(
                    content=event["content"],
                    tool_calls=tc_dicts,
                    additional_kwargs=additional_kwargs,
                ))

            elif etype == _TOOL:
                prev = messages[-1] if messages else None
                if isinstance(prev, AIMessage) and getattr(prev, "tool_calls", None):
                    messages.append(ToolMessage(
                        content=event["content"],
                        tool_call_id=event.get("tool_call_id", ""),
                    ))

        # Ensure history starts from a user turn.
        first_user = next(
            (i for i, m in enumerate(messages) if isinstance(m, HumanMessage)), None
        )
        if first_user is None:
            return messages
        messages = messages[first_user:]

        messages = _apply_layer1_guard(messages)
        messages = _apply_layer2_pruning(messages)
        return _trim_to_token_budget(messages, token_budget)

    def trim_history_to_turns(self, keep: int = 5) -> None:
        user_indices = [i for i, e in enumerate(self.history) if e["type"] == _USER]
        if len(user_indices) <= keep:
            return
        start_idx = user_indices[-keep]
        self.history = self.history[start_idx:]
