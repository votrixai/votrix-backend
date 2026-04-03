from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.message import RemoveMessage

from app.llm.engine.state import GraphState

_TOKEN_THRESHOLD = 170_000
_SUMMARY_PREAMBLE = "[SUMMARY OF EARLIER CONVERSATION]\n"
_SUMMARIZE_PROMPT = (
    "Summarise the following conversation concisely. "
    "Preserve all key facts, decisions, and context that may be needed later.\n\n"
)


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
    `keep_turns` turns exist, compacts all messages. Raises if no user messages
    are present and the token limit is already exceeded.

    Graph topology:
        START → compact → model → tools_condition → tools → compact → model → ...
    """

    def __init__(self, threshold: int = _TOKEN_THRESHOLD, keep_turns: int = 3) -> None:
        self._threshold = threshold
        self._keep_turns = keep_turns

    def _estimate_tokens(self, messages: list[BaseMessage], system_prompts: list[str]) -> int:
        msg_tokens = sum(
            len(m.content if isinstance(m.content, str) else str(m.content)) // 4
            for m in messages
        )
        sys_tokens = sum(len(sp) // 4 for sp in system_prompts)
        return msg_tokens + sys_tokens

    def _should_compact(self, messages: list[BaseMessage], system_prompts: list[str]) -> bool:
        return self._estimate_tokens(messages, system_prompts) >= self._threshold

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
        return response.content

    async def __call__(self, state: GraphState, config: RunnableConfig) -> dict:
        messages = list(state["messages"])
        configurable = config.get("configurable", {})
        system_prompts: list[str] = configurable.get("system_prompts", [])

        if not self._should_compact(messages, system_prompts):
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
            old = messages[:]
            recent = []

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
