from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

from app.llm.engine.state import GraphState


async def call_model(state: GraphState, config: RunnableConfig) -> dict:
    configurable = config.get("configurable", {})
    llm = configurable["llm"]
    system_prompt: str = configurable.get("system_prompt", "")

    messages = list(state["messages"])
    if system_prompt:
        messages = [SystemMessage(content=system_prompt)] + messages

    response = await llm.ainvoke(messages)
    return {"messages": [response]}
