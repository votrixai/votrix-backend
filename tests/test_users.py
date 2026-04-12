import uuid
from unittest.mock import patch


async def test_create_user(client):
    r = await client.post("/users", json={"display_name": "Alice"})
    assert r.status_code == 201
    data = r.json()
    assert data["display_name"] == "Alice"
    assert data["agent_id"] is None
    assert "id" in data
    # cleanup
    await client.delete(f"/users/{data['id']}")


async def test_list_users_contains_created(client, user):
    r = await client.get("/users")
    assert r.status_code == 200
    ids = [u["id"] for u in r.json()]
    assert user["id"] in ids


async def test_get_user(client, user):
    r = await client.get(f"/users/{user['id']}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == user["id"]
    assert data["display_name"] == "Test User"
    assert data["agent_id"] is None


async def test_get_user_not_found(client):
    r = await client.get(f"/users/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_delete_user_not_found(client):
    r = await client.delete(f"/users/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_provision_user(client, user):
    with patch(
        "app.routers.users.provisioning.create_user_agent",
        return_value="agt_newagent",
    ) as mock:
        r = await client.post(f"/users/{user['id']}/provision?agent_slug=marketing-agent")

    assert r.status_code == 200
    data = r.json()
    assert data["agent_id"] == "agt_newagent"
    assert data["provisioned"] is True
    mock.assert_called_once_with(
        slug="marketing-agent",
        user_id=user["id"],
        display_name="Test User",
    )


async def test_provision_user_idempotent(client, provisioned_user):
    with patch("app.routers.users.provisioning.create_user_agent") as mock:
        r = await client.post(
            f"/users/{provisioned_user['id']}/provision?agent_slug=marketing-agent"
        )
    assert r.status_code == 200
    data = r.json()
    assert data["agent_id"] == "agt_test123"
    assert data["provisioned"] is False
    mock.assert_not_called()


async def test_provision_user_not_found(client):
    r = await client.post(f"/users/{uuid.uuid4()}/provision?agent_slug=marketing-agent")
    assert r.status_code == 404
