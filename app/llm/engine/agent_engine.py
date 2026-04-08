import asyncio
import logging
import time
from typing import AsyncGenerator, ClassVar
from uuid import UUID

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models.blueprint_agents import BlueprintAgent
from app.llm.engine.graph import build_graph
from app.llm.history.checkpoint_manager import CheckpointManager
from app.llm.history.compactor import Compactor
from app.llm.prompt.builder import build_system_prompt
from app.llm.tools.loader import load_tools
from app.utils.llm import build_chat_model

logger = logging.getLogger(__name__)


class AgentEngine:
    """
    Per-session execution engine.

    The compiled graph and checkpoint manager are class-level singletons shared
    across all instances. Call AgentEngine.init(pool) once at app startup.

    Per-session usage:
        engine = AgentEngine(agent_id, end_user_id, session_id, db_session)
        await engine.setup(agent)
        async for event in engine.astream(message): ...            # SSE
        async for event in engine.astream(message, cancel_event):  # WS
    """

    _graph: ClassVar = None
    _checkpoint_manager: ClassVar[CheckpointManager] = None

    @classmethod
    async def init(cls, pool) -> None:
        """
        Initialize the class-level graph singleton and checkpoint manager.
        Called once at app startup (lifespan).
        """
        checkpointer = AsyncPostgresSaver(pool)
        # setup() migrations include CREATE INDEX CONCURRENTLY which
        # cannot run inside a transaction. Run each migration with autocommit.
        async with pool.connection() as conn:
            await conn.set_autocommit(True)
            cur = conn.cursor()
            await cur.execute(checkpointer.MIGRATIONS[0])
            try:
                results = await cur.execute(
                    "SELECT v FROM checkpoint_migrations ORDER BY v DESC LIMIT 1"
                )
                row = await results.fetchone()
                # psycopg typically returns tuple rows; use index instead of dict access.
                version = -1 if row is None else int(row[0])
            except Exception:
                version = -1
            for v, migration in zip(
                range(version + 1, len(checkpointer.MIGRATIONS)),
                checkpointer.MIGRATIONS[version + 1:],
                strict=False,
            ):
                await cur.execute(migration)
                await cur.execute(
                    """
                    INSERT INTO checkpoint_migrations (v) VALUES (%s)
                    ON CONFLICT (v) DO NOTHING
                    """,
                    (v,),
                )
        compactor = Compactor()
        cls._graph = build_graph(checkpointer, compactor)
        cls._checkpoint_manager = CheckpointManager(pool)

    def __init__(
        self,
        agent_id: UUID,
        end_user_id: UUID,
        session_id: UUID,
        db_session: AsyncSession,
    ) -> None:
        self._agent_id = agent_id
        self._end_user_id = end_user_id
        self._session_id = session_id
        self._db_session = db_session
        self._llm = None
        self._base_tools: list = []
        self._deferred_tools_map: dict = {}
        self._system_prompts: list[str] = []

    async def setup(self, agent: BlueprintAgent) -> None:
        """
        Load and cache llm + tools + system_prompt.
        Must be called once before astream().

        The LLM is kept unbound here; model_node binds the appropriate tool
        subset each turn based on GraphState.active_tools.
        """
        settings = get_settings()
        model_name: str = agent.model or "gemini-2.0-flash"
        llm = build_chat_model(model_name, settings)

        t0 = time.perf_counter()
        self._system_prompts, bundle = await asyncio.gather(
            build_system_prompt(self._agent_id, self._end_user_id, self._db_session),
            load_tools(self._agent_id, self._end_user_id, self._db_session, agent=agent, session_id=self._session_id),
        )
        logger.info(
            "engine_setup agent_id=%s gather_ms=%.0f base_tools=%d deferred_tools=%d",
            self._agent_id,
            (time.perf_counter() - t0) * 1000,
            len(bundle["base_tools"]),
            len(bundle["deferred_tools_map"]),
        )
        self._llm = llm
        self._base_tools = bundle["base_tools"]
        self._deferred_tools_map = bundle["deferred_tools_map"]

    async def astream(
        self,
        message: str,
        images: list[str] | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream one turn. Yields raw LangChain event dicts.
        cancel_event: WS only — passed to model_node to abort mid-stream.
        images: list of public URLs to include as vision input for this turn.

        Relevant event["event"] values:
            on_chat_model_stream  → token (model node uses astream so these fire)
            on_tool_start         → tool call began
            on_tool_end           → tool call finished

        After streaming completes, prune stale checkpoint rows for this thread
        so the checkpoints table never accumulates more than one row per session.
        """
        if images:
            content: list = [
                {"type": "image_url", "image_url": {"url": url}} for url in images
            ]
            content.append({"type": "text", "text": message})
            human_msg = HumanMessage(content=content)
        else:
            human_msg = HumanMessage(content=message)

        thread_id = str(self._session_id)
        async for event in self._graph.astream_events(
            {"messages": [human_msg], "tool_call_count": 0},
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "llm": self._llm,
                    "base_tools": self._base_tools,
                    "deferred_tools_map": self._deferred_tools_map,
                    "system_prompts": self._system_prompts,
                    "cancel_event": cancel_event,
                }
            },
            version="v2",
        ):
            yield event

        await self._checkpoint_manager.prune(thread_id)
