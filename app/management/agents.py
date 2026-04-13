"""
Provision or sync an agent template into Anthropic's managed agent API.

provision(agent_id) — first-time setup:
  1. Upload skills listed in config.json
  2. Get or create cloud environment
  3. Assemble system prompt from IDENTITY.md + SOUL.md
  4. Call client.beta.agents.create()
  5. Write {agent_id, env_id, version} to agents/{agent_id}/.cache.json

sync(agent_id) — re-sync after config change:
  1. Re-upload skills (no-op if content unchanged)
  2. Call client.beta.agents.update() with current version (optimistic lock)
  3. Update .cache.json with new version
"""

from __future__ import annotations

import json
from pathlib import Path

from app.management import environments, skills
from app.client import get_client

AGENTS_DIR = Path(__file__).parents[2] / "agents"

_AGENT_TOOLSET = {
    "type": "agent_toolset_20260401",
    "default_config": {"permission_policy": {"type": "always_allow"}},
}


def _agent_dir(agent_id: str) -> Path:
    path = AGENTS_DIR / agent_id
    if not path.is_dir():
        raise FileNotFoundError(f"Agent directory not found: {path}")
    return path


def _read_config(agent_id: str) -> dict:
    config_path = _agent_dir(agent_id) / "config.json"
    return json.loads(config_path.read_text())


def _read_cache(agent_id: str) -> dict:
    p = _agent_dir(agent_id) / ".cache.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _write_cache(agent_id: str, data: dict) -> None:
    p = _agent_dir(agent_id) / ".cache.json"
    p.write_text(json.dumps(data, indent=2))


def _build_system(agent_id: str) -> str:
    """Concatenate IDENTITY.md + SOUL.md from the agent directory."""
    agent_dir = _agent_dir(agent_id)
    parts = []
    for name in ("IDENTITY.md", "SOUL.md"):
        p = agent_dir / name
        if p.exists():
            parts.append(p.read_text(encoding="utf-8").strip())
    return "\n\n---\n\n".join(parts)


def _build_tools(config: dict) -> list[dict]:
    # Phase 2: add mcp_toolset entries per integration here
    return [_AGENT_TOOLSET]


def _skill_entries(skill_ids: dict[str, str]) -> list[dict]:
    return [{"type": "custom", "skill_id": sid, "version": "latest"} for sid in skill_ids.values()]


def provision(agent_id: str) -> None:
    """Create the managed agent in Anthropic and cache its IDs."""
    config = _read_config(agent_id)

    print(f"[build:{agent_id}] provisioning...")
    skill_ids = skills.get_or_upload_all(config.get("skills", []))
    env_id = environments.get_or_create(agent_id)
    system = _build_system(agent_id)
    tools = _build_tools(config)

    client = get_client()
    agent = client.beta.agents.create(
        name=config["name"],
        model=config.get("model", "claude-sonnet-4-6"),
        system=system,
        tools=tools,
        skills=_skill_entries(skill_ids),
    )

    cache = {"agent_id": agent.id, "env_id": env_id, "version": agent.version}
    _write_cache(agent_id, cache)
    print(f"[build:{agent_id}] provisioned → agent_id={agent.id} version={agent.version}")


def sync(agent_id: str) -> None:
    """Update an already-provisioned agent after config/skill changes."""
    config = _read_config(agent_id)
    cache = _read_cache(agent_id)

    if not cache.get("agent_id"):
        print(f"[build:{agent_id}] no cache found — running provision instead")
        provision(agent_id)
        return

    print(f"[build:{agent_id}] syncing...")
    skill_ids = skills.get_or_upload_all(config.get("skills", []))
    system = _build_system(agent_id)
    tools = _build_tools(config)

    client = get_client()
    updated = client.beta.agents.update(
        cache["agent_id"],
        version=cache["version"],
        name=config["name"],
        model=config.get("model", "claude-sonnet-4-6"),
        system=system,
        tools=tools,
        skills=_skill_entries(skill_ids),
    )

    cache["version"] = updated.version
    _write_cache(agent_id, cache)
    print(f"[build:{agent_id}] synced → version={updated.version}")
