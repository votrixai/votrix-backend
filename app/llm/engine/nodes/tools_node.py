from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig

from app.llm.engine.state import GraphState


async def call_tools(state: GraphState, config: RunnableConfig) -> dict:
    configurable = config.get("configurable", {})
    tools: list = configurable.get("tools", [])
    tools_by_name = {t.name: t for t in tools}

    last_message = state["messages"][-1]
    tool_messages = []

    for tool_call in last_message.tool_calls:
        tool = tools_by_name.get(tool_call["name"])
        try:
            if tool is None:
                raise ValueError(f"Unknown tool: {tool_call['name']}")
            result = await tool.ainvoke(tool_call["args"])
            tool_messages.append(ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"],
                name=tool_call["name"],
            ))
        except Exception as e:
            tool_messages.append(ToolMessage(
                content=f"Error executing '{tool_call['name']}': {e}",
                tool_call_id=tool_call["id"],
                name=tool_call["name"],
            ))

    return {"messages": tool_messages}
