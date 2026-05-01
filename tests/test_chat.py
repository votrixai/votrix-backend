import uuid


async def test_chat_session_not_found(client, db_user):
    r = await client.post(
        "/chat",
        json={"session_id": str(uuid.uuid4()), "message": "hello"},
        headers={"X-Workspace-Id": db_user["workspace_id"]},
    )
    assert r.status_code == 404


async def test_chat_missing_workspace_header_returns_400(client, db_user):
    r = await client.post(
        "/chat",
        json={"session_id": str(uuid.uuid4()), "message": "hello"},
    )
    assert r.status_code == 400
