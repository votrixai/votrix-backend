"""Org DAO tests."""

import uuid
import pytest
from app.db.queries.orgs import create_org, get_org, list_orgs, update_org, delete_org


async def test_create_and_get(session):
    org = await create_org(session, display_name="Acme", timezone="US/Eastern")
    await session.commit()
    fetched = await get_org(session, org.id)
    assert fetched is not None
    assert fetched.display_name == "Acme"
    assert fetched.timezone == "US/Eastern"


async def test_get_not_found(session):
    assert await get_org(session, uuid.uuid4()) is None


async def test_list(session):
    await create_org(session, display_name="A")
    await create_org(session, display_name="B")
    await session.commit()
    orgs = await list_orgs(session)
    assert len(orgs) == 2


async def test_update(session):
    org = await create_org(session, display_name="Old")
    await session.commit()
    updated = await update_org(session, org.id, display_name="New")
    assert updated.display_name == "New"


async def test_delete(session):
    org = await create_org(session, display_name="Del")
    await session.commit()
    assert await delete_org(session, org.id) is True
    assert await get_org(session, org.id) is None
