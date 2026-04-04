import logging
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import RemoveMessage

from app.llm.engine.state import GraphState

logger = logging.getLogger(__name__)

_TOKEN_THRESHOLD = 170_000
_SUMMARY_PREAMBLE = "[SUMMARY OF EARLIER CONVERSATION]\n"
_SUMMARIZE_PROMPT = (
    "Summarise the following conversation concisely. "
    "Preserve all key facts, decisions, and context that may be needed later.\n\n"
)


def _message_content_to_str(content: Any) -> str:
    """
    Normalize LLM message content to str (Claude/Gemini often return block lists).

    Same idea as votrix-ai-core ``ChatNodeBase._extract_text_from_response``:
    str → as-is; list → pull text from ``{"type":"text","text":...}`` dicts or
    objects with a ``.text`` attribute; else stringify.
    """
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif isinstance(block, dict) and block.get("text") is not None:
                parts.append(str(block["text"]))
            elif hasattr(block, "text"):
                parts.append(str(getattr(block, "text", "")))
            else:
                parts.append(str(block))
        return "".join(parts).strip() if parts else str(content)
    return str(content).strip()


def truncate_tool_message(msg: ToolMessage, head: int = 2500, tail: int = 2500) -> ToolMessage:
    """
    Truncate a ToolMessage content to at most head+tail characters.
    Keeps the first `head` chars and last `tail` chars with a sentinel in between.
    Returns the message unchanged if content fits within head+tail.
    """
    content = msg.content if isinstance(msg.content, str) else str(msg.content)
    if len(content) <= head + tail:
        return msg
    truncated = content[:head] + "\n...[truncated]...\n" + content[-tail:]
    return ToolMessage(
        content=truncated,
        tool_call_id=msg.tool_call_id,
        name=msg.name,
        id=msg.id,
    )


class Compactor:
    """
    LangGraph node that summarises old conversation history when the total
    estimated token count (messages + system prompts) exceeds the threshold.

    Keeps the last `keep_turns` complete user turns verbatim. If fewer than
    `keep_turns` user turns exist, still keeps the latest user message (and
    everything after it) so the model always receives a non-empty chat turn.
    Raises if no user messages are present and the token limit is exceeded.

    Graph topology:
        START → compact → model → tools_condition → tools → compact → model → ...
    """

    def __init__(self, threshold: int = _TOKEN_THRESHOLD, keep_turns: int = 6) -> None:
        self._threshold = threshold
        self._keep_turns = keep_turns

    def _token_breakdown(
        self, messages: list[BaseMessage], system_prompts: list[str]
    ) -> tuple[int, int, int]:
        """
        Rough token estimate (~chars/4). Returns (from_messages, from_system_prompts, total).

        Compaction can trigger with few or zero *chat* messages if system_prompts are huge,
        or if ToolMessage / AIMessage bodies are very large (e.g. big tool JSON).
        """
        msg_tokens = sum(
            len(m.content if isinstance(m.content, str) else str(m.content)) // 4
            for m in messages
        )
        sys_tokens = sum(len(sp) // 4 for sp in system_prompts)
        return msg_tokens, sys_tokens, msg_tokens + sys_tokens

    def _should_compact(self, messages: list[BaseMessage], system_prompts: list[str]) -> bool:
        _, _, total = self._token_breakdown(messages, system_prompts)
        return total >= self._threshold

    async def _summarize(self, messages: list[BaseMessage], llm) -> str:
        """
        Call the LLM to produce a concise summary of the given messages.
        Formats messages as a plain transcript before sending.
        """
        parts = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                parts.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                parts.append(f"Assistant: {msg.content}")
            elif isinstance(msg, ToolMessage):
                parts.append(f"Tool ({msg.name}): {msg.content}")
            elif isinstance(msg, SystemMessage):
                parts.append(f"System: {msg.content}")

        response = await llm.ainvoke(
            [HumanMessage(content=_SUMMARIZE_PROMPT + "\n".join(parts))]
        )
        return _message_content_to_str(response.content)

    async def __call__(self, state: GraphState, config: RunnableConfig) -> dict:
        messages = list(state["messages"])
        configurable = config.get("configurable", {})
        system_prompts: list[str] = configurable.get("system_prompts", [])

        msg_t, sys_t, total_est = self._token_breakdown(messages, system_prompts)
        if total_est < self._threshold:
            return {}

        human_indices = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]

        if not human_indices:
            raise RuntimeError(
                f"Token limit ({self._threshold}) exceeded but no user messages found — cannot compact."
            )

        if len(human_indices) >= self._keep_turns:
            split_idx = human_indices[-self._keep_turns]
            old = messages[:split_idx]
            recent = messages[split_idx:]
        else:
            # Fewer than keep_turns user messages total: still must not delete the
            # latest user turn. Removing all HumanMessages leaves only SystemMessage(s)
            # for the model node — Gemini then builds an empty `contents` and raises
            # ValueError: contents are required.
            split_idx = human_indices[-1]
            old = messages[:split_idx]
            recent = messages[split_idx:]

        logger.info(
            "History compaction triggered: est_total_tokens=%s (from_graph_messages=%s, "
            "from_system_prompts=%s) threshold=%s graph_message_count=%s human_turns=%s "
            "removing_messages=%s retaining_messages=%s keep_turns=%s system_prompt_sections=%s",
            total_est,
            msg_t,
            sys_t,
            self._threshold,
            len(messages),
            len(human_indices),
            len(old),
            len(recent),
            self._keep_turns,
            len(system_prompts),
        )

        llm = configurable["llm"]
        summary_text = await self._summarize(old, llm)
        summary_msg = SystemMessage(content=_SUMMARY_PREAMBLE + summary_text)

        # Prune active_tools whose anchor AIMessage is being removed.
        # Any deferred tool whose last-use message falls in the compacted region
        # is no longer referenced in retained messages, so drop it.
        removed_ids = {m.id for m in old}
        current_active: dict = state.get("active_tools", {})
        new_active = {
            name: anchor
            for name, anchor in current_active.items()
            if anchor not in removed_ids
        }

        result: dict = {
            "messages": [RemoveMessage(id=m.id) for m in old] + [summary_msg],
        }
        if new_active != current_active:
            result["active_tools"] = new_active
        return result
