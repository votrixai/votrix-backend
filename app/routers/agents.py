"""
Agent template routes — reads from agents/ directory on disk.

GET  /agents          list all agent templates
GET  /agents/{slug}   get config + provisioned status
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.models.agent import AgentCache, AgentConfig, AgentDetail

router = APIRouter(prefix="/agents", tags=["agents"])

AGENTS_DIR = Path(__file__).parents[2] / "agents"


def _load_agent(slug: str) -> AgentDetail:
    agent_dir = AGENTS_DIR / slug
    config_path = agent_dir / "config.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{slug}' not found")

    config = AgentConfig(**json.loads(config_path.read_text()))

    cache_path = agent_dir / ".cache.json"
    if cache_path.exists():
        cache = AgentCache(**json.loads(cache_path.read_text()))
        return AgentDetail(config=config, provisioned=True, cache=cache)

    return AgentDetail(config=config, provisioned=False)


@router.get("", response_model=list[AgentDetail])
async def list_agents():
    """List all agent templates defined in agents/."""
    slugs = sorted(d.name for d in AGENTS_DIR.iterdir() if d.is_dir())
    return [_load_agent(slug) for slug in slugs]


@router.get("/{slug}", response_model=AgentDetail)
async def get_agent(slug: str):
    """Get a single agent template with its provisioned status."""
    return _load_agent(slug)
