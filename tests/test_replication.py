"""Agent instantiation + replication tests."""

import uuid
import pytest
from app.db.queries.orgs import create_org
from app.db.queries.agents import create_agent
from app.db.queries.end_user_accounts import create_end_user_account
from app.db.queries import blueprint_files as bf
from app.db.queries import user_files as uf
from app.db.queries.end_user_agents import (
    link_agent,
    get_link,
    unlink_agent,
    replicate_blueprint_to_user,
)


@pytest.fixture
async def setup(session):
    """Return (agent_id, user_id)."""
    org = await create_org(session, display_name="O")
    await session.commit()
    agent = await create_agent(session, org.id, display_name="A")
    user = await create_end_user_account(session, org.id, display_name="U")
    await session.commit()
    return agent["id"], user.id


async def test_link_agent(session, setup):
    aid, uid = setup
    link = await link_agent(session, uid, aid)
    assert link is not None
    assert link.blueprint_agent_id == aid
    assert link.end_user_account_id == uid


async def test_idempotent_link(session, setup):
    aid, uid = setup
    link1 = await link_agent(session, uid, aid)
    link2 = await link_agent(session, uid, aid)
    assert link1.id == link2.id


async def test_unlink(session, setup):
    aid, uid = setup
    await link_agent(session, uid, aid)
    assert await unlink_agent(session, uid, aid) is True
    assert await get_link(session, uid, aid) is None


async def test_replicate(session, setup):
    aid, uid = setup
    await bf.mkdir(session, aid, "/skills")
    await bf.write_file(session, aid, "/skills/SKILL.md", "# Skill content")
    await bf.write_file(session, aid, "/IDENTITY.md", "I am bot")

    await link_agent(session, uid, aid)
    count = await replicate_blueprint_to_user(session, aid, uid)
    assert count == 3  # 1 dir + 2 files

    uf_skill = await uf.read_file(session, aid, uid, "/skills/SKILL.md")
    assert uf_skill is not None
    assert uf_skill["content"] == "# Skill content"

    uf_id = await uf.read_file(session, aid, uid, "/IDENTITY.md")
    assert uf_id["content"] == "I am bot"
