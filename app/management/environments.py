"""
Get or create a single shared Anthropic cloud environment.

One environment is enough for all agents and all users — environments are
stateless cloud sandboxes and the env_id is just a config parameter passed
to sessions.create(). The ID is cached in .env_cache.json at the project root.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.client import get_client

_CACHE_PATH = Path(__file__).parents[2] / ".env_cache.json"


def get_or_create() -> str:
    """Return cached env_id or create a new cloud environment."""
    if _CACHE_PATH.exists():
        data = json.loads(_CACHE_PATH.read_text())
        if env_id := data.get("env_id"):
            return env_id

    client = get_client()
    env = client.beta.environments.create(
        name="votrix",
        config={"type": "cloud"},
    )
    _CACHE_PATH.write_text(json.dumps({"env_id": env.id}, indent=2))
    print(f"[env] created → {env.id}")
    return env.id
