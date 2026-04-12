import json
import uuid
from unittest.mock import patch


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


async def test_chat_agent_not_built(client, provisioned_user):
    with patch("app.routers.chat._read_cache", return_value={}):
        r = await client.post(
            "/agents/marketing-agent/chat",
            json={"user_id": provisioned_user["id"], "message": "hello"},
        )
    assert r.status_code == 500


async def test_chat_streams_events(client, provisioned_user):
    async def mock_stream(*args, **kwargs):
        yield {"type": "token", "content": "Hello"}
        yield {"type": "done"}

    with (
        patch("app.routers.chat._read_cache", return_value={"env_id": "env_test123"}),
        patch("app.routers.chat.runtime.stream", new=mock_stream),
    ):
        r = await client.post(
            "/agents/marketing-agent/chat",
            json={"user_id": provisioned_user["id"], "message": "hello"},
        )

    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]

    lines = [l for l in r.text.split("\n") if l.startswith("data: ")]
    events = [json.loads(l[len("data: "):]) for l in lines]

    assert {"type": "token", "content": "Hello"} in events
    assert {"type": "done"} in events
