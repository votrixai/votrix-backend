"""Blueprint file DAO tests."""

import uuid
import pytest
from app.db.queries.orgs import create_org
from app.db.queries.agents import create_agent
from app.db.queries import blueprint_files as bf
from app.models.files import classify_file


@pytest.fixture
async def agent_id(session):
    org = await create_org(session, display_name="O")
    await session.commit()
    row = await create_agent(session, org.id, name="A")
    return row["id"]


async def test_write_and_read(session, agent_id):
    await bf.write_file(session, agent_id, "/hello.md", "world")
    f = await bf.read_file(session, agent_id, "/hello.md")
    assert f is not None
    assert f["content"] == "world"


async def test_upsert(session, agent_id):
    await bf.write_file(session, agent_id, "/f.md", "v1")
    await bf.write_file(session, agent_id, "/f.md", "v2")
    f = await bf.read_file(session, agent_id, "/f.md")
    assert f["content"] == "v2"


async def test_ls(session, agent_id):
    await bf.write_file(session, agent_id, "/a.md", "a")
    await bf.write_file(session, agent_id, "/b.md", "b")
    entries = await bf.ls(session, agent_id, "/")
    assert len(entries) == 2


async def test_mkdir(session, agent_id):
    d = await bf.mkdir(session, agent_id, "/skills")
    assert d["type"] == "directory"
    assert await bf.exists(session, agent_id, "/skills")


async def test_rm(session, agent_id):
    await bf.write_file(session, agent_id, "/tmp.md", "x")
    await bf.rm(session, agent_id, "/tmp.md")
    assert not await bf.exists(session, agent_id, "/tmp.md")


async def test_rm_rf(session, agent_id):
    await bf.mkdir(session, agent_id, "/dir")
    await bf.write_file(session, agent_id, "/dir/a.md", "a")
    await bf.write_file(session, agent_id, "/dir/b.md", "b")
    count = await bf.rm_rf(session, agent_id, "/dir")
    assert count == 3


async def test_mv(session, agent_id):
    await bf.write_file(session, agent_id, "/old.md", "data")
    await bf.mv(session, agent_id, "/old.md", "/new.md")
    assert not await bf.exists(session, agent_id, "/old.md")
    f = await bf.read_file(session, agent_id, "/new.md")
    assert f is not None


async def test_edit(session, agent_id):
    await bf.write_file(session, agent_id, "/e.md", "hello world")
    result = await bf.edit_file(session, agent_id, "/e.md", "hello", "goodbye")
    assert result is not None
    f = await bf.read_file(session, agent_id, "/e.md")
    assert f["content"] == "goodbye world"


async def test_grep(session, agent_id):
    await bf.write_file(session, agent_id, "/a.md", "foo bar\nbaz")
    await bf.write_file(session, agent_id, "/b.md", "no match")
    results = await bf.grep(session, agent_id, "foo")
    assert len(results) == 1
    assert results[0]["path"] == "/a.md"


async def test_glob(session, agent_id):
    await bf.write_file(session, agent_id, "/skills/booking/SKILL.md", "s")
    await bf.write_file(session, agent_id, "/readme.txt", "r")
    results = await bf.glob(session, agent_id, "*.md")
    paths = [r["path"] for r in results]
    assert "/skills/booking/SKILL.md" in paths
    assert "/readme.txt" not in paths


async def test_tree(session, agent_id):
    await bf.mkdir(session, agent_id, "/d")
    await bf.write_file(session, agent_id, "/d/f.md", "x")
    entries = await bf.tree(session, agent_id)
    assert len(entries) == 2


async def test_exists(session, agent_id):
    assert not await bf.exists(session, agent_id, "/nope")
    await bf.write_file(session, agent_id, "/yes.md", "y")
    assert await bf.exists(session, agent_id, "/yes.md")


# ── classify_file pure-function tests ────────────────────────

def test_classify_skill():
    assert classify_file("/skills/booking/SKILL.md", "SKILL.md") == "skill"


def test_classify_skill_asset():
    assert classify_file("/skills/booking/config.json", "config.json") == "skill_asset"


def test_classify_prompt():
    assert classify_file("/IDENTITY.md", "IDENTITY.md") == "prompt"


def test_classify_generic():
    assert classify_file("/notes.txt", "notes.txt") == "file"
