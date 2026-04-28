"""
Agent template routes — reads from agents/ directory on disk.

GET   /agents                        list all agent templates
GET   /agents/{agent_id}             get config
POST  /agents/{agent_id}/reprovision reprovision agent for current user

Note: reprovision is currently scoped to the authenticated user.
Future: will become a template-level update that propagates to all users.
"""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthedUser, require_user
from app.db.engine import get_session
from app.db.queries import user_agents as user_agents_q
from app.management.provisioning import create_user_agent
from app.models.agent import AgentConfig

router = APIRouter(prefix="/agents", tags=["agents"])

AGENTS_DIR = Path(__file__).parents[2] / "agents"


def _load_config(agent_id: str) -> AgentConfig:
    config_path = AGENTS_DIR / agent_id / "config.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    data = json.loads(config_path.read_text())
    return AgentConfig(slug=agent_id, **{k: v for k, v in data.items() if k not in ("agentId", "envId")})


EXCLUDED_AGENT_DIRS = {"TEMPLATE"}


@router.get("", response_model=list[AgentConfig])
async def list_agents():
    agent_ids = sorted(
        d.name for d in AGENTS_DIR.iterdir()
        if d.is_dir() and d.name not in EXCLUDED_AGENT_DIRS
    )
    return [_load_config(agent_id) for agent_id in agent_ids]


@router.get("/{agent_id}", response_model=AgentConfig)
async def get_agent(agent_id: str):
    return _load_config(agent_id)


@router.post("/{agent_id}/reprovision")
async def reprovision_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: AuthedUser = Depends(require_user),
):
    _load_config(agent_id)  # 404 if unknown agent
    new_agent_id = await create_user_agent(agent_id, str(current_user.id))
    existing = await user_agents_q.get(db, current_user.id, agent_id)
    if existing:
        existing.agent_id = new_agent_id
        await db.commit()
    else:
        await user_agents_q.create(db, current_user.id, agent_id, new_agent_id)
    return {"agent_id": new_agent_id}
