"""Router integration tests via httpx AsyncClient."""

import pytest


async def test_org_crud(client):
    # Create
    r = await client.post("/orgs", json={"display_name": "TestOrg"})
    assert r.status_code == 201
    org = r.json()
    org_id = org["id"]

    # Get
    r = await client.get(f"/orgs/{org_id}")
    assert r.status_code == 200
    assert r.json()["display_name"] == "TestOrg"

    # List
    r = await client.get("/orgs")
    assert r.status_code == 200
    assert len(r.json()) >= 1


async def test_agent_crud(client):
    org = (await client.post("/orgs", json={"display_name": "O"})).json()
    org_id = org["id"]

    # Create agent
    r = await client.post(f"/orgs/{org_id}/agents", json={"display_name": "Bot"})
    assert r.status_code == 201
    agent = r.json()
    agent_id = agent["id"]

    # Get agent
    r = await client.get(f"/agents/{agent_id}")
    assert r.status_code == 200
    assert r.json()["display_name"] == "Bot"

    # List agents
    r = await client.get(f"/orgs/{org_id}/agents")
    assert r.status_code == 200
    assert len(r.json()) == 1


async def test_blueprint_file_crud(client):
    org = (await client.post("/orgs", json={"display_name": "O"})).json()
    agent = (await client.post(f"/orgs/{org['id']}/agents", json={"display_name": "A", "skip_defaults": True})).json()
    aid = agent["id"]

    # Write file
    r = await client.post(f"/agents/{aid}/files", json={"path": "/hello.md", "content": "world"})
    assert r.status_code == 201

    # Read file
    r = await client.get(f"/agents/{aid}/files/read", params={"path": "/hello.md"})
    assert r.status_code == 200
    assert r.json()["content"] == "world"

    # List
    r = await client.get(f"/agents/{aid}/files", params={"path": "/"})
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Delete
    r = await client.delete(f"/agents/{aid}/files", params={"path": "/hello.md"})
    assert r.status_code == 204


async def test_user_instantiation(client):
    org = (await client.post("/orgs", json={"display_name": "O"})).json()
    agent = (await client.post(f"/orgs/{org['id']}/agents", json={"display_name": "A", "skip_defaults": True})).json()
    aid = agent["id"]

    # Create blueprint file first
    await client.post(f"/agents/{aid}/files", json={"path": "/doc.md", "content": "hello"})

    # Create user
    r = await client.post(f"/orgs/{org['id']}/users", json={"display_name": "U1"})
    assert r.status_code == 201
    user = r.json()
    uid = user["id"]

    # Instantiate agent
    r = await client.post(f"/users/{uid}/agents", json={"blueprint_agent_id": aid})
    assert r.status_code == 201

    # Verify replicated file
    r = await client.get(f"/users/{uid}/agents/{aid}/files/read", params={"path": "/doc.md"})
    assert r.status_code == 200
    assert r.json()["content"] == "hello"


async def test_user_file_crud(client):
    org = (await client.post("/orgs", json={"display_name": "O"})).json()
    agent = (await client.post(f"/orgs/{org['id']}/agents", json={"display_name": "A", "skip_defaults": True})).json()
    aid = agent["id"]
    user = (await client.post(f"/orgs/{org['id']}/users", json={"display_name": "U"})).json()
    uid = user["id"]

    # Link agent
    await client.post(f"/users/{uid}/agents", json={"blueprint_agent_id": aid})

    # Write user file
    r = await client.post(
        f"/users/{uid}/agents/{aid}/files",
        json={"path": "/notes.md", "content": "my notes"},
    )
    assert r.status_code == 201

    # Read
    r = await client.get(f"/users/{uid}/agents/{aid}/files/read", params={"path": "/notes.md"})
    assert r.status_code == 200
    assert r.json()["content"] == "my notes"


async def test_agent_default_files(client):
    """Creating an agent populates default template files from prompts/agents/default/."""
    org = (await client.post("/orgs", json={"display_name": "O"})).json()
    agent = (await client.post(f"/orgs/{org['id']}/agents", json={"display_name": "D"})).json()
    aid = agent["id"]

    # Tree should contain the default files
    r = await client.get(f"/agents/{aid}/files/tree")
    assert r.status_code == 200
    tree = r.json()
    paths = {f["path"] for f in tree}
    # Spot-check key files exist
    assert "/IDENTITY.md" in paths
    assert "/SOUL.md" in paths
    assert "/skills/booking/SKILL.md" in paths
    assert len(tree) >= 15  # 21 files + dirs expected


async def test_agent_skip_defaults(client):
    """Creating an agent with skip_defaults=true produces no files."""
    org = (await client.post("/orgs", json={"display_name": "O"})).json()
    agent = (await client.post(
        f"/orgs/{org['id']}/agents",
        json={"display_name": "Empty", "skip_defaults": True},
    )).json()
    aid = agent["id"]

    r = await client.get(f"/agents/{aid}/files/tree")
    assert r.status_code == 200
    assert r.json() == []


async def test_soft_delete(client):
    """Soft-deleted agent is hidden from list but still GET-able with files intact."""
    org = (await client.post("/orgs", json={"display_name": "O"})).json()
    org_id = org["id"]
    agent = (await client.post(
        f"/orgs/{org_id}/agents",
        json={"display_name": "S", "skip_defaults": True},
    )).json()
    aid = agent["id"]

    # Add a file
    await client.post(f"/agents/{aid}/files", json={"path": "/keep.md", "content": "kept"})

    # Soft delete
    r = await client.delete(f"/agents/{aid}", params={"soft": "true"})
    assert r.status_code == 204

    # Hidden from list
    r = await client.get(f"/orgs/{org_id}/agents")
    assert all(a["id"] != aid for a in r.json())

    # Still accessible via direct GET
    r = await client.get(f"/agents/{aid}")
    assert r.status_code == 200
    assert r.json()["deleted_at"] is not None

    # Files still intact
    r = await client.get(f"/agents/{aid}/files/read", params={"path": "/keep.md"})
    assert r.status_code == 200
    assert r.json()["content"] == "kept"


async def test_hard_delete(client):
    """Hard delete removes agent and all files."""
    org = (await client.post("/orgs", json={"display_name": "O"})).json()
    agent = (await client.post(
        f"/orgs/{org['id']}/agents",
        json={"display_name": "H", "skip_defaults": True},
    )).json()
    aid = agent["id"]

    await client.post(f"/agents/{aid}/files", json={"path": "/gone.md", "content": "bye"})

    # Hard delete
    r = await client.delete(f"/agents/{aid}")
    assert r.status_code == 204

    # Agent gone
    r = await client.get(f"/agents/{aid}")
    assert r.status_code == 404


async def test_404s(client):
    import uuid
    fake = str(uuid.uuid4())
    r = await client.get(f"/orgs/{fake}")
    assert r.status_code == 404
    r = await client.get(f"/agents/{fake}")
    assert r.status_code == 404
