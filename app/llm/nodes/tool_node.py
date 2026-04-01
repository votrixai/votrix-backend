"""Tool node: execute all tool calls from the last LLM message.

Never raises — all errors are caught and returned as ToolMessage content.
"""

import asyncio
import logging

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig

from app.llm.state import AgentState

logger = logging.getLogger(__name__)

TOOL_CALL_TIMEOUT = 600  # seconds per tool call


async def tool_executor(state: AgentState, config: RunnableConfig) -> dict:
    """Execute all tool calls from state["messages"][-1].tool_calls.

    Steps:
    1. Read tools list from config["configurable"]["tools"]
    2. Build tools_by_name lookup dict
    3. For each tool_call in the last message:
       a. Look up tool by name (unknown tool → error ToolMessage)
       b. asyncio.wait_for(tool.ainvoke(args), timeout=TOOL_CALL_TIMEOUT)
       c. TimeoutError → error ToolMessage
       d. Any other Exception → error ToolMessage
    4. Return messages + incremented tool_call_count
    """
    tools: list = config.get("configurable", {}).get("tools") or []
    tools_by_name = {t.name: t for t in tools}

    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", []) or []

    results: list[ToolMessage] = []

    for tc in tool_calls:
        tool_name = tc["name"]
        tool_id = tc["id"]
        args = tc.get("args", {})

        if tool_name not in tools_by_name:
            logger.warning(f"Unknown tool requested: {tool_name!r}")
            results.append(
                ToolMessage(
                    content=f"Error: unknown tool '{tool_name}'.",
                    tool_call_id=tool_id,
                )
            )
            continue

        tool = tools_by_name[tool_name]
        try:
            output = await asyncio.wait_for(tool.ainvoke(args), timeout=TOOL_CALL_TIMEOUT)
            results.append(ToolMessage(content=str(output), tool_call_id=tool_id))
            logger.debug(f"Tool '{tool_name}' succeeded")
        except asyncio.TimeoutError:
            logger.warning(f"Tool '{tool_name}' timed out after {TOOL_CALL_TIMEOUT}s")
            results.append(
                ToolMessage(
                    content=f"Error: tool '{tool_name}' timed out after {TOOL_CALL_TIMEOUT} seconds.",
                    tool_call_id=tool_id,
                )
            )
        except Exception as e:
            logger.error(f"Tool '{tool_name}' raised {type(e).__name__}: {e}")
            results.append(
                ToolMessage(
                    content=f"Error: tool '{tool_name}' failed — {type(e).__name__}: {e}",
                    tool_call_id=tool_id,
                )
            )

    return {
        "messages": results,
        "tool_call_count": (state.get("tool_call_count") or 0) + len(tool_calls),
    }
