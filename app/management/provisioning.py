"""
Per-user agent provisioning.

create_user_agent(agent_id, user_id, display_name) → agent_id

Steps:
  1. Read agents/{agent_id}/config.json  (integrations, skills, model)
  2. Get or create shared environment (lazy, cached in .env_cache.json)
  3. Upload/cache skills              (lazy, idempotent per skill)
  4. Build per-user system prompt    (template + user context block)
  5. Build per-toolkit MCP servers   (one scoped Composio URL per integration slug)
  6. Call client.beta.agents.create() → return agent_id

Does NOT touch the database — caller (router) handles persistence.
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
    """Read PROMPT.md from the agent directory."""
    p = _agent_dir(agent_id) / "PROMPT.md"
    if not p.exists():
        raise FileNotFoundError(f"PROMPT.md not found for agent '{agent_id}'")
    return p.read_text(encoding="utf-8").strip()


def _build_user_system(agent_id: str, display_name: str) -> str:
    base = _build_system(agent_id)
    return base + f"\n\n---\n\n## Current User\nName: {display_name}\n"


def _build_mcp_servers(integrations: list[dict], user_id: str) -> list[dict]:
    """One scoped Composio MCP server per integration, with optional action filtering."""
    return [
        {
            "type": "url",
            "name": i["slug"],
            "url": composio.mcp_url_for_toolkit(user_id, i["slug"], i.get("tools")),
        }
        for i in integrations
    ]


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
) -> str:
    """
    Provision a per-user Anthropic managed agent.
    Returns the new agent_id (caller must persist to DB).

    composio_user_id: Composio entity ID used in MCP URLs for OAuth routing.
                      Defaults to user_id when not provided.
    """
    config = _read_config(agent_id)

    skill_ids = skills.get_or_upload_all(config.get("skills", []))
    integrations = config.get("integrations", [])
    composio_id = composio_user_id or user_id

    custom_tools = [TOOL_DEFINITIONS[t] for t in config.get("tools", []) if t in TOOL_DEFINITIONS]

    system = _build_user_system(agent_id, display_name)
    mcp_servers = _build_mcp_servers(integrations, composio_id)
    tools = _build_tools([s["name"] for s in mcp_servers], custom_tools)

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
