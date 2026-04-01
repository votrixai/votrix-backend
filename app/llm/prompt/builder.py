from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


async def build_system_prompt(_agent_id: UUID, _session: AsyncSession) -> str:
    return "You are a helpful assistant."
