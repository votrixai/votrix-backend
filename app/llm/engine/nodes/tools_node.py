import asyncio

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.config import get_config_list

from app.llm.engine.state import GraphState


async def _invoke_one(
    tool,
    tool_call: dict,
    call_config: dict,
    deferred_tools_map: dict,
    ai_message_id: str,
) -> tuple[ToolMessage, dict]:
    """Invoke a single tool call. Returns (ToolMessage, active_tools_updates)."""
    name = tool_call["name"]
    cfg = dict(call_config) if call_config else {}
    md = dict(cfg.get("metadata") or {})
    md["tool_call_id"] = tool_call["id"]
    cfg["metadata"] = md
    conf = dict(cfg.get("configurable") or {})
    conf["tool_call_id"] = tool_call["id"]
    cfg["configurable"] = conf

    try:
        if tool is None:
            raise ValueError(f"Unknown tool: {name}")
        result = await tool.ainvoke(tool_call["args"], cfg)

        active_update: dict = {}
        if isinstance(result, dict) and "__activate_tools__" in result:
            for activated_name in result["__activate_tools__"]:
                if activated_name in deferred_tools_map:
                    active_update[activated_name] = ai_message_id
            content = _format_tool_search_result(result)
        elif name in deferred_tools_map:
            active_update[name] = ai_message_id
            content = str(result)
        else:
            content = str(result)

    except Exception as e:
        content = f"Error executing '{name}': {e}"
        active_update = {}

    return ToolMessage(
        content=content,
        tool_call_id=tool_call["id"],
        name=name,
    ), active_update


async def call_tools(state: GraphState, config: RunnableConfig) -> dict:
    configurable = config.get("configurable", {})
    base_tools: list = configurable.get("base_tools", [])
    deferred_tools_map: dict = configurable.get("deferred_tools_map", {})
    tools_by_name = {t.name: t for t in base_tools} | deferred_tools_map

    last_message = state["messages"][-1]
    ai_message_id: str = last_message.id

    tool_calls = last_message.tool_calls
    call_configs = get_config_list(config, len(tool_calls))

    results = await asyncio.gather(*[
        _invoke_one(
            tools_by_name.get(tc["name"]),
            tc,
            cfg,
            deferred_tools_map,
            ai_message_id,
        )
        for tc, cfg in zip(tool_calls, call_configs, strict=True)
    ])

    tool_messages: list[ToolMessage] = []
    active_tools_updates: dict[str, str] = {}
    for msg, updates in results:
        tool_messages.append(msg)
        active_tools_updates.update(updates)

    out: dict = {
        "messages": tool_messages,
        "tool_call_count": state.get("tool_call_count", 0) + 1,
    }
    if active_tools_updates:
        new_active = dict(state.get("active_tools", {}))
        new_active.update(active_tools_updates)
        out["active_tools"] = new_active
    return out


def _format_tool_search_result(result: dict) -> str:
    tools = result.get("tools", [])
    if not tools:
        return "No matching tools found."
    lines = ["The following tools are now available:"]
    for t in tools:
        lines.append(f"- {t['name']}: {t['description']}")
    return "\n".join(lines)
