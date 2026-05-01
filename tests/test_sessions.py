import uuid
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from app.db.engine import session_scope
from app.db.models.sessions import Session, SessionEvent
from app.management.sessions import (
    fallback_session_title,
    title_from_message,
    usable_provider_title,
)


async def test_list_sessions_empty(client, db_user):
    r = await client.get("/sessions", headers={"X-Workspace-Id": db_user["workspace_id"]})
    assert r.status_code == 200
    assert r.json() == []


async def test_get_session_not_found(client, db_user):
    r = await client.get(
        f"/sessions/{uuid.uuid4()}",
        headers={"X-Workspace-Id": db_user["workspace_id"]},
    )
    assert r.status_code == 404


async def test_delete_session_not_found(client, db_user):
    r = await client.delete(
        f"/sessions/{uuid.uuid4()}",
        headers={"X-Workspace-Id": db_user["workspace_id"]},
    )
    assert r.status_code == 404


async def test_delete_session_deletes_events(client, db_user):
    async with session_scope() as db:
        session = Session(
            provider_session_id=f"prov_{uuid.uuid4()}",
            workspace_id=uuid.UUID(db_user["workspace_id"]),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        db.add_all(
            [
                SessionEvent(
                    session_id=session.id,
                    event_index=0,
                    event_type="user_message",
                    body="hello",
                ),
                SessionEvent(
                    session_id=session.id,
                    event_index=1,
                    event_type="ai_message",
                    body="hi",
                ),
            ]
        )
        await db.commit()
        session_id = session.id

    with patch(
        "app.routers.sessions.management_sessions.delete_provider_session",
        new=AsyncMock(),
    ):
        r = await client.delete(
            f"/sessions/{session_id}",
            headers={"X-Workspace-Id": db_user["workspace_id"]},
        )

    assert r.status_code == 204
    async with session_scope() as db:
        session_row = await db.scalar(select(Session).where(Session.id == session_id))
        event_rows = (
            await db.execute(
                select(SessionEvent).where(SessionEvent.session_id == session_id)
            )
        ).scalars().all()
    assert session_row is None
    assert event_rows == []


async def test_sessions_missing_workspace_header_uses_single_workspace(client, db_user):
    r = await client.get("/sessions")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_sessions_uses_first_message_when_stored_title_is_id_like(client, db_user):
    async with session_scope() as db:
        session = Session(
            provider_session_id=f"prov_{uuid.uuid4()}",
            workspace_id=uuid.UUID(db_user["workspace_id"]),
            title="a47be1cf",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        db.add(
            SessionEvent(
                session_id=session.id,
                event_index=0,
                event_type="user_message",
                body="Create a launch plan for the new campaign",
            )
        )
        await db.commit()

    r = await client.get("/sessions", headers={"X-Workspace-Id": db_user["workspace_id"]})

    assert r.status_code == 200
    assert r.json()[0]["title"] == "Create a launch plan for the new campaign"


async def test_list_sessions_uses_first_message_when_title_is_missing(client, db_user):
    async with session_scope() as db:
        session = Session(
            provider_session_id=f"prov_{uuid.uuid4()}",
            workspace_id=uuid.UUID(db_user["workspace_id"]),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        db.add(
            SessionEvent(
                session_id=session.id,
                event_index=0,
                event_type="user_message",
                body="Summarize the uploaded spreadsheet",
            )
        )
        await db.commit()

    r = await client.get("/sessions", headers={"X-Workspace-Id": db_user["workspace_id"]})

    assert r.status_code == 200
    assert r.json()[0]["title"] == "Summarize the uploaded spreadsheet"


async def test_list_sessions_returns_default_title_without_usable_title(client, db_user):
    async with session_scope() as db:
        session = Session(
            provider_session_id=f"prov_{uuid.uuid4()}",
            workspace_id=uuid.UUID(db_user["workspace_id"]),
            title="a47be1cf",
        )
        db.add(session)
        await db.commit()

    r = await client.get("/sessions", headers={"X-Workspace-Id": db_user["workspace_id"]})

    assert r.status_code == 200
    assert r.json()[0]["title"] == "New Conversation"


def test_usable_provider_title_filters_generated_ids():
    provider_session_id = "sess_0123456789abcdef"

    assert usable_provider_title("Customer Follow-up", provider_session_id) == "Customer Follow-up"
    assert usable_provider_title("  Customer Follow-up  ", provider_session_id) == "Customer Follow-up"
    assert usable_provider_title(provider_session_id, provider_session_id) is None
    assert usable_provider_title("a47be1cf", provider_session_id) is None
    assert usable_provider_title("5b9234e1", provider_session_id) is None
    assert usable_provider_title("sesn_0123456789abcdef", provider_session_id) is None
    assert usable_provider_title(str(uuid.uuid4()), provider_session_id) is None
    assert usable_provider_title("", provider_session_id) is None


def test_fallback_session_title_defaults_when_message_is_blank():
    assert fallback_session_title(" Summarize this file ") == "Summarize this file"
    assert fallback_session_title("   ") == "New Conversation"
    assert fallback_session_title(None) == "New Conversation"


def test_title_from_message_does_not_default():
    assert title_from_message(" Summarize this file ") == "Summarize this file"
    assert title_from_message("   ") is None
    assert title_from_message(None) is None
