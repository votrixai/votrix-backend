"""
Provision or sync an agent template into Anthropic's managed agent API.

provision(slug) — first-time setup:
  1. Upload skills listed in config.json
  2. Get or create cloud environment
  3. Assemble system prompt from IDENTITY.md + SOUL.md
  4. Call client.beta.agents.create()
  5. Write {agent_id, env_id, version} to agents/{slug}/.cache.json

sync(slug) — re-sync after config change:
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


def _agent_dir(slug: str) -> Path:
    path = AGENTS_DIR / slug
    if not path.is_dir():
        raise FileNotFoundError(f"Agent directory not found: {path}")
    return path


def _read_config(slug: str) -> dict:
    config_path = _agent_dir(slug) / "config.json"
    return json.loads(config_path.read_text())


def _read_cache(slug: str) -> dict:
    p = _agent_dir(slug) / ".cache.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _write_cache(slug: str, data: dict) -> None:
    p = _agent_dir(slug) / ".cache.json"
    p.write_text(json.dumps(data, indent=2))


def _build_system(slug: str) -> str:
    """Concatenate IDENTITY.md + SOUL.md from the agent directory."""
    agent_dir = _agent_dir(slug)
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


def provision(slug: str) -> None:
    """Create the managed agent in Anthropic and cache its IDs."""
    config = _read_config(slug)

    print(f"[build:{slug}] provisioning...")
    skill_ids = skills.get_or_upload_all(config.get("skills", []))
    env_id = environments.get_or_create(slug)
    system = _build_system(slug)
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
    _write_cache(slug, cache)
    print(f"[build:{slug}] provisioned → agent_id={agent.id} version={agent.version}")


def sync(slug: str) -> None:
    """Update an already-provisioned agent after config/skill changes."""
    config = _read_config(slug)
    cache = _read_cache(slug)

    if not cache.get("agent_id"):
        print(f"[build:{slug}] no cache found — running provision instead")
        provision(slug)
        return

    print(f"[build:{slug}] syncing...")
    skill_ids = skills.get_or_upload_all(config.get("skills", []))
    system = _build_system(slug)
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
    _write_cache(slug, cache)
    print(f"[build:{slug}] synced → version={updated.version}")
