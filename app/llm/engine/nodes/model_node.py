from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from app.llm.engine.state import GraphState
from app.llm.history.compactor import truncate_tool_message

DEFAULT_MAX_TOOL_ROUNDS = 10


async def call_model(state: GraphState, config: RunnableConfig) -> dict:
    configurable = config.get("configurable", {})
    llm = configurable["llm"]
    base_tools: list = configurable.get("base_tools", [])
    deferred_tools_map: dict = configurable.get("deferred_tools_map", {})
    system_prompts: list[str] = configurable.get("system_prompts", [])
    max_tool_rounds: int = configurable.get("max_tool_rounds", DEFAULT_MAX_TOOL_ROUNDS)

    # Guard: if tool_call_count has reached the limit, skip LLM invocation and
    # return a plain AIMessage (no tool_calls) so tools_condition routes to END.
    if state.get("tool_call_count", 0) >= max_tool_rounds:
        return {
            "messages": [
                AIMessage(
                    content=(
                        f"I've reached the maximum of {max_tool_rounds} tool-call "
                        "rounds for this request. Please rephrase or break your "
                        "request into smaller steps."
                    )
                )
            ]
        }

    # Bind base tools + any deferred tools currently active in this session.
    active_tools_state: dict = state.get("active_tools", {})
    active_deferred = [
        deferred_tools_map[name]
        for name in active_tools_state
        if name in deferred_tools_map
    ]
    current_tools = base_tools + active_deferred
    bound_llm = llm.bind_tools(current_tools) if current_tools else llm

    # Truncate large tool message payloads before sending to LLM.
    # In-memory only — state and checkpoint are not affected.
    messages = [truncate_tool_message(m) if isinstance(m, ToolMessage) else m for m in state["messages"]]

    if system_prompts:
        messages = [SystemMessage(content=sp) for sp in system_prompts] + messages

    response = await bound_llm.ainvoke(messages)
    return {"messages": [response]}
