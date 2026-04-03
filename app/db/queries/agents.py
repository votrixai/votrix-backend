"""Agent queries — CRUD for blueprint_agents + blueprint_agent_integrations.

Returns are SQLAlchemy ORM instances from :mod:`app.db.models` (no separate DAO dict/TypedDict layer).
"""

from __future__ import annotations

import uuid
from typing import Any, List, Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.blueprint_agents import BlueprintAgent
from app.db.models.blueprint_agent_integrations import BlueprintAgentIntegration
from app.db.models.blueprint_files import BlueprintFile
from app.db.models.user_files import UserFile
from app.storage import BUCKET, delete_file as storage_delete


async def get_agent(session: AsyncSession, agent_id: uuid.UUID) -> Optional[BlueprintAgent]:
    stmt = select(BlueprintAgent).where(BlueprintAgent.id == agent_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_agent(session: AsyncSession, org_id: uuid.UUID, **kwargs) -> BlueprintAgent:
    integrations = kwargs.pop("integrations", None) or []
    obj = BlueprintAgent(org_id=org_id, **kwargs)
    session.add(obj)
    await session.commit()
    await session.refresh(obj)

    if integrations:
        for item in integrations:
            if isinstance(item, dict):
                d = item
            else:
                d = item.model_dump()
            slug = d.get("integration_slug")
            if not slug:
                continue
            session.add(BlueprintAgentIntegration(
                blueprint_agent_id=obj.id,
                integration_slug=slug,
                deferred=bool(d.get("deferred", False)),
                enabled_tool_slugs=list(d.get("enabled_tool_slugs") or []),
            ))
        await session.commit()

    return obj


async def update_agent(session: AsyncSession, agent_id: uuid.UUID, **kwargs) -> Optional[BlueprintAgent]:
    stmt = (
        update(BlueprintAgent)
        .where(BlueprintAgent.id == agent_id)
        .values(**kwargs)
    )
    result = await session.execute(stmt)
    await session.commit()
    if result.rowcount == 0:
        return None
    return await session.get(BlueprintAgent, agent_id)


async def list_agents(session: AsyncSession, org_id: uuid.UUID) -> List[BlueprintAgent]:
    stmt = (
        select(BlueprintAgent)
        .where(BlueprintAgent.org_id == org_id)
        .where(BlueprintAgent.deleted_at.is_(None))
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def soft_delete_agent(session: AsyncSession, agent_id: uuid.UUID) -> bool:
    stmt = (
        update(BlueprintAgent)
        .where(BlueprintAgent.id == agent_id, BlueprintAgent.deleted_at.is_(None))
        .values(deleted_at=func.now())
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


async def delete_agent(session: AsyncSession, agent_id: uuid.UUID) -> bool:
    """Delete an agent and clean up any Storage objects before DB cascade."""
    for model in (BlueprintFile, UserFile):
        storage_stmt = (
            select(model.storage_path)
            .where(model.blueprint_agent_id == agent_id, model.storage_path.is_not(None))
        )
        for sp in (await session.execute(storage_stmt)).scalars().all():
            await storage_delete(BUCKET, sp)

    stmt = delete(BlueprintAgent).where(BlueprintAgent.id == agent_id)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


# ---------------------------------------------------------------------------
# Per-integration operations (blueprint_agent_integrations table)
# ---------------------------------------------------------------------------


async def get_agent_integrations(
    session: AsyncSession,
    agent_id: uuid.UUID,
) -> List[BlueprintAgentIntegration]:
    stmt = select(BlueprintAgentIntegration).where(
        BlueprintAgentIntegration.blueprint_agent_id == agent_id
    )
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows)


async def replace_agent_integrations(
    session: AsyncSession,
    agent_id: uuid.UUID,
    integrations: List[Any],
) -> None:
    """Replace all integration rows for an agent (full set from request body)."""
    await session.execute(
        delete(BlueprintAgentIntegration).where(
            BlueprintAgentIntegration.blueprint_agent_id == agent_id
        )
    )
    for item in integrations:
        if isinstance(item, dict):
            d = item
        else:
            d = item.model_dump()
        slug = d.get("integration_slug")
        if not slug:
            continue
        session.add(BlueprintAgentIntegration(
            blueprint_agent_id=agent_id,
            integration_slug=slug,
            deferred=bool(d.get("deferred", False)),
            enabled_tool_slugs=list(d.get("enabled_tool_slugs") or []),
        ))
    await session.commit()


async def upsert_agent_integration(
    session: AsyncSession,
    agent_id: uuid.UUID,
    integration_slug: str,
    deferred: bool,
    enabled_tool_slugs: List[str],
) -> Optional[BlueprintAgentIntegration]:
    """Add or replace a single integration row for the agent. Returns None if agent not found."""
    agent = await session.get(BlueprintAgent, agent_id)
    if not agent:
        return None

    result = await session.execute(
        select(BlueprintAgentIntegration).where(
            BlueprintAgentIntegration.blueprint_agent_id == agent_id,
            BlueprintAgentIntegration.integration_slug == integration_slug,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.deferred = deferred
        row.enabled_tool_slugs = enabled_tool_slugs
    else:
        row = BlueprintAgentIntegration(
            blueprint_agent_id=agent_id,
            integration_slug=integration_slug,
            deferred=deferred,
            enabled_tool_slugs=enabled_tool_slugs,
        )
        session.add(row)

    await session.commit()
    await session.refresh(row)
    return row


async def delete_agent_integration(
    session: AsyncSession,
    agent_id: uuid.UUID,
    integration_slug: str,
) -> bool:
    """Remove a single integration from the agent. Returns False if not found."""
    stmt = delete(BlueprintAgentIntegration).where(
        BlueprintAgentIntegration.blueprint_agent_id == agent_id,
        BlueprintAgentIntegration.integration_slug == integration_slug,
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


async def get_org_integration_slugs(session: AsyncSession, org_id: uuid.UUID) -> List[str]:
    """Helper used by agent_integrations router to check org's activated slugs."""
    from app.db.queries import orgs as orgs_q
    return await orgs_q.get_org_integration_slugs(session, org_id)
