"""
Per-user agent provisioning.

create_user_agent(agent_id) → anthropic_agent_id

Steps:
  1. Read agents/{agent_id}/config.json
  2. Upload/version skills (idempotent)
  3. Auto-connect API_KEY integrations (e.g. Apollo)
  4. Get or create Composio MCP server named "votrix-{agent_id}"
     (force=True deletes and recreates)
  5. Build system prompt
  6. Call client.beta.agents.create() → return agent_id
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import structlog

from app.management import skills
from app.client import get_async_client
from app.config import get_settings
from app.integrations.composio import create_mcp_server, get_auth_config, mcp_url
from app.tools import TOOL_DEFINITIONS

logger = structlog.get_logger()

AGENTS_DIR = Path(__file__).parents[2] / "agents"

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


def _build_tools(mcp_server_names: list[str], custom_tools: list[dict]) -> list[dict]:
    tools: list[dict] = [_AGENT_TOOLSET]
    tools += [{"type": "mcp_toolset", "mcp_server_name": name, **_MCP_TOOLSET_CONFIG} for name in mcp_server_names]
    tools += custom_tools
    return tools


async def _auto_connect_api_key_integrations(integrations: list[dict], entity_id: str) -> None:
    """For API_KEY integrations, auto-create connected_account at provision time.
    Key is read from env as {SLUG_UPPER}_API_KEY (e.g. APOLLO_API_KEY).
    Idempotent: checks by auth_config_id + entity_id via SDK.
    """
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://backend.composio.dev/api/v3/connected_accounts",
            headers={"x-api-key": settings.composio_api_key},
            params={"user_ids": entity_id, "statuses": "ACTIVE"},
            timeout=15,
        )
    r.raise_for_status()
    active_slugs = {
        (item.get("toolkit") or {}).get("slug", "")
        for item in r.json().get("items", [])
        if item.get("user_id") == entity_id and item.get("status") == "ACTIVE"
    }

    for i in integrations:
        slug = i["slug"]
        ac = await get_auth_config(slug)
        if ac is None:
            raise RuntimeError(
                f"No auth_config found in Composio for integration '{slug}'. "
                "Create one in the Composio dashboard first."
            )

        auth_scheme = (ac.get("auth_scheme") or "").upper()
        if auth_scheme != "API_KEY":
            continue

        if slug in active_slugs:
            logger.info("provisioning: '%s' already connected for %s", slug, entity_id)
            continue

        env_key = f"{slug.upper()}_API_KEY"
        api_key_val = os.environ.get(env_key)
        if not api_key_val:
            raise RuntimeError(
                f"Integration '{slug}' requires API_KEY but env var '{env_key}' is not set."
            )

        logger.info("provisioning: auto-connecting API_KEY integration '%s' for %s", slug, entity_id)
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://backend.composio.dev/api/v3/connected_accounts",
                headers={"x-api-key": settings.composio_api_key, "Content-Type": "application/json"},
                json={
                    "auth_config": {"id": ac["id"]},
                    "connection": {"user_id": entity_id, "data": {"api_key": api_key_val}},
                },
                timeout=15,
            )
        if not r.is_success:
            raise RuntimeError(f"Failed to connect '{slug}': {r.status_code} {r.text}")
        logger.info("provisioning: '%s' connected successfully", slug)


def _skill_entries(skill_ids: dict[str, str]) -> list[dict]:
    return [{"type": "custom", "skill_id": sid, "version": "latest"} for sid in skill_ids.values()]


async def create_user_agent(
    agent_id: str,
    composio_entity_id: str | None = None,
) -> str:
    """
    Provision an Anthropic managed agent from a template.
    Returns the Anthropic agent_id (caller must persist to DB).
    """
    config = _read_config(agent_id)
    composio_id = composio_entity_id or agent_id

    skill_ids = await skills.get_or_upload_all(config.get("skills", []))
    custom_tools = [TOOL_DEFINITIONS[t] for t in config.get("tools", []) if t in TOOL_DEFINITIONS]

    integrations = config.get("integrations", [])
    direct_mcp_servers = config.get("mcp_servers", [])

    mcp_servers: list[dict] = []

    # Direct MCP servers (no Composio)
    for srv in direct_mcp_servers:
        mcp_servers.append({"type": "url", "name": srv["name"], "url": srv["url"]})

    # Composio MCP server (only when integrations are configured)
    if integrations:
        await _auto_connect_api_key_integrations(integrations, composio_id)
        mcp_server_id = await create_mcp_server(agent_id, integrations)
        if mcp_server_id:
            mcp_servers.append({
                "type": "url",
                "name": f"composio-{agent_id}",
                "url": mcp_url(mcp_server_id, composio_id),
            })

    system = _build_user_system(agent_id)
    tools = _build_tools([s["name"] for s in mcp_servers], custom_tools)

    client = get_async_client()
    agent = await client.beta.agents.create(
        name=config["name"],
        model=config.get("model", "claude-sonnet-4-6"),
        system=system,
        tools=tools,
        skills=_skill_entries(skill_ids),
        mcp_servers=mcp_servers,
    )

    return agent.id
