"""Tests for the require_workspace auth dependency.

The dependency is exercised via a single test-only echo endpoint mounted on the
production app at import time. The path is namespaced so it cannot collide with
real routes; it exists only because Phase 1 adds the dependency before any router
adopts it, so there is no production endpoint to call yet.
"""

import uuid

import pytest
from fastapi import Depends
from sqlalchemy import delete

from app.auth import WorkspaceContext, require_workspace
from app.db.engine import session_scope
from app.db.models.workspaces import Workspace, WorkspaceMember
from app.main import app


@app.get("/__test_workspace_echo__")
async def _echo_workspace(ctx: WorkspaceContext = Depends(require_workspace)):
    return {
        "user_id": str(ctx.user_id),
        "workspace_id": str(ctx.workspace_id),
        "role": ctx.role,
    }


_PATH = "/__test_workspace_echo__"


@pytest.fixture
async def foreign_workspace():
    """A workspace the test user is NOT a member of."""
    async with session_scope() as db:
        ws = Workspace(display_name="Foreign workspace")
        db.add(ws)
        await db.commit()
        await db.refresh(ws)
        ws_id = ws.id
    yield ws_id
    async with session_scope() as db:
        await db.execute(delete(Workspace).where(Workspace.id == ws_id))
        await db.commit()


@pytest.fixture
async def second_workspace(db_user):
    """A second workspace the test user IS a member of."""
    user_id = uuid.UUID(db_user["id"])
    async with session_scope() as db:
        ws = Workspace(display_name="Second workspace")
        db.add(ws)
        await db.commit()
        await db.refresh(ws)
        db.add(WorkspaceMember(workspace_id=ws.id, user_id=user_id, role="owner"))
        await db.commit()
        ws_id = ws.id
    yield ws_id
    async with session_scope() as db:
        await db.execute(delete(WorkspaceMember).where(WorkspaceMember.workspace_id == ws_id))
        await db.execute(delete(Workspace).where(Workspace.id == ws_id))
        await db.commit()


async def test_missing_header_with_one_workspace_uses_it(client, db_user):
    r = await client.get(_PATH)
    assert r.status_code == 200
    assert r.json() == {
        "user_id": db_user["id"],
        "workspace_id": db_user["workspace_id"],
        "role": "owner",
    }


async def test_malformed_uuid_returns_400(client, db_user):
    r = await client.get(_PATH, headers={"X-Workspace-Id": "not-a-uuid"})
    assert r.status_code == 400
    assert "valid UUID" in r.json()["detail"]


async def test_empty_header_returns_400(client, db_user):
    r = await client.get(_PATH, headers={"X-Workspace-Id": ""})
    assert r.status_code == 400


async def test_nonexistent_workspace_returns_403(client, db_user):
    # A random UUID the user cannot possibly be a member of.
    r = await client.get(_PATH, headers={"X-Workspace-Id": str(uuid.uuid4())})
    assert r.status_code == 403


async def test_non_member_workspace_returns_403(client, db_user, foreign_workspace):
    r = await client.get(_PATH, headers={"X-Workspace-Id": str(foreign_workspace)})
    assert r.status_code == 403
    assert "Not a member" in r.json()["detail"]


async def test_member_returns_200_with_workspace_id(client, db_user):
    r = await client.get(_PATH, headers={"X-Workspace-Id": db_user["workspace_id"]})
    assert r.status_code == 200
    assert r.json()["user_id"] == db_user["id"]
    assert r.json()["workspace_id"] == db_user["workspace_id"]
    assert r.json()["role"] == "owner"


async def test_user_with_two_workspaces_can_target_either(client, db_user, second_workspace):
    r1 = await client.get(_PATH, headers={"X-Workspace-Id": db_user["workspace_id"]})
    assert r1.status_code == 200
    assert r1.json()["workspace_id"] == db_user["workspace_id"]

    r2 = await client.get(_PATH, headers={"X-Workspace-Id": str(second_workspace)})
    assert r2.status_code == 200
    assert r2.json()["workspace_id"] == str(second_workspace)


async def test_missing_header_with_multiple_workspaces_returns_400(client, db_user, second_workspace):
    r = await client.get(_PATH)
    assert r.status_code == 400
    assert "X-Workspace-Id" in r.json()["detail"]
