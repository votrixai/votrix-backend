"""SSE chat route: token events, done, and content-shape handling (str / block list)."""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.db.engine import get_session
from app.models.session import SessionEventType
from app.routers import chat as chat_module


@pytest.fixture
def chat_app():
    """Minimal app with chat router only — no DB pool / LangGraph lifespan."""
    app = FastAPI()
    app.include_router(chat_module.router)

    async def override_session():
        yield AsyncMock()

    app.dependency_overrides[get_session] = override_session
    return app


def _parse_sse_data_lines(body: str) -> list[dict]:
    """Extract JSON payloads from ``data: {...}`` lines."""
    out: list[dict] = []
    for block in body.split("\n\n"):
        for line in block.split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                raw = line[5:].strip()
                if raw:
                    out.append(json.loads(raw))
    return out


def test_chat_sse_streams_string_tokens_and_done(monkeypatch, chat_app):
    agent_id = uuid.uuid4()
    fake_agent = SimpleNamespace(
        id=agent_id,
        model="claude-sonnet-4-6",
        org_id=uuid.uuid4(),
        display_name="test",
        deleted_at=None,
    )

    async def fake_get_agent(session, aid):
        assert aid == agent_id
        return fake_agent

    monkeypatch.setattr(chat_module.agents_q, "get_agent", fake_get_agent)
    monkeypatch.setattr(chat_module.sessions_q, "upsert_session", AsyncMock())
    monkeypatch.setattr(chat_module.sessions_q, "append_event", AsyncMock())

    class FakeEngine:
        def __init__(self, *args, **kwargs):
            pass

        async def setup(self, agent):
            pass

        async def astream(self, message: str):
            class Chunk:
                def __init__(self, content):
                    self.content = content

            assert message == "ping"
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": Chunk("Hel")},
                "run_id": "r1",
            }
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": Chunk("lo")},
                "run_id": "r1",
            }

    monkeypatch.setattr(chat_module, "AgentEngine", FakeEngine)

    uid, sid = uuid.uuid4(), uuid.uuid4()
    with TestClient(chat_app) as client:
        r = client.post(
            f"/agents/{agent_id}/chat",
            json={
                "user_id": str(uid),
                "session_id": str(sid),
                "message": "ping",
            },
        )

    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("text/event-stream")
    events = _parse_sse_data_lines(r.text)
    assert [e.get("type") for e in events[:-1]] == ["token", "token"]
    assert events[0]["content"] == "Hel"
    assert events[1]["content"] == "lo"
    assert events[-1] == {"type": "done"}

    append = chat_module.sessions_q.append_event
    assert append.await_count >= 2
    ai_calls = [
        c
        for c in append.await_args_list
        if c.kwargs.get("event_type") == SessionEventType.ai_message
    ]
    assert len(ai_calls) == 1
    assert ai_calls[0].kwargs.get("event_body") == "Hello"


def test_chat_sse_list_content_blocks_yield_tokens(monkeypatch, chat_app):
    """Anthropic-style chunk.content as list of {type, text} dicts."""
    agent_id = uuid.uuid4()
    fake_agent = SimpleNamespace(
        id=agent_id,
        model="claude-sonnet-4-6",
        org_id=uuid.uuid4(),
        display_name="test",
        deleted_at=None,
    )

    async def fake_get_agent(session, aid):
        return fake_agent

    monkeypatch.setattr(chat_module.agents_q, "get_agent", fake_get_agent)
    monkeypatch.setattr(chat_module.sessions_q, "upsert_session", AsyncMock())
    monkeypatch.setattr(chat_module.sessions_q, "append_event", AsyncMock())

    class FakeEngine:
        def __init__(self, *args, **kwargs):
            pass

        async def setup(self, agent):
            pass

        async def astream(self, message: str):
            class Chunk:
                def __init__(self, content):
                    self.content = content

            yield {
                "event": "on_chat_model_stream",
                "data": {
                    "chunk": Chunk([{"type": "text", "text": "OK"}]),
                },
                "run_id": "r2",
            }

    monkeypatch.setattr(chat_module, "AgentEngine", FakeEngine)

    uid, sid = uuid.uuid4(), uuid.uuid4()
    with TestClient(chat_app) as client:
        r = client.post(
            f"/agents/{agent_id}/chat",
            json={
                "user_id": str(uid),
                "session_id": str(sid),
                "message": "x",
            },
        )

    assert r.status_code == 200
    events = _parse_sse_data_lines(r.text)
    assert events[0] == {"type": "token", "content": "OK"}
    assert events[-1] == {"type": "done"}


def test_chat_sse_tool_then_text(monkeypatch, chat_app):
    """Tool call round followed by a final text reply (list-format content)."""
    agent_id = uuid.uuid4()
    fake_agent = SimpleNamespace(
        id=agent_id,
        model="claude-sonnet-4-6",
        org_id=uuid.uuid4(),
        display_name="test",
        deleted_at=None,
    )

    async def fake_get_agent(session, aid):
        return fake_agent

    monkeypatch.setattr(chat_module.agents_q, "get_agent", fake_get_agent)
    monkeypatch.setattr(chat_module.sessions_q, "upsert_session", AsyncMock())
    monkeypatch.setattr(chat_module.sessions_q, "append_event", AsyncMock())

    class FakeEngine:
        def __init__(self, *args, **kwargs):
            pass

        async def setup(self, agent):
            pass

        async def astream(self, message: str):
            class Chunk:
                def __init__(self, content):
                    self.content = content

            # First: a tool call round (no text tokens)
            yield {"event": "on_tool_start", "name": "search", "run_id": "t1",
                   "data": {"input": {"query": "emails"}}}
            yield {"event": "on_tool_end", "name": "search", "run_id": "t1",
                   "data": {"output": "results"}}
            # Then: model final text reply as Anthropic list-format content
            yield {"event": "on_chat_model_stream",
                   "data": {"chunk": Chunk([{"type": "text", "text": "Done"}])},
                   "run_id": "r2"}

    monkeypatch.setattr(chat_module, "AgentEngine", FakeEngine)

    uid, sid = uuid.uuid4(), uuid.uuid4()
    with TestClient(chat_app) as client:
        r = client.post(
            f"/agents/{agent_id}/chat",
            json={"user_id": str(uid), "session_id": str(sid), "message": "check"},
        )

    assert r.status_code == 200
    events = _parse_sse_data_lines(r.text)
    types = [e["type"] for e in events]
    assert "tool_start" in types
    assert "tool_end" in types
    assert {"type": "token", "content": "Done"} in events
    assert events[-1] == {"type": "done"}

    append = chat_module.sessions_q.append_event
    ai_calls = [
        c for c in append.await_args_list
        if c.kwargs.get("event_type") == SessionEventType.ai_message
    ]
    assert len(ai_calls) == 1
    assert ai_calls[0].kwargs["event_body"] == "Done"


def test_chat_sse_error_event_on_engine_failure(monkeypatch, chat_app):
    agent_id = uuid.uuid4()
    fake_agent = SimpleNamespace(
        id=agent_id,
        model="claude-sonnet-4-6",
        org_id=uuid.uuid4(),
        display_name="test",
        deleted_at=None,
    )

    async def fake_get_agent(session, aid):
        return fake_agent

    monkeypatch.setattr(chat_module.agents_q, "get_agent", fake_get_agent)
    monkeypatch.setattr(chat_module.sessions_q, "upsert_session", AsyncMock())
    monkeypatch.setattr(chat_module.sessions_q, "append_event", AsyncMock())

    class FakeEngine:
        def __init__(self, *args, **kwargs):
            pass

        async def setup(self, agent):
            pass

        async def astream(self, message: str):
            raise RuntimeError("boom")
            yield  # pragma: no cover

    monkeypatch.setattr(chat_module, "AgentEngine", FakeEngine)

    uid, sid = uuid.uuid4(), uuid.uuid4()
    with TestClient(chat_app) as client:
        r = client.post(
            f"/agents/{agent_id}/chat",
            json={
                "user_id": str(uid),
                "session_id": str(sid),
                "message": "x",
            },
        )

    assert r.status_code == 200
    events = _parse_sse_data_lines(r.text)
    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "boom" in events[0]["message"]
