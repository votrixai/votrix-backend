"""
Per-user agent provisioning.

create_user_agent(agent_id, user_id, display_name, force) → anthropic_agent_id

Steps:
  1. Read agents/{agent_id}/config.json
  2. Upload/version skills (idempotent)
  3. Get or create Composio MCP server named "votrix-{agent_id}"
     (force=True deletes and recreates)
  4. Build system prompt
  5. Call client.beta.agents.create() → return agent_id
"""

from __future__ import annotations

import json
from pathlib import Path

from app.management import skills
from app.client import get_client
from app.integrations import composio
from app.tools import TOOL_DEFINITIONS

AGENTS_DIR = Path(__file__).parents[2] / "agents"

_AGENT_TOOLSET = {
    "type": "agent_toolset_20260401",
    "default_config": {"permission_policy": {"type": "always_allow"}},
}

_MCP_TOOLSET_CONFIG = {
    "default_config": {"permission_policy": {"type": "always_allow"}},
}


def _agent_dir(agent_id: str) -> Path:
    path = AGENTS_DIR / agent_id
    if not path.is_dir():
        raise FileNotFoundError(f"Agent directory not found: {path}")
    return path


def _read_config(agent_id: str) -> dict:
    return json.loads((_agent_dir(agent_id) / "config.json").read_text())


def _build_system(agent_id: str) -> str:
    p = _agent_dir(agent_id) / "PROMPT.md"
    if not p.exists():
        raise FileNotFoundError(f"PROMPT.md not found for agent '{agent_id}'")
    return p.read_text(encoding="utf-8").strip()


def _build_user_system(agent_id: str, display_name: str) -> str:
    base = _build_system(agent_id)
    return base + f"\n\n---\n\n## Current User\nName: {display_name}\n"


def _build_tools(mcp_server_names: list[str], custom_tools: list[dict]) -> list[dict]:
    return (
        [_AGENT_TOOLSET]
        + [{"type": "mcp_toolset", "mcp_server_name": name, **_MCP_TOOLSET_CONFIG} for name in mcp_server_names]
        + custom_tools
    )


def _skill_entries(skill_ids: dict[str, str]) -> list[dict]:
    return [{"type": "custom", "skill_id": sid, "version": "latest"} for sid in skill_ids.values()]


def create_user_agent(
    agent_id: str,
    user_id: str,
    display_name: str,
    composio_user_id: str | None = None,
    force: bool = False,
) -> str:
    """
    Provision a per-user Anthropic managed agent.
    Returns the Anthropic agent_id (caller must persist to DB).
    """
    config = _read_config(agent_id)
    composio_id = composio_user_id or user_id

    skill_ids = skills.get_or_upload_all(config.get("skills", []), force=force)
    custom_tools = [TOOL_DEFINITIONS[t] for t in config.get("tools", []) if t in TOOL_DEFINITIONS]

    # Get or create Composio MCP server for this agent's integrations
    integrations = config.get("integrations", [])
    mcp_server_id = composio.get_or_create_mcp_server(agent_id, integrations, force=force)

    mcp_servers = []
    if mcp_server_id:
        mcp_servers = [{
            "type": "url",
            "name": "composio",
            "url": composio.mcp_url(mcp_server_id, composio_id),
        }]

    system = _build_user_system(agent_id, display_name)
    tools = _build_tools([s["name"] for s in mcp_servers], custom_tools)

    client = get_client()
    agent = client.beta.agents.create(
        name=f"{config['name']} — {display_name}",
        model=config.get("model", "claude-sonnet-4-6"),
        system=system,
        tools=tools,
        skills=_skill_entries(skill_ids),
        mcp_servers=mcp_servers,
    )

    return agent.id
