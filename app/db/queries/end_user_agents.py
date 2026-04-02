"""DAO functions for end_user_agents + replication.

Return shapes (DAO; HTTP layer uses ``app.models.end_user_account`` link types):

    ``link_agent``, ``get_link``, ``list_links_for_account``
        → :class:`app.db.models.end_user_agents.EndUserAgent`
        OR ``None`` for ``get_link`` only.

    ``unlink_agent``
        → ``bool`` — whether a link row was removed.

    ``replicate_blueprint_to_user``
        → ``int`` — number of filesystem nodes (dirs + files) written
        to ``user_files`` for that user/agent pair.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.blueprint_files import NodeType
from app.db.models.end_user_agents import EndUserAgent
from app.db.queries import blueprint_files, user_files
from app.storage import BUCKET, download_file


async def link_agent(
    session: AsyncSession,
    end_user_account_id: uuid.UUID,
    blueprint_agent_id: uuid.UUID,
) -> EndUserAgent:
    """Create a link between an end user account and a blueprint agent."""
    stmt = (
        insert(EndUserAgent)
        .values(
            end_user_account_id=end_user_account_id,
            blueprint_agent_id=blueprint_agent_id,
        )
        .on_conflict_do_nothing(index_elements=["end_user_account_id", "blueprint_agent_id"])
        .returning(EndUserAgent)
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
) -> Optional[EndUserAgent]:
    stmt = select(EndUserAgent).where(
        EndUserAgent.end_user_account_id == end_user_account_id,
        EndUserAgent.blueprint_agent_id == blueprint_agent_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_links_for_account(
    session: AsyncSession, end_user_account_id: uuid.UUID
) -> List[EndUserAgent]:
    stmt = (
        select(EndUserAgent)
        .where(EndUserAgent.end_user_account_id == end_user_account_id)
        .order_by(EndUserAgent.created_at)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def unlink_agent(
    session: AsyncSession,
    end_user_account_id: uuid.UUID,
    blueprint_agent_id: uuid.UUID,
) -> bool:
    stmt = delete(EndUserAgent).where(
        EndUserAgent.end_user_account_id == end_user_account_id,
        EndUserAgent.blueprint_agent_id == blueprint_agent_id,
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
        if node.type == NodeType.directory:
            await user_files.mkdir(session, blueprint_agent_id, user_account_id, node.path)
            count += 1
        else:
            content_row = await blueprint_files.read_file(session, blueprint_agent_id, node.path)
            if content_row:
                if content_row.storage_path:
                    data = await download_file(BUCKET, content_row.storage_path)
                    await user_files.write_file(
                        session, blueprint_agent_id, user_account_id,
                        node.path,
                        mime_type=content_row.mime_type or "application/octet-stream",
                        binary_data=data,
                    )
                else:
                    await user_files.write_file(
                        session, blueprint_agent_id, user_account_id,
                        node.path, content_row.content or "",
                        mime_type=content_row.mime_type or "text/markdown",
                    )
                count += 1
    return count
