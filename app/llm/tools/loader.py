from typing import List
from uuid import UUID

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.queries import agents as agents_q
from app.integrations.context import ToolContext
from app.models.agent import AgentIntegration


async def load_tools(
    agent_id: UUID,
    end_user_id: UUID,
    session: AsyncSession,
) -> List[BaseTool]:
    """Load active tools for a given (agent, user) pair via ToolContext."""
    agent = await agents_q.get_agent(session, agent_id)
    if not agent:
        return []

    settings = get_settings()
    integration_rows = await agents_q.get_agent_integrations(session, agent_id)
    payload = [
        AgentIntegration(
            integration_slug=i.integration_slug,
            deferred=i.deferred,
            enabled_tool_slugs=list(i.enabled_tool_slugs or []),
        )
        for i in integration_rows
    ]
    ctx = ToolContext(api_key=settings.composio_api_key)
    await ctx.initialize(
        agent_integrations=payload,
        user_id=str(end_user_id),
    )
    return ctx.get_active_tools()
