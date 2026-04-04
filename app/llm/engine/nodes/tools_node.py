from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.config import get_config_list

from app.llm.engine.state import GraphState


async def call_tools(state: GraphState, config: RunnableConfig) -> dict:
    configurable = config.get("configurable", {})
    base_tools: list = configurable.get("base_tools", [])
    deferred_tools_map: dict = configurable.get("deferred_tools_map", {})
    tools_by_name = {t.name: t for t in base_tools} | deferred_tools_map

    last_message = state["messages"][-1]
    ai_message_id: str = last_message.id  # anchor for active_tools updates

    tool_messages: list[ToolMessage] = []
    active_tools_updates: dict[str, str] = {}  # tool_name → anchor AIMessage.id

    tool_calls = last_message.tool_calls
    # Propagate graph RunnableConfig so astream_events emits on_tool_start / on_tool_end
    # (matches langgraph.prebuilt.ToolNode — ainvoke without config is invisible to the stream).
    call_configs = get_config_list(config, len(tool_calls))

    for tool_call, call_config in zip(tool_calls, call_configs, strict=True):
        name = tool_call["name"]
        tool = tools_by_name.get(name)
        try:
            if tool is None:
                raise ValueError(f"Unknown tool: {name}")
            # So astream_events on_tool_* carry the model's tool_call id (pairs start/end; SSE can match).
            cfg = dict(call_config) if call_config else {}
            md = dict(cfg.get("metadata") or {})
            md["tool_call_id"] = tool_call["id"]
            cfg["metadata"] = md
            conf = dict(cfg.get("configurable") or {})
            conf["tool_call_id"] = tool_call["id"]
            cfg["configurable"] = conf
            result = await tool.ainvoke(tool_call["args"], cfg)

            # Protocol: any handler returning {"__activate_tools__": [...]} will
            # have those deferred tools activated for subsequent model calls.
            if isinstance(result, dict) and "__activate_tools__" in result:
                for activated_name in result["__activate_tools__"]:
                    if activated_name in deferred_tools_map:
                        active_tools_updates[activated_name] = ai_message_id
                content = _format_tool_search_result(result)
            elif name in deferred_tools_map:
                # Update anchor to this AIMessage each time a deferred tool is used.
                active_tools_updates[name] = ai_message_id
                content = str(result)
            else:
                content = str(result)

            tool_messages.append(ToolMessage(
                content=content,
                tool_call_id=tool_call["id"],
                name=name,
            ))
        except Exception as e:
            tool_messages.append(ToolMessage(
                content=f"Error executing '{name}': {e}",
                tool_call_id=tool_call["id"],
                name=name,
            ))

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
