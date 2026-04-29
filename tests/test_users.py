async def test_get_me(client, db_user):
    r = await client.get("/users/me")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == db_user["id"]
    assert data["display_name"] == "Test User"
    assert len(data["workspaces"]) == 1
    assert data["workspaces"][0]["role"] == "owner"


async def test_get_me_not_found(client):
    r = await client.get("/users/me")
    assert r.status_code == 404


async def test_update_me(client, db_user):
    r = await client.patch("/users/me", json={"display_name": "New Name"})
    assert r.status_code == 200
    assert r.json()["display_name"] == "New Name"
