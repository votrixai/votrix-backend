"""
Agent template routes — reads from agents/ directory on disk.

GET  /agents              list all agent templates
GET  /agents/{agent_id}   get config
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

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
