"""
Agent template routes — reads from agents/ directory on disk.

GET  /agents          list all agent templates
GET  /agents/{slug}   get config
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.models.agent import AgentConfig

router = APIRouter(prefix="/agents", tags=["agents"])

AGENTS_DIR = Path(__file__).parents[2] / "agents"


def _load_config(slug: str) -> AgentConfig:
    config_path = AGENTS_DIR / slug / "config.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{slug}' not found")
    return AgentConfig(**json.loads(config_path.read_text()))


@router.get("", response_model=list[AgentConfig])
async def list_agents():
    slugs = sorted(d.name for d in AGENTS_DIR.iterdir() if d.is_dir())
    return [_load_config(slug) for slug in slugs]


@router.get("/{slug}", response_model=AgentConfig)
async def get_agent(slug: str):
    return _load_config(slug)
