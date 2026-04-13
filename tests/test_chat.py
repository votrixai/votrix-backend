import json
import uuid
from unittest.mock import MagicMock, patch


async def test_chat_user_not_found(client):
    r = await client.post(
        "/agents/marketing-agent/chat",
        json={"user_id": str(uuid.uuid4()), "message": "hello"},
    )
    assert r.status_code == 404


async def test_chat_user_not_provisioned(client, user):
    r = await client.post(
        "/agents/marketing-agent/chat",
        json={"user_id": user["id"], "message": "hello"},
    )
    assert r.status_code == 409


async def test_chat_session_not_found(client, provisioned_user):
    # No session created — chat should 404
    r = await client.post(
        "/agents/marketing-agent/chat",
        json={"user_id": provisioned_user["id"], "message": "hello"},
    )
    assert r.status_code == 404


async def test_chat_streams_events(client, provisioned_user):
    async def mock_stream(*args, **kwargs):
        yield {"type": "token", "content": "Hello"}
        yield {"type": "done"}

    # Create a session first so chat has a valid session_id to look up
    with (
        patch("app.routers.sessions.get_env_id", return_value="env_test123"),
        patch("app.routers.sessions.create_session", new=MagicMock(return_value="ses_test123")),
    ):
        s = await client.post(f"/users/{provisioned_user['id']}/sessions")
    assert s.status_code == 201
    session_id = s.json()["id"]

    with patch("app.routers.chat.runtime.stream", new=mock_stream):
        r = await client.post(
            "/agents/marketing-agent/chat",
            json={"user_id": provisioned_user["id"], "session_id": session_id, "message": "hello"},
        )

    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]

    lines = [l for l in r.text.split("\n") if l.startswith("data: ")]
    events = [json.loads(l[len("data: "):]) for l in lines]

    assert {"type": "token", "content": "Hello"} in events
    assert {"type": "done"} in events
