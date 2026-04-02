"""Agent DAO tests."""

import uuid
import pytest
from app.db.queries.orgs import create_org
from app.db.queries.agents import create_agent, get_agent, list_agents, update_agent, delete_agent


@pytest.fixture
async def org(session):
    o = await create_org(session, display_name="TestOrg")
    await session.commit()
    return o


async def test_create_and_get(session, org):
    row = await create_agent(session, org.id, display_name="Bot1")
    agent = await get_agent(session, row["id"])
    assert agent is not None
    assert agent["display_name"] == "Bot1"


async def test_list(session, org):
    await create_agent(session, org.id, display_name="A")
    await create_agent(session, org.id, display_name="B")
    agents = await list_agents(session, org.id)
    assert len(agents) == 2


async def test_update(session, org):
    row = await create_agent(session, org.id, display_name="Old")
    updated = await update_agent(session, row["id"], display_name="New")
    assert updated["display_name"] == "New"


async def test_delete(session, org):
    row = await create_agent(session, org.id, display_name="Del")
    assert await delete_agent(session, row["id"]) is True
    assert await get_agent(session, row["id"]) is None


async def test_get_not_found(session):
    assert await get_agent(session, uuid.uuid4()) is None
