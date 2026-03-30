"""Conflict detection, resolution, and version log queries."""

from typing import Any, Dict, List, Optional

from app.db.client import get_supabase

CONFLICTS_TABLE = "agent_conflicts"
VERSION_LOG_TABLE = "agent_version_log"
AGENTS_TABLE = "agents"


# ── Version management ───────────────────────────────────────


async def get_prompt_version(org_id: str, agent_id: str) -> int:
    resp = (
        get_supabase()
        .table(AGENTS_TABLE)
        .select("prompt_version")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .single()
        .execute()
    )
    return resp.data["prompt_version"]


async def bump_prompt_version(org_id: str, agent_id: str) -> int:
    """Increment prompt_version and return the new value."""
    current = await get_prompt_version(org_id, agent_id)
    new_version = current + 1
    (
        get_supabase()
        .table(AGENTS_TABLE)
        .update({"prompt_version": new_version})
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .execute()
    )
    return new_version


# ── Version log ──────────────────────────────────────────────


async def log_version_entry(
    org_id: str, agent_id: str, version: int, action: str, path: str,
    previous_content: Optional[str] = None,
) -> None:
    (
        get_supabase()
        .table(VERSION_LOG_TABLE)
        .upsert({
            "org_id": org_id,
            "agent_id": agent_id,
            "version": version,
            "action": action,
            "path": path,
            "previous_content": previous_content,
        }, on_conflict="org_id,agent_id,version,path")
        .execute()
    )


async def get_version_log(
    org_id: str, agent_id: str, version: Optional[int] = None
) -> List[Dict[str, Any]]:
    query = (
        get_supabase()
        .table(VERSION_LOG_TABLE)
        .select("version, action, path, created_at")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
    )
    if version is not None:
        query = query.eq("version", version)
    resp = query.order("version", desc=True).order("path").execute()
    return resp.data or []


# ── Conflicts ────────────────────────────────────────────────


async def create_conflict(
    org_id: str, agent_id: str, version: int,
    end_user_id: str, path: str, conflict_type: str,
    base_content: Optional[str], end_user_content: Optional[str],
    new_content: Optional[str],
) -> Dict[str, Any]:
    """Create or supersede a conflict (upsert on end_user_id + path)."""
    row = {
        "org_id": org_id,
        "agent_id": agent_id,
        "version": version,
        "end_user_id": end_user_id,
        "path": path,
        "conflict_type": conflict_type,
        "base_content": base_content,
        "end_user_content": end_user_content,
        "new_content": new_content,
        "status": "unresolved",
        "resolved_at": None,
    }
    resp = (
        get_supabase()
        .table(CONFLICTS_TABLE)
        .upsert(row, on_conflict="org_id,agent_id,end_user_id,path")
        .execute()
    )
    return resp.data[0]


async def get_unresolved_conflicts(
    org_id: str, agent_id: str,
    end_user_id: Optional[str] = None,
    path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query = (
        get_supabase()
        .table(CONFLICTS_TABLE)
        .select("*")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("status", "unresolved")
    )
    if end_user_id:
        query = query.eq("end_user_id", end_user_id)
    if path:
        query = query.eq("path", path)
    resp = query.order("created_at", desc=True).execute()
    return resp.data or []


async def get_conflict_summary(org_id: str, agent_id: str) -> Dict[str, Any]:
    """Aggregate unresolved conflicts: total, by_path, by_end_user."""
    conflicts = await get_unresolved_conflicts(org_id, agent_id)
    by_path: Dict[str, int] = {}
    by_end_user: Dict[str, int] = {}
    for c in conflicts:
        by_path[c["path"]] = by_path.get(c["path"], 0) + 1
        by_end_user[c["end_user_id"]] = by_end_user.get(c["end_user_id"], 0) + 1
    return {
        "total_unresolved": len(conflicts),
        "by_path": by_path,
        "by_end_user": by_end_user,
    }


async def resolve_conflicts(
    org_id: str, agent_id: str,
    end_user_id: Optional[str] = None,
    path: Optional[str] = None,
    resolution_status: str = "resolved_keep_admin",
) -> int:
    """Mark matching unresolved conflicts as resolved. Returns count."""
    query = (
        get_supabase()
        .table(CONFLICTS_TABLE)
        .update({"status": resolution_status, "resolved_at": "now()"})
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("status", "unresolved")
    )
    if end_user_id:
        query = query.eq("end_user_id", end_user_id)
    if path:
        query = query.eq("path", path)
    resp = query.execute()
    return len(resp.data or [])


async def get_end_user_overview(org_id: str, agent_id: str) -> List[Dict[str, Any]]:
    """Get override + conflict counts per end user (for admin dashboard)."""
    # Get override counts
    override_resp = (
        get_supabase()
        .table("agent_files")
        .select("end_user_id")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .not_.is_("end_user_id", "null")
        .execute()
    )
    override_counts: Dict[str, int] = {}
    for row in override_resp.data or []:
        uid = row["end_user_id"]
        override_counts[uid] = override_counts.get(uid, 0) + 1

    # Get conflict counts
    conflict_resp = (
        get_supabase()
        .table(CONFLICTS_TABLE)
        .select("end_user_id")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("status", "unresolved")
        .execute()
    )
    conflict_counts: Dict[str, int] = {}
    for row in conflict_resp.data or []:
        uid = row["end_user_id"]
        conflict_counts[uid] = conflict_counts.get(uid, 0) + 1

    # Merge
    all_users = set(override_counts.keys()) | set(conflict_counts.keys())
    return [
        {
            "end_user_id": uid,
            "override_count": override_counts.get(uid, 0),
            "conflict_count": conflict_counts.get(uid, 0),
        }
        for uid in sorted(all_users)
    ]
