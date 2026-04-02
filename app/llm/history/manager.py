from typing import List
from uuid import UUID

from langchain_core.messages import BaseMessage


class HistoryManager:
    """
    Read-only view over the LangGraph checkpointer for a given thread.

    The checkpointer (AsyncPostgresSaver) owns writes — it persists state
    automatically after every graph step. This class only reads from it
    to expose conversation history to callers outside the graph (e.g. a
    GET /history endpoint or a UI that needs to display past messages).

    thread_id convention: "{agent_id}:{end_user_id}"
    """

    async def get_messages(self, agent_id: UUID, end_user_id: UUID) -> List[BaseMessage]:
        """
        Return the full message list for the given (agent, user) thread
        by reading the latest checkpoint from the checkpointer.
        """
        ...

    async def clear(self, agent_id: UUID, end_user_id: UUID) -> None:
        """
        Delete all checkpoint rows for this thread, effectively resetting
        the conversation history.
        """
        ...
