"""Build and compile the LangGraph agent graph.

Called once at app startup (inside ChatService.initialize()).
Tools and model are injected per-invocation via config["configurable"] —
the compiled graph itself is model/tool-agnostic.

Topology:
    START → llm_call ─┬─→ END            (no tool calls / loop limit)
                       └─→ tool_executor
                               └─→ summarize → llm_call  (loop)
"""

from langgraph.graph import END, START, StateGraph

from app.llm.edges import route_after_llm
from app.llm.nodes.llm_node import llm_call
from app.llm.nodes.summarize_node import maybe_summarize
from app.llm.nodes.tool_node import tool_executor
from app.llm.state import AgentState


def build_graph(checkpointer=None, store=None):
    """Build and compile the agent StateGraph.

    Args:
        checkpointer: AsyncPostgresSaver (or MemorySaver) for per-thread session persistence.
        store: AsyncPostgresStore (or InMemoryStore) for cross-session long-term memory.

    Returns:
        CompiledStateGraph — use .ainvoke() or .astream_events() per request.
    """
    builder = StateGraph(AgentState)

    builder.add_node("llm_call", llm_call)
    builder.add_node("tool_executor", tool_executor)
    builder.add_node("summarize", maybe_summarize)

    builder.add_edge(START, "llm_call")
    builder.add_conditional_edges("llm_call", route_after_llm, ["tool_executor", END])
    builder.add_edge("tool_executor", "summarize")
    builder.add_edge("summarize", "llm_call")

    return builder.compile(checkpointer=checkpointer, store=store)
