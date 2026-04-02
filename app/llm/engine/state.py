from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    """
    Immutable-ish state threaded through the LangGraph agent loop.

    `messages` uses the `add_messages` reducer so each node returns a delta
    (new messages only) rather than the full list — LangGraph merges them.

    Runtime context (model name, tool list) is passed via RunnableConfig,
    not stored here, to keep the checkpoint payload lean.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
