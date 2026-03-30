"""Guidelines queries — global singleton prompt guidelines."""

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.guidelines import Guideline


async def get(session: AsyncSession, guideline_id: str) -> Optional[str]:
    stmt = select(Guideline.content).where(Guideline.guideline_id == guideline_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_all(session: AsyncSession) -> Dict[str, str]:
    stmt = select(Guideline.guideline_id, Guideline.content)
    result = await session.execute(stmt)
    return {row["guideline_id"]: row["content"] for row in result.mappings()}


async def upsert(session: AsyncSession, guideline_id: str, content: str) -> None:
    stmt = (
        pg_insert(Guideline)
        .values(guideline_id=guideline_id, content=content)
        .on_conflict_do_update(
            index_elements=["guideline_id"],
            set_={"content": content},
        )
    )
    await session.execute(stmt)
    await session.commit()


async def list_all(session: AsyncSession) -> List[Dict[str, Any]]:
    stmt = select(Guideline.guideline_id, Guideline.updated_at)
    result = await session.execute(stmt)
    return [dict(r) for r in result.mappings()]
