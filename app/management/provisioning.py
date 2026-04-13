"""
Per-user agent provisioning.

create_user_agent(agent_id, user_id, display_name) → agent_id

What it does:
  1. Read agents/{agent_id}/config.json  (integrations, skills, model)
  2. Read agents/{agent_id}/.cache.json  (env_id from template build)
  3. Upload skills if not already cached (idempotent)
  4. Build per-user system prompt  (template + user context block)
  5. Build per-user MCP servers    (?user_id= embedded in URL)
  6. Call client.beta.agents.create() → return agent_id

Does NOT touch the database — caller (router) handles persistence.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.management import environments, skills
from app.management.agents import (
    _agent_dir,
    _build_system,
    _read_cache,
    _read_config,
    _skill_entries,
)
from app.client import get_client
from app.integrations import composio

_AGENT_TOOLSET = {
    "type": "agent_toolset_20260401",
    "default_config": {"permission_policy": {"type": "always_allow"}},
}

_MCP_TOOLSET = {
    "default_config": {"permission_policy": {"type": "always_allow"}},
}


def _build_user_system(agent_id: str, display_name: str) -> str:
    """Template system prompt + injected user context block."""
    base = _build_system(agent_id)
    user_block = f"\n\n---\n\n## Current User\nName: {display_name}\n"
    return base + user_block


def _build_mcp_servers(integrations: list[str], user_id: str) -> list[dict]:
    """Single Composio MCP server that exposes all integrations for this user."""
    if not integrations:
        return []
    return [
        {
            "type": "url",
            "name": "composio",
            "url": composio.mcp_url(user_id),
        }
    ]


def _build_tools(mcp_server_names: list[str]) -> list[dict]:
    return [_AGENT_TOOLSET] + [
        {"type": "mcp_toolset", "mcp_server_name": name, **_MCP_TOOLSET}
        for name in mcp_server_names
    ]


def create_user_agent(agent_id: str, user_id: str, display_name: str) -> str:
    """
    Provision a per-user Anthropic managed agent.
    Returns the new agent_id (caller must persist to DB).
    """
    config = _read_config(agent_id)
    cache = _read_cache(agent_id)

    if not cache.get("env_id"):
        raise RuntimeError(
            f"Agent '{agent_id}' template not provisioned — run: "
            f"python -m app.management.run --agent {agent_id}"
        )

    env_id = cache["env_id"]
    skill_ids = skills.get_or_upload_all(config.get("skills", []))
    integrations = config.get("integrations", [])

    system = _build_user_system(agent_id, display_name)
    mcp_servers = _build_mcp_servers(integrations, user_id)
    mcp_names = [s["name"] for s in mcp_servers]
    tools = _build_tools(mcp_names)

    client = get_client()
    agent = client.beta.agents.create(
        name=f"{config['name']} — {display_name}",
        model=config.get("model", "claude-sonnet-4-6"),
        system=system,
        tools=tools,
        skills=_skill_entries(skill_ids),
        mcp_servers=mcp_servers if mcp_servers else [],
    )

    return agent.id
