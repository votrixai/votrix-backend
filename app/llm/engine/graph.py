from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition

from app.llm.history.compactor import Compactor
from .nodes.model_node import call_model
from .nodes.tools_node import call_tools
from .state import GraphState


def build_graph(checkpointer: AsyncPostgresSaver, compactor: Compactor):
    """
    Compile the agent loop. Called once at startup by AgentHandler._build_graph().

    Topology:
        START → compact → model → (tools_condition) → tools → compact → model → ...
                                                             → END

    The compact node is a no-op when message count is below threshold, so it
    adds negligible overhead on short conversations.
    """
    workflow = StateGraph(GraphState)

    workflow.add_node("compact", compactor)
    workflow.add_node("model", call_model)
    workflow.add_node("tools", call_tools)

    workflow.add_edge(START, "compact")
    workflow.add_edge("compact", "model")
    workflow.add_conditional_edges("model", tools_condition)
    workflow.add_edge("tools", "compact")

    return workflow.compile(checkpointer=checkpointer)
