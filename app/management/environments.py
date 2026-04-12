"""
Create (or reuse) an Anthropic cloud environment per agent.

The env_id is cached in agents/{slug}/.cache.json alongside the agent_id.
Environments are stateless cloud sandboxes — one per agent slug is enough;
multiple users' sessions share the same env config.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.client import get_client

AGENTS_DIR = Path(__file__).parents[2] / "agents"


def _cache_path(slug: str) -> Path:
    return AGENTS_DIR / slug / ".cache.json"


def _read_cache(slug: str) -> dict:
    p = _cache_path(slug)
    if p.exists():
        return json.loads(p.read_text())
    return {}


def _write_cache(slug: str, data: dict) -> None:
    p = _cache_path(slug)
    p.write_text(json.dumps(data, indent=2))


def get_or_create(slug: str) -> str:
    """Return cached env_id or create a new cloud environment."""
    cache = _read_cache(slug)
    if env_id := cache.get("env_id"):
        print(f"  [env:{slug}] cached {env_id}")
        return env_id

    client = get_client()
    env = client.beta.environments.create(
        name=f"votrix-{slug}",
        config={"type": "cloud"},
    )
    cache["env_id"] = env.id
    _write_cache(slug, cache)
    print(f"  [env:{slug}] created → {env.id}")
    return env.id
