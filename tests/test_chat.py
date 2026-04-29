import uuid


async def test_chat_session_not_found(client, db_user):
    r = await client.post(
        "/chat",
        json={"session_id": str(uuid.uuid4()), "message": "hello"},
    )
    assert r.status_code == 404
