from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

from app.llm.engine.state import GraphState


async def call_model(state: GraphState, config: RunnableConfig) -> dict:
    configurable = config.get("configurable", {})
    llm = configurable["llm"]
    system_prompts: list[str] = configurable.get("system_prompts", [])

    messages = list(state["messages"])
    if system_prompts:
        messages = [SystemMessage(content=sp) for sp in system_prompts] + messages

    response = await llm.ainvoke(messages)
    return {"messages": [response]}
