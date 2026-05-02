"""Cross-tenant access tests for the workspace-scoped routers.

These verify that an authenticated user who is a member of two workspaces
cannot read or mutate resources of one workspace by sending the other
workspace's id in the X-Workspace-Id header. All cross-tenant access must
return 404 (not 403, not 200) so we don't leak existence.

Resources are seeded directly via DB to avoid Anthropic API calls.
"""

import uuid

import pytest
from sqlalchemy import delete

from app.db.engine import session_scope
from app.db.models.agent_blueprints import AgentBlueprint
from app.db.models.agent_employees import AgentEmployee
from app.db.models.sessions import Session
from app.db.models.workspaces import Workspace, WorkspaceMember


@pytest.fixture
async def two_workspaces(db_user):
    """User is owner of two workspaces: A (from db_user) and B (created here)."""
    user_id = uuid.UUID(db_user["id"])
    ws_a_id = uuid.UUID(db_user["workspace_id"])
    async with session_scope() as db:
        ws_b = Workspace(display_name="Workspace B")
        db.add(ws_b)
        await db.commit()
        await db.refresh(ws_b)
        db.add(WorkspaceMember(workspace_id=ws_b.id, user_id=user_id, role="owner"))
        await db.commit()
        ws_b_id = ws_b.id
    yield {"a": ws_a_id, "b": ws_b_id}
    async with session_scope() as db:
        await db.execute(delete(WorkspaceMember).where(WorkspaceMember.workspace_id == ws_b_id))
        await db.execute(delete(Workspace).where(Workspace.id == ws_b_id))
        await db.commit()


@pytest.fixture
async def session_in_workspace_a(two_workspaces):
    """A session that lives in workspace A."""
    async with session_scope() as db:
        s = Session(provider_session_id=f"prov_{uuid.uuid4()}", workspace_id=two_workspaces["a"])
        db.add(s)
        await db.commit()
        await db.refresh(s)
        sid = s.id
    yield sid
    async with session_scope() as db:
        await db.execute(delete(Session).where(Session.id == sid))
        await db.commit()


@pytest.fixture
async def session_in_workspace_b(two_workspaces):
    """A session that lives in workspace B."""
    async with session_scope() as db:
        s = Session(provider_session_id=f"prov_{uuid.uuid4()}", workspace_id=two_workspaces["b"])
        db.add(s)
        await db.commit()
        await db.refresh(s)
        sid = s.id
    yield sid
    async with session_scope() as db:
        await db.execute(delete(Session).where(Session.id == sid))
        await db.commit()


@pytest.fixture
async def blueprint_and_employees(two_workspaces):
    """A blueprint, plus an employee record in workspace A only."""
    bp_id = uuid.uuid4()
    async with session_scope() as db:
        bp = AgentBlueprint(
            id=bp_id,
            provider_agent_id=f"prov_{uuid.uuid4()}",
            display_name="Test Blueprint",
        )
        db.add(bp)
        await db.commit()
        emp = AgentEmployee(workspace_id=two_workspaces["a"], agent_blueprint_id=bp_id)
        db.add(emp)
        await db.commit()
        await db.refresh(emp)
        emp_id = emp.id
    yield {"blueprint_id": bp_id, "employee_in_a": emp_id}
    async with session_scope() as db:
        await db.execute(delete(AgentEmployee).where(AgentEmployee.agent_blueprint_id == bp_id))
        await db.execute(delete(AgentBlueprint).where(AgentBlueprint.id == bp_id))
        await db.commit()


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


async def test_get_session_in_other_workspace_returns_404(
    client, two_workspaces, session_in_workspace_a
):
    """Session exists in A — querying with B's header must return 404, not 403."""
    r = await client.get(
        f"/sessions/{session_in_workspace_a}",
        headers={"X-Workspace-Id": str(two_workspaces["b"])},
    )
    assert r.status_code == 404


async def test_delete_session_in_other_workspace_returns_404(
    client, two_workspaces, session_in_workspace_a
):
    r = await client.delete(
        f"/sessions/{session_in_workspace_a}",
        headers={"X-Workspace-Id": str(two_workspaces["b"])},
    )
    assert r.status_code == 404


async def test_list_sessions_only_returns_active_workspace(
    client, two_workspaces, session_in_workspace_a, session_in_workspace_b
):
    r_a = await client.get(
        "/sessions", headers={"X-Workspace-Id": str(two_workspaces["a"])}
    )
    assert r_a.status_code == 200
    ids_a = {row["id"] for row in r_a.json()}
    assert str(session_in_workspace_a) in ids_a
    assert str(session_in_workspace_b) not in ids_a

    r_b = await client.get(
        "/sessions", headers={"X-Workspace-Id": str(two_workspaces["b"])}
    )
    assert r_b.status_code == 200
    ids_b = {row["id"] for row in r_b.json()}
    assert str(session_in_workspace_b) in ids_b
    assert str(session_in_workspace_a) not in ids_b


async def test_get_session_files_in_other_workspace_returns_404(
    client, two_workspaces, session_in_workspace_a
):
    r = await client.get(
        f"/sessions/{session_in_workspace_a}/files",
        headers={"X-Workspace-Id": str(two_workspaces["b"])},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


async def test_chat_session_in_other_workspace_returns_404(
    client, two_workspaces, session_in_workspace_a
):
    r = await client.post(
        "/chat",
        json={"session_id": str(session_in_workspace_a), "message": "hi"},
        headers={"X-Workspace-Id": str(two_workspaces["b"])},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------


async def test_list_employees_only_returns_active_workspace(
    client, two_workspaces, blueprint_and_employees
):
    r_a = await client.get(
        "/employees", headers={"X-Workspace-Id": str(two_workspaces["a"])}
    )
    assert r_a.status_code == 200
    assert len(r_a.json()) == 1
    assert r_a.json()[0]["id"] == str(blueprint_and_employees["employee_in_a"])

    r_b = await client.get(
        "/employees", headers={"X-Workspace-Id": str(two_workspaces["b"])}
    )
    assert r_b.status_code == 200
    assert r_b.json() == []


async def test_fire_employee_in_other_workspace_returns_404(
    client, two_workspaces, blueprint_and_employees
):
    r = await client.delete(
        f"/employees/{blueprint_and_employees['employee_in_a']}",
        headers={"X-Workspace-Id": str(two_workspaces["b"])},
    )
    assert r.status_code == 404
