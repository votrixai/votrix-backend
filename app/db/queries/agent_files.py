"""Agent prompt file queries — virtual filesystem operations.

Core ops (fast path): ls, read_file, write_file, edit_file, grep, glob
Supporting ops: mkdir, rm, rm_rf, mv, stat, tree

Override layer:
  - end_user_id=None → base file (member-owned)
  - end_user_id=<id> → end user override
  - Reads for end users merge base + overrides via DISTINCT ON
"""

import posixpath
import re
from typing import Any, Dict, List, Optional

from app.db.client import get_supabase
from app.models.files import classify_file, default_end_user_perm

TABLE = "agent_prompt_files"


def _base_query(org_id: str, agent_id: str):
    return get_supabase().table(TABLE).select("*").eq("org_id", org_id).eq("agent_id", agent_id)


def _derive_fields(path: str, name: str, content: str = "") -> Dict[str, Any]:
    """Compute derived columns for a file row."""
    return {
        "parent": posixpath.dirname(path) or "/",
        "ext": name.rsplit(".", 1)[-1] if "." in name else "",
        "depth": path.strip("/").count("/") + 1 if path.strip("/") else 0,
        "size_bytes": len(content.encode("utf-8")) if content else 0,
        "file_class": classify_file(path, name),
    }


# ── Core ops ─────────────────────────────────────────────────


async def ls(
    org_id: str, agent_id: str, parent: str = "/", *, end_user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List directory contents. For end users, merges base + overrides."""
    cols = "id, path, name, type, end_user_perm, end_user_id, mime_type, size_bytes, file_class, created_by, updated_at"

    if end_user_id is None:
        # Member view: base files only
        resp = (
            get_supabase()
            .table(TABLE)
            .select(cols)
            .eq("org_id", org_id)
            .eq("agent_id", agent_id)
            .eq("parent", parent)
            .is_("end_user_id", "null")
            .order("type", desc=True)
            .order("name")
            .execute()
        )
        return resp.data or []
    else:
        # End user view: base files + overrides, override wins on same path
        # Fetch both base and user rows under this parent
        resp = (
            get_supabase()
            .table(TABLE)
            .select(cols)
            .eq("org_id", org_id)
            .eq("agent_id", agent_id)
            .eq("parent", parent)
            .or_(f"end_user_id.is.null,end_user_id.eq.{end_user_id}")
            .order("type", desc=True)
            .order("name")
            .execute()
        )
        # Merge: override wins per path
        merged: Dict[str, Dict] = {}
        for row in resp.data or []:
            path = row["path"]
            if path not in merged or row.get("end_user_id") is not None:
                merged[path] = row
        # Filter out files with end_user_perm = 'none'
        return [r for r in merged.values() if r.get("end_user_perm", "r") != "none"]


async def read_file(
    org_id: str, agent_id: str, path: str, *, end_user_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Read a file. For end users, returns override if exists, else base."""
    cols = "content, mime_type, size_bytes, end_user_perm, end_user_id, file_class, name, type, path"

    if end_user_id is None:
        # Member: read base only
        resp = (
            get_supabase()
            .table(TABLE)
            .select(cols)
            .eq("org_id", org_id)
            .eq("agent_id", agent_id)
            .eq("path", path)
            .is_("end_user_id", "null")
            .maybe_single()
            .execute()
        )
        return resp.data
    else:
        # End user: try override first, fall back to base
        resp = (
            get_supabase()
            .table(TABLE)
            .select(cols)
            .eq("org_id", org_id)
            .eq("agent_id", agent_id)
            .eq("path", path)
            .or_(f"end_user_id.is.null,end_user_id.eq.{end_user_id}")
            .order("end_user_id", nullsfirst=False)  # override first
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return None
        row = rows[0]
        # Check permission
        if row.get("end_user_perm", "r") == "none":
            return None
        return row


async def write_file(
    org_id: str,
    agent_id: str,
    path: str,
    content: str,
    mime_type: str = "text/markdown",
    end_user_perm: str = "r",
    created_by: str = "system",
    *,
    end_user_id: Optional[str] = None,
    base_version: int = 1,
) -> Dict[str, Any]:
    """Write a file. If end_user_id is set, creates/updates an override."""
    name = posixpath.basename(path)
    derived = _derive_fields(path, name, content)

    # For end user writes, use default perm from base
    if end_user_id is not None:
        end_user_perm = default_end_user_perm(path, name)

    row = {
        "org_id": org_id,
        "agent_id": agent_id,
        "end_user_id": end_user_id,
        "path": path,
        "name": name,
        "type": "file",
        "end_user_perm": end_user_perm,
        "content": content,
        "mime_type": mime_type,
        "base_version": base_version,
        "created_by": created_by,
        **derived,
    }
    # Upsert key includes coalesce(end_user_id, '') via unique constraint
    resp = (
        get_supabase()
        .table(TABLE)
        .upsert(row, on_conflict="org_id,agent_id,coalesce(end_user_id, ''),path")
        .execute()
    )
    return resp.data[0]


async def edit_file(
    org_id: str, agent_id: str, path: str, old_str: str, new_str: str,
    *, end_user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Replace first occurrence of old_str with new_str in file content."""
    file = await read_file(org_id, agent_id, path, end_user_id=end_user_id)
    if not file or old_str not in file["content"]:
        return None

    updated_content = file["content"].replace(old_str, new_str, 1)

    if end_user_id is not None:
        # End user editing: create/update override with the merged content
        return await write_file(
            org_id, agent_id, path, updated_content,
            file.get("mime_type", "text/markdown"),
            end_user_id=end_user_id,
            base_version=file.get("base_version", 1),
        )
    else:
        return await write_file(
            org_id, agent_id, path, updated_content,
            file.get("mime_type", "text/markdown"),
        )


async def grep(
    org_id: str, agent_id: str, pattern: str, case_insensitive: bool = False,
    *, end_user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Regex search across all files for an agent. Returns matching paths + lines."""
    query = (
        get_supabase()
        .table(TABLE)
        .select("path, name, file_class, content, end_user_id")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("type", "file")
    )
    if end_user_id is None:
        query = query.is_("end_user_id", "null")
    else:
        query = query.or_(f"end_user_id.is.null,end_user_id.eq.{end_user_id}")

    resp = query.execute()

    # If end user, merge so override wins
    rows = resp.data or []
    if end_user_id is not None:
        merged: Dict[str, Dict] = {}
        for row in rows:
            p = row["path"]
            if p not in merged or row.get("end_user_id") is not None:
                merged[p] = row
        rows = list(merged.values())

    flags = re.IGNORECASE if case_insensitive else 0
    compiled = re.compile(pattern, flags)
    results = []
    for row in rows:
        lines = row["content"].split("\n")
        matching = [line for line in lines if compiled.search(line)]
        if matching:
            results.append({
                "path": row["path"],
                "name": row["name"],
                "file_class": row["file_class"],
                "matches": matching,
            })
    return results


async def glob(
    org_id: str, agent_id: str, pattern: str,
    *, end_user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Match files by glob pattern. Supports *.md, skills/**/*.md, etc."""
    if "**" in pattern:
        prefix = pattern.split("**")[0].rstrip("/")
        name_part = pattern.split("**")[-1].lstrip("/")
    elif "/" in pattern:
        prefix = posixpath.dirname(pattern)
        name_part = posixpath.basename(pattern)
    else:
        prefix = ""
        name_part = pattern

    name_like = name_part.replace("*", "%").replace("?", "_") if name_part else "%"

    query = (
        get_supabase()
        .table(TABLE)
        .select("path, name, type, file_class, size_bytes, updated_at, end_user_id")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
    )
    if end_user_id is None:
        query = query.is_("end_user_id", "null")
    else:
        query = query.or_(f"end_user_id.is.null,end_user_id.eq.{end_user_id}")

    if prefix:
        query = query.like("path", f"{prefix}/%")
    if name_like != "%":
        query = query.like("name", name_like)

    resp = query.order("updated_at", desc=True).execute()

    rows = resp.data or []
    if end_user_id is not None:
        merged: Dict[str, Dict] = {}
        for row in rows:
            p = row["path"]
            if p not in merged or row.get("end_user_id") is not None:
                merged[p] = row
        rows = list(merged.values())

    return rows


# ── Supporting ops ───────────────────────────────────────────


async def mkdir(
    org_id: str, agent_id: str, path: str, created_by: str = "system"
) -> Dict[str, Any]:
    name = posixpath.basename(path)
    derived = _derive_fields(path, name)
    row = {
        "org_id": org_id,
        "agent_id": agent_id,
        "end_user_id": None,
        "path": path,
        "name": name,
        "type": "directory",
        "end_user_perm": "r",
        "content": "",
        "mime_type": "",
        "created_by": created_by,
        **derived,
    }
    resp = (
        get_supabase()
        .table(TABLE)
        .upsert(row, on_conflict="org_id,agent_id,coalesce(end_user_id, ''),path")
        .execute()
    )
    return resp.data[0]


async def rm(org_id: str, agent_id: str, path: str, *, end_user_id: Optional[str] = None) -> None:
    query = (
        get_supabase()
        .table(TABLE)
        .delete()
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("path", path)
    )
    if end_user_id is None:
        query = query.is_("end_user_id", "null")
    else:
        query = query.eq("end_user_id", end_user_id)
    query.execute()


async def rm_rf(org_id: str, agent_id: str, path: str, *, end_user_id: Optional[str] = None) -> int:
    """Delete a directory and everything under it."""
    def _scoped(q):
        if end_user_id is None:
            return q.is_("end_user_id", "null")
        return q.eq("end_user_id", end_user_id)

    resp1 = _scoped(
        get_supabase()
        .table(TABLE)
        .delete()
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .like("path", f"{path}/%")
    ).execute()

    resp2 = _scoped(
        get_supabase()
        .table(TABLE)
        .delete()
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("path", path)
    ).execute()

    return len(resp1.data or []) + len(resp2.data or [])


async def mv(org_id: str, agent_id: str, old_path: str, new_path: str) -> None:
    """Move/rename a file or directory (base files only). Also updates children."""
    new_name = posixpath.basename(new_path)
    new_derived = _derive_fields(new_path, new_name)

    (
        get_supabase()
        .table(TABLE)
        .update({"path": new_path, "name": new_name, **new_derived})
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("path", old_path)
        .is_("end_user_id", "null")
        .execute()
    )

    children_resp = (
        get_supabase()
        .table(TABLE)
        .select("id, path, name")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .like("path", f"{old_path}/%")
        .is_("end_user_id", "null")
        .execute()
    )
    for child in children_resp.data or []:
        child_new_path = new_path + child["path"][len(old_path):]
        child_derived = _derive_fields(child_new_path, child["name"])
        (
            get_supabase()
            .table(TABLE)
            .update({"path": child_new_path, **child_derived})
            .eq("id", child["id"])
            .execute()
        )


async def stat(
    org_id: str, agent_id: str, path: str, *, end_user_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    cols = "id, path, name, type, end_user_perm, end_user_id, mime_type, size_bytes, file_class, created_by, created_at, updated_at"
    query = (
        get_supabase()
        .table(TABLE)
        .select(cols)
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("path", path)
    )
    if end_user_id is None:
        query = query.is_("end_user_id", "null")
    else:
        query = query.eq("end_user_id", end_user_id)
    resp = query.maybe_single().execute()
    return resp.data


async def exists(
    org_id: str, agent_id: str, path: str, *, end_user_id: Optional[str] = None
) -> bool:
    query = (
        get_supabase()
        .table(TABLE)
        .select("id")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("path", path)
    )
    if end_user_id is None:
        query = query.is_("end_user_id", "null")
    else:
        query = query.eq("end_user_id", end_user_id)
    resp = query.maybe_single().execute()
    return resp.data is not None


async def tree(
    org_id: str, agent_id: str, root: str = "/", *, end_user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Flat list of all nodes under root, ordered by path."""
    query = (
        get_supabase()
        .table(TABLE)
        .select("path, name, type, file_class, end_user_id")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
    )
    if end_user_id is None:
        query = query.is_("end_user_id", "null")
    else:
        query = query.or_(f"end_user_id.is.null,end_user_id.eq.{end_user_id}")

    if root != "/":
        query = query.like("path", f"{root}/%")

    resp = query.order("path").execute()

    rows = resp.data or []
    if end_user_id is not None:
        merged: Dict[str, Dict] = {}
        for row in rows:
            p = row["path"]
            if p not in merged or row.get("end_user_id") is not None:
                merged[p] = row
        rows = sorted(merged.values(), key=lambda r: r["path"])

    return rows


# ── Override layer helpers ───────────────────────────────────


async def get_all_base_files(org_id: str, agent_id: str) -> List[Dict[str, Any]]:
    """Get all base files (for publish diffing)."""
    resp = (
        get_supabase()
        .table(TABLE)
        .select("path, name, content, base_version, end_user_perm, file_class")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("type", "file")
        .is_("end_user_id", "null")
        .execute()
    )
    return resp.data or []


async def get_end_user_overrides(
    org_id: str, agent_id: str, end_user_id: str
) -> List[Dict[str, Any]]:
    """Get all overrides for a specific end user."""
    resp = (
        get_supabase()
        .table(TABLE)
        .select("path, name, content, base_version, end_user_perm, file_class")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("end_user_id", end_user_id)
        .eq("type", "file")
        .execute()
    )
    return resp.data or []


async def get_all_overrides_for_paths(
    org_id: str, agent_id: str, paths: List[str]
) -> List[Dict[str, Any]]:
    """Get all end user overrides that touch any of the given paths."""
    if not paths:
        return []
    resp = (
        get_supabase()
        .table(TABLE)
        .select("path, name, content, base_version, end_user_id, end_user_perm")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .not_.is_("end_user_id", "null")
        .in_("path", paths)
        .execute()
    )
    return resp.data or []


async def bump_base_version(
    org_id: str, agent_id: str, paths: List[str], new_version: int
) -> None:
    """Update base_version on base files after publish."""
    if not paths:
        return
    (
        get_supabase()
        .table(TABLE)
        .update({"base_version": new_version})
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .is_("end_user_id", "null")
        .in_("path", paths)
        .execute()
    )


async def delete_end_user_overrides(
    org_id: str, agent_id: str, end_user_id: str, paths: Optional[List[str]] = None
) -> int:
    """Delete overrides for an end user. If paths given, only those; else all."""
    query = (
        get_supabase()
        .table(TABLE)
        .delete()
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("end_user_id", end_user_id)
    )
    if paths:
        query = query.in_("path", paths)
    resp = query.execute()
    return len(resp.data or [])


async def update_override_base_version(
    org_id: str, agent_id: str, end_user_id: str, path: str, new_version: int
) -> None:
    """Bump an override's base_version after conflict resolution (auto-sync)."""
    (
        get_supabase()
        .table(TABLE)
        .update({"base_version": new_version})
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("end_user_id", end_user_id)
        .eq("path", path)
        .execute()
    )
