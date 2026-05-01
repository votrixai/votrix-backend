import uuid


async def test_list_sessions_empty(client, db_user):
    r = await client.get("/sessions", headers={"X-Workspace-Id": db_user["workspace_id"]})
    assert r.status_code == 200
    assert r.json() == []


async def test_get_session_not_found(client, db_user):
    r = await client.get(
        f"/sessions/{uuid.uuid4()}",
        headers={"X-Workspace-Id": db_user["workspace_id"]},
    )
    assert r.status_code == 404


async def test_delete_session_not_found(client, db_user):
    r = await client.delete(
        f"/sessions/{uuid.uuid4()}",
        headers={"X-Workspace-Id": db_user["workspace_id"]},
    )
    assert r.status_code == 404


async def test_sessions_missing_workspace_header_returns_400(client, db_user):
    r = await client.get("/sessions")
    assert r.status_code == 400
