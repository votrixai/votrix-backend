import uuid


async def test_list_sessions_empty(client, user):
    r = await client.get(f"/users/{user['id']}/sessions")
    assert r.status_code == 200
    assert r.json() == []


async def test_get_session_not_found(client):
    r = await client.get(f"/sessions/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_delete_session_not_found(client):
    r = await client.delete(f"/sessions/{uuid.uuid4()}")
    assert r.status_code == 404
