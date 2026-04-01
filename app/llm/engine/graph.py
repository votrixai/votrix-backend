from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition

from .nodes.model_node import call_model
from .nodes.tools_node import call_tools
from .state import GraphState


def build_graph(checkpointer: AsyncPostgresSaver):
    """
    Compile the agent loop. Called once at startup by AgentHandler._build_graph().

    Topology:
        START → model → (tools_condition) → tools → model → ...
                                          → END
    """
    workflow = StateGraph(GraphState)

    workflow.add_node("model", call_model)
    workflow.add_node("tools", call_tools)

    workflow.add_edge(START, "model")
    workflow.add_conditional_edges("model", tools_condition)
    workflow.add_edge("tools", "model")

    return workflow.compile(checkpointer=checkpointer)
