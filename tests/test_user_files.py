"""User file DAO tests."""

import uuid
import pytest
from app.db.queries.orgs import create_org
from app.db.queries.agents import create_agent
from app.db.queries.end_user_accounts import create_end_user_account
from app.db.queries import user_files as uf


@pytest.fixture
async def ids(session):
    """Return (agent_id, user1_id, user2_id)."""
    org = await create_org(session, display_name="O")
    await session.commit()
    agent = await create_agent(session, org.id, name="A")
    u1 = await create_end_user_account(session, org.id, display_name="U1")
    u2 = await create_end_user_account(session, org.id, display_name="U2")
    await session.commit()
    return agent["id"], u1.id, u2.id


async def test_write_and_read(session, ids):
    aid, uid, _ = ids
    await uf.write_file(session, aid, uid, "/doc.md", "content")
    f = await uf.read_file(session, aid, uid, "/doc.md")
    assert f is not None
    assert f["content"] == "content"


async def test_isolation(session, ids):
    aid, u1, u2 = ids
    await uf.write_file(session, aid, u1, "/shared.md", "user1")
    await uf.write_file(session, aid, u2, "/shared.md", "user2")
    f1 = await uf.read_file(session, aid, u1, "/shared.md")
    f2 = await uf.read_file(session, aid, u2, "/shared.md")
    assert f1["content"] == "user1"
    assert f2["content"] == "user2"


async def test_delete_files(session, ids):
    aid, uid, _ = ids
    await uf.write_file(session, aid, uid, "/a.md", "a")
    await uf.write_file(session, aid, uid, "/b.md", "b")
    count = await uf.delete_files(session, aid, uid, ["/a.md"])
    assert count == 1
    assert await uf.read_file(session, aid, uid, "/a.md") is None
    assert await uf.read_file(session, aid, uid, "/b.md") is not None
