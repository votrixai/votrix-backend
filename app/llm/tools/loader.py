from typing import Dict, List, TypedDict
from uuid import UUID

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.queries import agents as agents_q
from app.llm.tools.assembler import ToolAssembler
from app.models.agent import AgentIntegration


class ToolBundle(TypedDict):
    base_tools: List[BaseTool]           # bound to LLM every turn
    deferred_tools_map: Dict[str, BaseTool]  # activated on-demand via tool_search


async def load_tools(
    agent_id: UUID,
    end_user_id: UUID,
    session: AsyncSession,
) -> ToolBundle:
    """Load tools for a given (agent, user) pair via ToolAssembler."""
    agent = await agents_q.get_agent(session, agent_id)
    if not agent:
        return ToolBundle(base_tools=[], deferred_tools_map={})

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
    assembler = ToolAssembler(api_key=settings.composio_api_key)
    await assembler.initialize(
        agent_integrations=payload,
        user_id=str(end_user_id),
        agent_id=agent_id,
        session=session,
    )
    return ToolBundle(
        base_tools=assembler.get_active_tools(),
        deferred_tools_map=assembler.get_deferred_tools_map(),
    )
