"""LLM node: invoke the model with tools bound."""

import logging

from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

from app.llm.memory.compaction import trim_to_window
from app.llm.models.fallback import invoke_with_fallback
from app.llm.models.resolver import get_model
from app.llm.state import AgentState

logger = logging.getLogger(__name__)


async def llm_call(state: AgentState, config: RunnableConfig) -> dict:
    """Invoke the LLM with the current message history and bound tools.

    Steps:
    1. Read model_name, tools, system_prompt from config["configurable"]
    2. Resolve model via get_model(), bind tools
    3. Build preamble: SystemMessage with system_prompt + optional summary
    4. Trim messages to fit context window (no LLM call needed)
    5. invoke_with_fallback (primary → backup on failure)
    6. Return updated messages and incremented llm_call_count
    """
    cfg = config.get("configurable", {})
    model_name: str = cfg.get("model_name", "claude-sonnet-4-5-20250929")
    backup_model_name: str | None = cfg.get("backup_model_name")
    tools: list = cfg.get("tools") or []
    system_prompt: str = cfg.get("system_prompt", "")
    max_context_tokens: int = cfg.get("max_context_tokens", 120_000)

    # Resolve and equip model
    model = get_model(model_name)
    if tools:
        model = model.bind_tools(tools)

    # Build system message, appending the running summary if one exists
    summary = state.get("summary") or ""
    system_content = system_prompt
    if summary:
        system_content += f"\n\n---\nConversation summary (older context):\n{summary}"
    preamble = [SystemMessage(content=system_content)] if system_content else []

    # Trim message history to stay within the context window
    trimmed = trim_to_window(state["messages"], max_context_tokens)
    full_messages = preamble + trimmed

    response = await invoke_with_fallback(
        model=model,
        messages=full_messages,
        backup_model_name=backup_model_name,
        tools=tools if tools else None,
        config=config,
    )

    return {
        "messages": [response],
        "llm_call_count": (state.get("llm_call_count") or 0) + 1,
    }
