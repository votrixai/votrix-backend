"""
Per-user agent provisioning.

create_user_agent(agent_id) → anthropic_agent_id

Steps:
  1. Read agents/{agent_id}/config.json
  2. Upload/version skills (idempotent)
  3. Build system prompt
  4. Call client.beta.agents.create() → return agent_id
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import structlog

from app.management import skills
from app.client import get_async_client
from app.tools import TOOL_DEFINITIONS
from app.tools.composio_meta import DEFINITIONS as COMPOSIO_META_TOOLS

logger = structlog.get_logger()

AGENTS_DIR = Path(__file__).parents[2] / "agents"


def get_integrations_by_blueprint_id(blueprint_id: uuid.UUID) -> list[str]:
    """
    Reverse-lookup: given an agent_blueprint primary key (== config.json agentId),
    return the list of integration slugs defined in that agent's config.json.
    Returns [] if no matching agent is found.
    """
    target = str(blueprint_id)
    for agent_dir in AGENTS_DIR.iterdir():
        if not agent_dir.is_dir():
            continue
        cfg = agent_dir / "config.json"
        if not cfg.exists():
            continue
        try:
            data = json.loads(cfg.read_text())
        except Exception:
            continue
        if data.get("agentId") == target:
            return [i["slug"] for i in data.get("integrations", [])]
    return []

_AGENT_TOOLSET = {
    "type": "agent_toolset_20260401",
    "default_config": {"permission_policy": {"type": "always_allow"}},
}

_MCP_TOOLSET_CONFIG = {
    "default_config": {
        "enabled": True,
        "permission_policy": {"type": "always_allow"},
    },
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


def _build_user_system(agent_id: str) -> str:
    config = _read_config(agent_id)
    integrations = [i["slug"] for i in config.get("integrations", [])]
    base = _build_system(agent_id)
    if not integrations:
        return base + "\n"
    slugs = " · ".join(integrations)
    integration_section = (
        f"## Integrations\n{slugs}\n"
        "These are the integrations available to this agent — connected or connectable."
    )
    return base + "\n\n---\n\n" + integration_section + "\n"


def _build_tools(custom_tools: list[dict]) -> list[dict]:
    return [_AGENT_TOOLSET] + custom_tools


def _skill_entries(skill_ids: dict[str, str]) -> list[dict]:
    return [{"type": "custom", "skill_id": sid, "version": "latest"} for sid in skill_ids.values()]


async def update_user_agent(agent_id: str, provider_agent_id: str) -> None:
    """
    Update an existing Anthropic managed agent in-place (same provider_agent_id).
    Retrieves current version for optimistic locking, then pushes new config.
    """
    config = _read_config(agent_id)

    skill_ids = await skills.get_or_upload_all(config.get("skills", []))
    custom_tools = [TOOL_DEFINITIONS[t] for t in config.get("tools", []) if t in TOOL_DEFINITIONS]
    if config.get("integrations"):
        custom_tools = COMPOSIO_META_TOOLS + custom_tools

    system = _build_user_system(agent_id)
    tools = _build_tools(custom_tools)

    client = get_async_client()
    current = await client.beta.agents.retrieve(provider_agent_id)
    await client.beta.agents.update(
        provider_agent_id,
        version=current.version,
        name=config["name"],
        model=config.get("model", "claude-sonnet-4-6"),
        system=system,
        tools=tools,
        skills=_skill_entries(skill_ids),
    )


async def create_user_agent(agent_id: str) -> str:
    """
    Provision an Anthropic managed agent from a template.
    Returns the Anthropic agent_id (caller must persist to DB).
    """
    config = _read_config(agent_id)

    skill_ids = await skills.get_or_upload_all(config.get("skills", []))
    custom_tools = [TOOL_DEFINITIONS[t] for t in config.get("tools", []) if t in TOOL_DEFINITIONS]
    if config.get("integrations"):
        custom_tools = COMPOSIO_META_TOOLS + custom_tools

    system = _build_user_system(agent_id)
    tools = _build_tools(custom_tools)

    client = get_async_client()
    agent = await client.beta.agents.create(
        name=config["name"],
        model=config.get("model", "claude-sonnet-4-6"),
        system=system,
        tools=tools,
        skills=_skill_entries(skill_ids),
    )

    return agent.id
