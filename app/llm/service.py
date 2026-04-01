"""ChatService — top-level entry point for the chat router.

Lifecycle (in app/main.py lifespan):
    service = ChatService(db_url=settings.database_url)
    await service.initialize()
    app.state.chat_service = service

Per-request (in chat router):
    stream = service.chat(
        messages=[HumanMessage(content="hello")],
        thread_id="session-abc-123",
        agent_config=agent,
        tools=tools,
        user_id="user-456",
    )
    return StreamingResponse(stream, media_type="text/event-stream")
"""

import logging
from typing import AsyncIterator

from app.llm.callbacks import VotrixCallbackHandler
from app.llm.graph import build_graph
from app.llm.memory.checkpointer import create_checkpointer
from app.llm.memory.store import create_store
from app.llm.prompts.assembler import build_system_prompt
from app.llm.streaming import stream_graph_events

logger = logging.getLogger(__name__)


class ChatService:
    """Manages the compiled LangGraph and memory backends. Created once at startup."""

    def __init__(self, db_url: str) -> None:
        self._db_url = db_url
        self._graph = None
        self._checkpointer = None
        self._store = None

    async def initialize(self) -> None:
        """Set up checkpointer, store, and compile the graph. Call once at startup."""
        self._checkpointer = await create_checkpointer(self._db_url)
        self._store = await create_store(self._db_url)
        self._graph = build_graph(checkpointer=self._checkpointer, store=self._store)
        logger.info("ChatService initialized")

    async def chat(
        self,
        messages: list,
        thread_id: str,
        agent_config: dict,
        tools: list,
        user_id: str,
        model_name: str = "claude-sonnet-4-5-20250929",
        backup_model_name: str | None = None,
    ) -> AsyncIterator[str]:
        """Run one chat turn. Returns an async SSE stream.

        Steps:
        1. Build system prompt from agent_config + active tool names
        2. Assemble config with thread_id, model, tools, callbacks
        3. Build input_state (new messages + reset loop counters)
        4. Return stream_graph_events generator
        """
        tool_names = [t.name for t in tools]
        system_prompt = build_system_prompt(agent_config, tool_names)

        config = {
            "configurable": {
                "thread_id": thread_id,
                "model_name": model_name,
                "backup_model_name": backup_model_name,
                "system_prompt": system_prompt,
                "tools": tools,
                "max_context_tokens": 120_000,
                "summarization_model": "claude-haiku-4-5-20251001",
            },
            "callbacks": [
                VotrixCallbackHandler(
                    agent_id=str(agent_config.get("id", "")),
                    user_id=user_id,
                )
            ],
        }

        # Reset per-turn loop counters. Messages append via add_messages reducer.
        # summary is NOT included here — it persists from the checkpointer.
        input_state = {
            "messages": messages,
            "llm_call_count": 0,
            "tool_call_count": 0,
        }

        return stream_graph_events(self._graph, input_state, config)

    async def get_thread_history(self, thread_id: str) -> list:
        """Retrieve the full message history for a thread from the checkpointer."""
        config = {"configurable": {"thread_id": thread_id}}
        state = await self._graph.aget_state(config)
        return state.values.get("messages", []) if state else []

    async def delete_thread(self, thread_id: str) -> None:
        """Delete all checkpoints for a thread (GDPR deletion, user-initiated clear)."""
        if self._checkpointer and hasattr(self._checkpointer, "adelete_thread"):
            await self._checkpointer.adelete_thread(thread_id)
