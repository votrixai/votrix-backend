"""Agent queries — CRUD for agents table + prompt sections + registry."""

from typing import Any, Dict, Optional

from app.db.client import get_supabase

TABLE = "agents"

# Maps prompt section keys to DB column names.
_PROMPT_COLS = {
    "identity": "prompt_identity",
    "soul": "prompt_soul",
    "agents": "prompt_agents",
    "user": "prompt_user",
    "tools": "prompt_tools",
    "bootstrap": "prompt_bootstrap",
}


async def get_agent(org_id: str, agent_id: str = "default") -> Optional[Dict[str, Any]]:
    resp = (
        get_supabase()
        .table(TABLE)
        .select("*")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .maybe_single()
        .execute()
    )
    return resp.data


async def create_agent(org_id: str, agent_id: str = "default", **kwargs) -> Dict[str, Any]:
    row = {"org_id": org_id, "agent_id": agent_id, **kwargs}
    resp = get_supabase().table(TABLE).insert(row).execute()
    return resp.data[0]


async def get_prompt_sections(org_id: str, agent_id: str = "default") -> Dict[str, str]:
    cols = ", ".join(_PROMPT_COLS.values())
    resp = (
        get_supabase()
        .table(TABLE)
        .select(cols)
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .maybe_single()
        .execute()
    )
    if not resp.data:
        return {}
    row = resp.data
    return {key: row.get(col, "") for key, col in _PROMPT_COLS.items()}


async def set_prompt_section(org_id: str, agent_id: str, section: str, content: str) -> None:
    col = _PROMPT_COLS.get(section)
    if not col:
        raise ValueError(f"Unknown prompt section: {section}")
    (
        get_supabase()
        .table(TABLE)
        .update({col: content, "updated_at": "now()"})
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .execute()
    )


async def get_registry(org_id: str, agent_id: str = "default") -> Dict[str, Any]:
    resp = (
        get_supabase()
        .table(TABLE)
        .select("registry")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .maybe_single()
        .execute()
    )
    if not resp.data:
        return {}
    return resp.data.get("registry") or {}


async def set_registry(org_id: str, agent_id: str, registry: Dict[str, Any]) -> None:
    (
        get_supabase()
        .table(TABLE)
        .update({"registry": registry, "updated_at": "now()"})
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .execute()
    )


async def set_registry_field(org_id: str, agent_id: str, field: str, value: Any) -> None:
    """Update a single top-level field in the registry JSONB."""
    reg = await get_registry(org_id, agent_id)
    reg[field] = value
    await set_registry(org_id, agent_id, reg)


async def list_agents(org_id: str):
    resp = (
        get_supabase()
        .table(TABLE)
        .select("agent_id, created_at, updated_at")
        .eq("org_id", org_id)
        .execute()
    )
    return resp.data or []


async def delete_agent(org_id: str, agent_id: str) -> None:
    (
        get_supabase()
        .table(TABLE)
        .delete()
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .execute()
    )
