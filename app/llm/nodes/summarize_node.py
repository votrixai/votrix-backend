"""Summarize node: compress old messages into a running summary when context grows too large.

Triggered after tool execution. If total tokens are below the threshold, this node
is a no-op (returns {} so the graph state is unchanged).
"""

import logging

from langchain_core.messages import HumanMessage, RemoveMessage
from langchain_core.runnables import RunnableConfig

from app.llm.memory.compaction import count_tokens
from app.llm.models.resolver import get_model
from app.llm.state import AgentState

logger = logging.getLogger(__name__)

COMPACTION_THRESHOLD = 200_000  # tokens — trigger summarization above this
KEEP_RECENT = 6  # number of most-recent messages to never include in the summary


async def maybe_summarize(state: AgentState, config: RunnableConfig) -> dict:
    """Conditionally compress old messages into a running summary.

    Steps:
    1. Count total tokens across all messages
    2. If below COMPACTION_THRESHOLD → no-op (return {})
    3. Split: old_messages (to summarize) vs recent[-KEEP_RECENT:] (to keep)
    4. Build prompt: extend existing summary or start fresh
    5. Call cheap summarization model
    6. Return new summary + RemoveMessage for each old message
    """
    messages = state["messages"]

    if len(messages) <= KEEP_RECENT:
        return {}

    if count_tokens(messages) < COMPACTION_THRESHOLD:
        return {}

    old_messages = messages[:-KEEP_RECENT]
    existing_summary = state.get("summary") or ""

    # Build summarization prompt
    messages_text = "\n".join(
        f"{m.type.upper()}: {m.content if isinstance(m.content, str) else str(m.content)}"
        for m in old_messages
    )

    if existing_summary:
        prompt = (
            f"Extend the existing summary below with the new conversation messages.\n\n"
            f"Existing summary:\n{existing_summary}\n\n"
            f"New messages to incorporate:\n{messages_text}"
        )
    else:
        prompt = f"Summarize the following conversation concisely:\n\n{messages_text}"

    cfg = config.get("configurable", {})
    summarization_model_name: str = cfg.get("summarization_model", "claude-haiku-4-5-20251001")

    summarize_model = get_model(summarization_model_name)
    response = await summarize_model.ainvoke([HumanMessage(content=prompt)])
    new_summary = response.content if isinstance(response.content, str) else str(response.content)

    logger.info(
        f"Compacted {len(old_messages)} messages into summary "
        f"({count_tokens(old_messages)} tokens freed)"
    )

    return {
        "summary": new_summary,
        "messages": [RemoveMessage(id=m.id) for m in old_messages],
    }
