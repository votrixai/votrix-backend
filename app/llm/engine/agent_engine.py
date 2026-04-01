import asyncio
from typing import AsyncGenerator, ClassVar
from uuid import UUID

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.llm.engine.graph import build_graph
from app.llm.prompt.builder import build_system_prompt
from app.llm.tools.loader import load_tools


class AgentEngine:
    """
    Per-session execution engine.

    The compiled graph is a class-level singleton shared across all instances.
    Call AgentEngine.init(pool) once at app startup before creating any instances.

    Per-session usage:
        engine = AgentEngine(agent_id, end_user_id, session_id, db_session)
        await engine.setup(agent)
        async for event in engine.astream(message): ...            # SSE
        async for event in engine.astream(message, cancel_event):  # WS
    """

    _graph: ClassVar = None

    @classmethod
    async def init(cls, pool) -> None:
        """
        Initialize the class-level graph singleton.
        Called once at app startup (lifespan).
        """
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        cls._graph = build_graph(checkpointer)

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
        self._system_prompt: str = ""

    async def setup(self, agent: dict) -> None:
        """
        Load and cache llm + tools + system_prompt.
        Must be called once before astream().
        agent: dict from agents_q.get_agent().
        """
        settings = get_settings()
        model_name: str = agent.get("model", "claude-sonnet-4-6")

        if model_name.startswith("claude"):
            llm = ChatAnthropic(model=model_name, api_key=settings.anthropic_api_key)
        else:
            llm = ChatOpenAI(model=model_name, api_key=settings.openai_api_key)

        self._system_prompt = await build_system_prompt(self._agent_id, self._db_session)
        tools = await load_tools(self._agent_id, self._end_user_id, self._db_session)
        self._llm = llm.bind_tools(tools) if tools else llm

    async def astream(
        self,
        message: str,
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream one turn. Yields raw LangChain event dicts.
        cancel_event: WS only — passed to model_node to abort mid-stream.

        Relevant event["event"] values:
            on_chat_model_stream  → token
            on_tool_start         → tool call began
            on_tool_end           → tool call finished
        """
        async for event in self._graph.astream_events(
            {"messages": [HumanMessage(content=message)]},
            config={
                "configurable": {
                    "thread_id": str(self._session_id),
                    "llm": self._llm,
                    "system_prompt": self._system_prompt,
                    "cancel_event": cancel_event,
                }
            },
            version="v2",
        ):
            yield event
