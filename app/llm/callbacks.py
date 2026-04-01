"""Observability hooks — structured logging for LLM and tool events.

Injected into graph invocations via config["callbacks"].
Future: plug in LangSmith tracing, OpenTelemetry spans, Prometheus counters.
"""

import logging
import time
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler

logger = logging.getLogger(__name__)


class VotrixCallbackHandler(AsyncCallbackHandler):
    """Callback handler for structured logging and timing metrics.

    Logged events:
    - on_llm_start:  agent_id, user_id, timestamp
    - on_llm_end:    duration_s, token usage from llm_output
    - on_tool_start: tool name, agent_id
    - on_tool_end:   tool name, duration_s
    - on_tool_error: tool name, error message
    """

    def __init__(self, agent_id: str, user_id: str) -> None:
        super().__init__()
        self.agent_id = agent_id
        self.user_id = user_id
        self._llm_start_time: float | None = None
        # Maps run_id → (tool_name, start_time)
        self._tool_start_times: dict[str, tuple[str, float]] = {}

    async def on_llm_start(self, serialized: dict, prompts: list, *, run_id: UUID, **kwargs) -> None:
        self._llm_start_time = time.monotonic()
        model = serialized.get("kwargs", {}).get("model", "unknown")
        logger.info(f"LLM start | agent={self.agent_id} user={self.user_id} model={model}")

    async def on_llm_end(self, response, *, run_id: UUID, **kwargs) -> None:
        duration = time.monotonic() - (self._llm_start_time or time.monotonic())
        usage = (getattr(response, "llm_output", None) or {}).get("token_usage", {})
        logger.info(
            f"LLM end | agent={self.agent_id} duration={duration:.2f}s "
            f"tokens={usage}"
        )

    async def on_tool_start(
        self, serialized: dict, input_str: str, *, run_id: UUID, **kwargs
    ) -> None:
        tool_name = serialized.get("name", "unknown")
        self._tool_start_times[str(run_id)] = (tool_name, time.monotonic())
        logger.info(f"Tool start | agent={self.agent_id} tool={tool_name}")

    async def on_tool_end(self, output, *, run_id: UUID, **kwargs) -> None:
        entry = self._tool_start_times.pop(str(run_id), ("unknown", time.monotonic()))
        tool_name, start = entry
        duration = time.monotonic() - start
        logger.info(f"Tool end | agent={self.agent_id} tool={tool_name} duration={duration:.2f}s")

    async def on_tool_error(self, error: Exception, *, run_id: UUID, **kwargs) -> None:
        entry = self._tool_start_times.pop(str(run_id), ("unknown", time.monotonic()))
        tool_name, _ = entry
        logger.error(f"Tool error | agent={self.agent_id} tool={tool_name} error={error}")
