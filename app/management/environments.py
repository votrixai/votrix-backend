"""
Create (or reuse) an Anthropic cloud environment per agent.

The env_id is cached in agents/{agent_id}/.cache.json alongside the agent_id.
Environments are stateless cloud sandboxes — one per agent is enough;
multiple users' sessions share the same env config.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.client import get_client

AGENTS_DIR = Path(__file__).parents[2] / "agents"


def _cache_path(agent_id: str) -> Path:
    return AGENTS_DIR / agent_id / ".cache.json"


def _read_cache(agent_id: str) -> dict:
    p = _cache_path(agent_id)
    if p.exists():
        return json.loads(p.read_text())
    return {}


def _write_cache(agent_id: str, data: dict) -> None:
    p = _cache_path(agent_id)
    p.write_text(json.dumps(data, indent=2))


def get_or_create(agent_id: str) -> str:
    """Return cached env_id or create a new cloud environment."""
    cache = _read_cache(agent_id)
    if env_id := cache.get("env_id"):
        print(f"  [env:{agent_id}] cached {env_id}")
        return env_id

    client = get_client()
    env = client.beta.environments.create(
        name=f"votrix-{agent_id}",
        config={"type": "cloud"},
    )
    cache["env_id"] = env.id
    _write_cache(agent_id, cache)
    print(f"  [env:{agent_id}] created → {env.id}")
    return env.id
