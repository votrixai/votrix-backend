"""DAO functions for end_user_agent_links + replication."""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.end_user_agent_links import EndUserAgentLink
from app.db.queries import blueprint_files, user_files


async def link_agent(
    session: AsyncSession,
    end_user_account_id: uuid.UUID,
    blueprint_agent_id: uuid.UUID,
) -> EndUserAgentLink:
    """Create a link between an end user account and a blueprint agent."""
    stmt = (
        insert(EndUserAgentLink)
        .values(
            end_user_account_id=end_user_account_id,
            blueprint_agent_id=blueprint_agent_id,
        )
        .on_conflict_do_nothing(index_elements=["end_user_account_id", "blueprint_agent_id"])
        .returning(EndUserAgentLink)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return await get_link(session, end_user_account_id, blueprint_agent_id)
    return row


async def get_link(
    session: AsyncSession,
    end_user_account_id: uuid.UUID,
    blueprint_agent_id: uuid.UUID,
) -> Optional[EndUserAgentLink]:
    stmt = select(EndUserAgentLink).where(
        EndUserAgentLink.end_user_account_id == end_user_account_id,
        EndUserAgentLink.blueprint_agent_id == blueprint_agent_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_links_for_account(
    session: AsyncSession, end_user_account_id: uuid.UUID
) -> List[EndUserAgentLink]:
    stmt = (
        select(EndUserAgentLink)
        .where(EndUserAgentLink.end_user_account_id == end_user_account_id)
        .order_by(EndUserAgentLink.created_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def unlink_agent(
    session: AsyncSession,
    end_user_account_id: uuid.UUID,
    blueprint_agent_id: uuid.UUID,
) -> bool:
    stmt = delete(EndUserAgentLink).where(
        EndUserAgentLink.end_user_account_id == end_user_account_id,
        EndUserAgentLink.blueprint_agent_id == blueprint_agent_id,
    )
    result = await session.execute(stmt)
    return result.rowcount > 0


async def replicate_blueprint_to_user(
    session: AsyncSession,
    blueprint_agent_id: uuid.UUID,
    user_account_id: uuid.UUID,
) -> int:
    """Copy all blueprint_files for an agent into user_files for the given user account.

    Returns the number of files replicated.
    """
    all_nodes = await blueprint_files.tree(session, blueprint_agent_id)
    count = 0
    for node in all_nodes:
        if node["type"] == "directory":
            await user_files.mkdir(session, blueprint_agent_id, user_account_id, node["path"])
            count += 1
        else:
            content_row = await blueprint_files.read_file(session, blueprint_agent_id, node["path"])
            if content_row:
                await user_files.write_file(
                    session, blueprint_agent_id, user_account_id,
                    node["path"], content_row.get("content", ""),
                    mime_type=content_row.get("mime_type", "text/markdown"),
                )
                count += 1
    return count
