"""LangGraph agent graph — demo implementation.

Two-node graph:  agent (LLM) ↔ tools
The LLM model and tools are injected at call time — graph is generic.
"""

from typing import List

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode


def build_graph(tools: List, model: str = "claude-sonnet-4-6"):
    llm = ChatAnthropic(model=model)
    llm_with_tools = llm.bind_tools(tools)

    def call_agent(state: MessagesState):
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def should_continue(state: MessagesState):
        if state["messages"][-1].tool_calls:
            return "tools"
        return END

    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_agent)
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")

    return graph.compile()


async def run(
    messages: List[BaseMessage],
    tools: List,
    model: str = "claude-sonnet-4-6",
) -> List[BaseMessage]:
    """Run one conversation turn. Returns the full updated message list."""
    graph = build_graph(tools, model)
    result = await graph.ainvoke({"messages": messages})
    return result["messages"]
