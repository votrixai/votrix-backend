import asyncio
import json
import logging
from typing import Literal
from uuid import UUID

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.queries import agents as agents_q
from app.llm.engine.agent_engine import AgentEngine

logger = logging.getLogger(__name__)

Phase = Literal["idle", "model", "tools"]


class WSHandler:
    """
    Per-connection WebSocket state machine.

    One instance per connected client. AgentEngine is created once at
    connection time and reused across all messages in the session.

    Interrupt rules:
        idle  → new message starts immediately
        model → new message cancels current model call, starts fresh with new message
        tools → new message is queued, runs after tools finish
    """

    def __init__(
        self,
        websocket: WebSocket,
        agent_id: UUID,
        end_user_id: UUID,
        session_id: UUID,
        db_session: AsyncSession,
    ) -> None:
        self._websocket = websocket
        self._agent_id = agent_id
        self._end_user_id = end_user_id
        self._session_id = session_id
        self._db_session = db_session

        self._engine: AgentEngine | None = None
        self._phase: Phase = "idle"
        self._cancel_event = asyncio.Event()
        self._pending_message: str | None = None
        self._queue: asyncio.Queue[str] = asyncio.Queue()

    async def setup(self) -> None:
        """Load agent and initialize AgentEngine once at connection time."""
        agent = await agents_q.get_agent(self._db_session, self._agent_id)
        if not agent:
            await self._websocket.close(code=4004, reason="Agent not found")
            return
        self._engine = AgentEngine(
            self._agent_id, self._end_user_id, self._session_id, self._db_session
        )
        await self._engine.setup(agent)

    async def run(self) -> None:
        """Run receiver and runner concurrently until disconnect."""
        await asyncio.gather(self._receiver(), self._runner())

    async def _receiver(self) -> None:
        """Read incoming text frames and route based on current phase."""
        try:
            while True:
                message = await self._websocket.receive_text()

                if self._phase == "idle":
                    await self._queue.put(message)

                elif self._phase == "model":
                    self._pending_message = message
                    self._cancel_event.set()

                elif self._phase == "tools":
                    self._pending_message = message

        except WebSocketDisconnect:
            pass

    async def _runner(self) -> None:
        """Serial consumer — pulls messages and drives the agent loop."""
        while True:
            message = await self._queue.get()

            while message:
                self._phase = "model"
                self._cancel_event.clear()
                cancelled = False
                ai_tokens: list[str] = []
                stream_ok = True

                try:
                    async for event in self._engine.astream(
                        message, cancel_event=self._cancel_event
                    ):
                        kind = event["event"]

                        if kind == "on_chat_model_stream":
                            content = event["data"]["chunk"].content
                            if isinstance(content, str):
                                frag = content
                            elif isinstance(content, list):
                                frag = "".join(
                                    b.get("text", "") for b in content
                                    if isinstance(b, dict) and b.get("type") == "text"
                                )
                            else:
                                frag = ""
                            if frag:
                                ai_tokens.append(frag)
                                await self._send({"type": "token", "content": frag})

                        elif kind == "on_tool_start":
                            self._phase = "tools"
                            # Same id for start/end: model tool_call id from event data, not graph run_id.
                            _d = event.get("data")
                            _tcid = ""
                            if isinstance(_d, dict):
                                _t = _d.get("tool_call_id")
                                if _t is not None and str(_t).strip():
                                    _tcid = str(_t)
                            if not _tcid and event.get("run_id") is not None:
                                _tcid = str(event["run_id"])
                            await self._send({
                                "type": "tool_start",
                                "tool_call_id": _tcid,
                                "name": event["name"],
                            })

                        elif kind == "on_tool_end":
                            self._phase = "model"
                            _d = event.get("data")
                            _tcid = ""
                            if isinstance(_d, dict):
                                _t = _d.get("tool_call_id")
                                if _t is not None and str(_t).strip():
                                    _tcid = str(_t)
                            if not _tcid and event.get("run_id") is not None:
                                _tcid = str(event["run_id"])
                            await self._send({
                                "type": "tool_end",
                                "tool_call_id": _tcid,
                            })

                        if self._cancel_event.is_set():
                            cancelled = True
                            break

                except Exception as e:
                    stream_ok = False
                    logger.exception(
                        "WebSocket agent stream failed agent_id=%s session_id=%s",
                        self._agent_id,
                        self._session_id,
                    )
                    await self._send({"type": "error", "message": str(e)})

                if cancelled and self._pending_message:
                    message = self._pending_message
                    self._pending_message = None
                else:
                    if not cancelled and stream_ok:
                        reply_text = "".join(ai_tokens)
                        if reply_text:
                            logger.info(
                                "AI reply preview: %s",
                                reply_text[:400].replace("\n", " "),
                            )
                        await self._send({"type": "done"})
                        if self._pending_message:
                            message = self._pending_message
                            self._pending_message = None
                        else:
                            self._phase = "idle"
                            message = None

    async def _send(self, payload: dict) -> None:
        await self._websocket.send_text(json.dumps(payload))
