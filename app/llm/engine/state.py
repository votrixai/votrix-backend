from typing import Annotated, Dict, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    """
    Immutable-ish state threaded through the LangGraph agent loop.

    `messages` uses the `add_messages` reducer so each node returns a delta
    (new messages only) rather than the full list — LangGraph merges them.

    `active_tools` tracks deferred tools that have been activated via tool_search.
    Maps tool_name → the id of the AIMessage that last triggered/used that tool.
    Used by model_node to bind the right tool schemas each turn, and pruned by
    the compactor when the anchor message is summarised away.

    `tool_call_count` counts completed tool-call rounds in the current turn.
    Reset to 0 on each new human message (fresh state). model_node checks this
    against max_tool_rounds before invoking the LLM; if exceeded it injects a
    limit-notice AIMessage and the graph routes to END.

    Runtime context (model name, tool list) is passed via RunnableConfig,
    not stored here, to keep the checkpoint payload lean.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    active_tools: Dict[str, str]  # tool_name → anchor AIMessage.id
    tool_call_count: int           # incremented by tools_node each round
