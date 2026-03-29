"""Agent prompt file queries — virtual filesystem operations.

Core ops (fast path): ls, read_file, write_file, edit_file, grep, glob
Supporting ops: mkdir, rm, rm_rf, mv, stat, tree
"""

import posixpath
import re
from typing import Any, Dict, List, Optional

from app.db.client import get_supabase
from app.models.files import classify_file

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


async def ls(org_id: str, agent_id: str, parent: str = "/") -> List[Dict[str, Any]]:
    resp = (
        get_supabase()
        .table(TABLE)
        .select("id, path, name, type, access_level, mime_type, size_bytes, file_class, created_by, updated_at")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("parent", parent)
        .order("type", desc=True)
        .order("name")
        .execute()
    )
    return resp.data or []


async def read_file(org_id: str, agent_id: str, path: str) -> Optional[Dict[str, Any]]:
    resp = (
        get_supabase()
        .table(TABLE)
        .select("content, mime_type, size_bytes, access_level, file_class, name, type")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("path", path)
        .maybe_single()
        .execute()
    )
    return resp.data


async def write_file(
    org_id: str,
    agent_id: str,
    path: str,
    content: str,
    mime_type: str = "text/markdown",
    access_level: str = "org_read",
    created_by: str = "system",
) -> Dict[str, Any]:
    name = posixpath.basename(path)
    derived = _derive_fields(path, name, content)
    row = {
        "org_id": org_id,
        "agent_id": agent_id,
        "path": path,
        "name": name,
        "type": "file",
        "access_level": access_level,
        "content": content,
        "mime_type": mime_type,
        "created_by": created_by,
        **derived,
    }
    resp = (
        get_supabase()
        .table(TABLE)
        .upsert(row, on_conflict="org_id,agent_id,path")
        .execute()
    )
    return resp.data[0]


async def edit_file(
    org_id: str, agent_id: str, path: str, old_str: str, new_str: str
) -> Optional[Dict[str, Any]]:
    """Replace first occurrence of old_str with new_str in file content."""
    file = await read_file(org_id, agent_id, path)
    if not file or old_str not in file["content"]:
        return None
    updated_content = file["content"].replace(old_str, new_str, 1)
    return await write_file(org_id, agent_id, path, updated_content, file.get("mime_type", "text/markdown"))


async def grep(
    org_id: str, agent_id: str, pattern: str, case_insensitive: bool = False
) -> List[Dict[str, Any]]:
    """Regex search across all files for an agent. Returns matching paths + lines."""
    # Fetch all file content for the agent (filtered set is small)
    resp = (
        get_supabase()
        .table(TABLE)
        .select("path, name, file_class, content")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("type", "file")
        .execute()
    )
    flags = re.IGNORECASE if case_insensitive else 0
    compiled = re.compile(pattern, flags)
    results = []
    for row in resp.data or []:
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


async def glob(org_id: str, agent_id: str, pattern: str) -> List[Dict[str, Any]]:
    """Match files by glob pattern. Supports *.md, skills/**/*.md, etc."""
    # Convert glob to SQL LIKE + name filter
    # Split pattern into directory prefix and filename pattern
    if "**" in pattern:
        # e.g. "skills/**/*.md" → path LIKE 'skills/%' AND name LIKE '%.md'
        prefix = pattern.split("**")[0].rstrip("/")
        name_part = pattern.split("**")[-1].lstrip("/")
    elif "/" in pattern:
        prefix = posixpath.dirname(pattern)
        name_part = posixpath.basename(pattern)
    else:
        prefix = ""
        name_part = pattern

    # Convert glob wildcards to SQL LIKE
    name_like = name_part.replace("*", "%").replace("?", "_") if name_part else "%"

    query = (
        get_supabase()
        .table(TABLE)
        .select("path, name, type, file_class, size_bytes, updated_at")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
    )
    if prefix:
        query = query.like("path", f"{prefix}/%")
    if name_like != "%":
        query = query.like("name", name_like)

    resp = query.order("updated_at", desc=True).execute()
    return resp.data or []


# ── Supporting ops ───────────────────────────────────────────


async def mkdir(
    org_id: str, agent_id: str, path: str, created_by: str = "system"
) -> Dict[str, Any]:
    name = posixpath.basename(path)
    derived = _derive_fields(path, name)
    row = {
        "org_id": org_id,
        "agent_id": agent_id,
        "path": path,
        "name": name,
        "type": "directory",
        "access_level": "org_read",
        "content": "",
        "mime_type": "",
        "created_by": created_by,
        **derived,
    }
    resp = (
        get_supabase()
        .table(TABLE)
        .upsert(row, on_conflict="org_id,agent_id,path")
        .execute()
    )
    return resp.data[0]


async def rm(org_id: str, agent_id: str, path: str) -> None:
    (
        get_supabase()
        .table(TABLE)
        .delete()
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("path", path)
        .execute()
    )


async def rm_rf(org_id: str, agent_id: str, path: str) -> int:
    """Delete a directory and everything under it."""
    # Delete the directory itself + all children whose path starts with path/
    resp1 = (
        get_supabase()
        .table(TABLE)
        .delete()
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .like("path", f"{path}/%")
        .execute()
    )
    resp2 = (
        get_supabase()
        .table(TABLE)
        .delete()
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("path", path)
        .execute()
    )
    return len(resp1.data or []) + len(resp2.data or [])


async def mv(org_id: str, agent_id: str, old_path: str, new_path: str) -> None:
    """Move/rename a file or directory. Also updates children if directory."""
    new_name = posixpath.basename(new_path)
    new_derived = _derive_fields(new_path, new_name)

    # Move the node itself
    (
        get_supabase()
        .table(TABLE)
        .update({"path": new_path, "name": new_name, **new_derived})
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("path", old_path)
        .execute()
    )

    # Move children (if directory)
    children_resp = (
        get_supabase()
        .table(TABLE)
        .select("id, path, name")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .like("path", f"{old_path}/%")
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


async def stat(org_id: str, agent_id: str, path: str) -> Optional[Dict[str, Any]]:
    resp = (
        get_supabase()
        .table(TABLE)
        .select("id, path, name, type, access_level, mime_type, size_bytes, file_class, created_by, created_at, updated_at")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("path", path)
        .maybe_single()
        .execute()
    )
    return resp.data


async def exists(org_id: str, agent_id: str, path: str) -> bool:
    resp = (
        get_supabase()
        .table(TABLE)
        .select("id")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
        .eq("path", path)
        .maybe_single()
        .execute()
    )
    return resp.data is not None


async def tree(org_id: str, agent_id: str, root: str = "/") -> List[Dict[str, Any]]:
    """Flat list of all nodes under root, ordered by path (for tree rendering)."""
    query = (
        get_supabase()
        .table(TABLE)
        .select("path, name, type, file_class")
        .eq("org_id", org_id)
        .eq("agent_id", agent_id)
    )
    if root != "/":
        query = query.like("path", f"{root}/%")
    resp = query.order("path").execute()
    return resp.data or []
