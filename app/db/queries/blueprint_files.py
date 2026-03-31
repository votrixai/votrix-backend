"""Blueprint file queries — admin/member-owned virtual filesystem.

Core ops (fast path): ls, read_file, write_file, edit_file, grep, glob
Supporting ops: mkdir, rm, rm_rf, mv, stat, tree
"""

from __future__ import annotations

import posixpath
import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.blueprint_files import BlueprintFile
from app.models.files import classify_file
from app.storage import BUCKET, is_text_mime, upload_file as storage_upload, delete_file as storage_delete


def _derive_fields(path: str, name: str, content: str = "", size_bytes: int = 0) -> Dict[str, Any]:
    """Compute derived columns for a file row."""
    return {
        "parent": posixpath.dirname(path) or "/",
        "ext": name.rsplit(".", 1)[-1] if "." in name else "",
        "depth": path.strip("/").count("/") + 1 if path.strip("/") else 0,
        "size_bytes": size_bytes or (len(content.encode("utf-8")) if content else 0),
        "file_class": classify_file(path, name),
    }


def _row_to_dict(row) -> Dict[str, Any]:
    if hasattr(row, "__table__"):
        return {c.key: getattr(row, c.key) for c in row.__table__.columns}
    return dict(row)


async def _ensure_ancestors(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    path: str, created_by: str = "system",
) -> None:
    """Auto-create missing ancestor directory rows (mkdir -p)."""
    parts = path.strip("/").split("/")
    for i in range(1, len(parts)):
        ancestor = "/" + "/".join(parts[:i])
        name = parts[i - 1]
        derived = _derive_fields(ancestor, name)
        values = {
            "blueprint_agent_id": blueprint_agent_id,
            "path": ancestor,
            "name": name,
            "type": "directory",
            "content": "",
            "mime_type": "",
            "created_by": created_by,
            **derived,
        }
        stmt = (
            pg_insert(BlueprintFile)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["blueprint_agent_id", "path"])
        )
        await session.execute(stmt)


# ── Core ops ─────────────────────────────────────────────────


async def ls(
    session: AsyncSession, blueprint_agent_id: uuid.UUID, parent: str = "/"
) -> List[Dict[str, Any]]:
    """List directory contents (base files only)."""
    stmt = (
        select(
            BlueprintFile.id, BlueprintFile.path, BlueprintFile.name,
            BlueprintFile.type, BlueprintFile.mime_type, BlueprintFile.size_bytes,
            BlueprintFile.file_class, BlueprintFile.created_by, BlueprintFile.updated_at,
        )
        .where(
            BlueprintFile.blueprint_agent_id == blueprint_agent_id,
            BlueprintFile.parent == parent,
        )
        .order_by(BlueprintFile.type.desc(), BlueprintFile.name)
    )
    result = await session.execute(stmt)
    return [dict(r) for r in result.mappings()]


async def read_file(
    session: AsyncSession, blueprint_agent_id: uuid.UUID, path: str
) -> Optional[Dict[str, Any]]:
    """Read a base file by path."""
    stmt = (
        select(
            BlueprintFile.content, BlueprintFile.mime_type, BlueprintFile.size_bytes,
            BlueprintFile.file_class, BlueprintFile.name, BlueprintFile.type, BlueprintFile.path,
            BlueprintFile.storage_path,
        )
        .where(
            BlueprintFile.blueprint_agent_id == blueprint_agent_id,
            BlueprintFile.path == path,
        )
    )
    result = await session.execute(stmt)
    row = result.mappings().first()
    return dict(row) if row else None


async def write_file(
    session: AsyncSession,
    blueprint_agent_id: uuid.UUID,
    path: str,
    content: Optional[str] = None,
    mime_type: str = "text/markdown",
    created_by: str = "system",
    binary_data: Optional[bytes] = None,
) -> Dict[str, Any]:
    """Write or upsert a base file. Text content goes to Postgres, binary to Storage."""
    name = posixpath.basename(path)
    await _ensure_ancestors(session, blueprint_agent_id, path, created_by)

    # Clean up old storage object if overwriting a binary file
    old_storage = (
        await session.execute(
            select(BlueprintFile.storage_path)
            .where(BlueprintFile.blueprint_agent_id == blueprint_agent_id, BlueprintFile.path == path)
        )
    ).scalar_one_or_none()
    if old_storage:
        await storage_delete(BUCKET, old_storage)

    storage_path = None
    if binary_data is not None:
        if is_text_mime(mime_type):
            # Text-ish binary upload — decode to string and store in Postgres
            content = binary_data.decode("utf-8", errors="replace")
            size = len(binary_data)
        else:
            # Binary file → upload to Supabase Storage
            storage_path = f"blueprints/{blueprint_agent_id}{path}"
            await storage_upload(BUCKET, storage_path, binary_data, mime_type)
            content = None
            size = len(binary_data)
    else:
        content = content or ""
        size = len(content.encode("utf-8"))

    derived = _derive_fields(path, name, content or "", size_bytes=size)
    values = {
        "blueprint_agent_id": blueprint_agent_id,
        "path": path,
        "name": name,
        "type": "file",
        "content": content,
        "storage_path": storage_path,
        "mime_type": mime_type,
        "created_by": created_by,
        **derived,
    }
    update_cols = {k: v for k, v in values.items() if k not in ("blueprint_agent_id", "path")}
    stmt = (
        pg_insert(BlueprintFile)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["blueprint_agent_id", "path"],
            set_=update_cols,
        )
        .returning(BlueprintFile)
    )
    result = await session.execute(stmt)
    await session.commit()
    return _row_to_dict(result.scalar_one())


async def edit_file(
    session: AsyncSession, blueprint_agent_id: uuid.UUID, path: str, old_str: str, new_str: str
) -> Optional[Dict[str, Any]]:
    """Replace first occurrence of old_str with new_str in file content."""
    file = await read_file(session, blueprint_agent_id, path)
    if not file or not file.get("content") or old_str not in file["content"]:
        return None
    updated_content = file["content"].replace(old_str, new_str, 1)
    return await write_file(
        session, blueprint_agent_id, path, updated_content,
        file.get("mime_type", "text/markdown"),
    )


async def grep(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    pattern: str, case_insensitive: bool = False
) -> List[Dict[str, Any]]:
    """Regex search across all base files. Returns matching paths + lines."""
    stmt = (
        select(
            BlueprintFile.path, BlueprintFile.name, BlueprintFile.file_class,
            BlueprintFile.content, BlueprintFile.storage_path,
        )
        .where(
            BlueprintFile.blueprint_agent_id == blueprint_agent_id,
            BlueprintFile.type == "file",
        )
    )
    result = await session.execute(stmt)
    flags = re.IGNORECASE if case_insensitive else 0
    compiled = re.compile(pattern, flags)
    results = []
    for row in result.mappings():
        if row["storage_path"] is not None:
            # Binary file — match against filename/path only
            if compiled.search(row["name"]) or compiled.search(row["path"]):
                results.append({
                    "path": row["path"],
                    "name": row["name"],
                    "file_class": row["file_class"],
                    "matches": ["[binary file]"],
                })
        else:
            content = row["content"] or ""
            lines = content.split("\n")
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
    session: AsyncSession, blueprint_agent_id: uuid.UUID, pattern: str
) -> List[Dict[str, Any]]:
    """Match base files by glob pattern. Supports *.md, skills/**/*.md, etc."""
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

    stmt = (
        select(
            BlueprintFile.path, BlueprintFile.name, BlueprintFile.type,
            BlueprintFile.file_class, BlueprintFile.size_bytes, BlueprintFile.updated_at,
        )
        .where(BlueprintFile.blueprint_agent_id == blueprint_agent_id)
    )
    if prefix:
        stmt = stmt.where(BlueprintFile.path.like(f"{prefix}/%"))
    if name_like != "%":
        stmt = stmt.where(BlueprintFile.name.like(name_like))

    stmt = stmt.order_by(BlueprintFile.updated_at.desc())
    result = await session.execute(stmt)
    return [dict(r) for r in result.mappings()]


# ── Supporting ops ───────────────────────────────────────────


async def mkdir(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    path: str, created_by: str = "system"
) -> Dict[str, Any]:
    name = posixpath.basename(path)
    await _ensure_ancestors(session, blueprint_agent_id, path, created_by)

    # Clean up storage if overwriting a binary file with a directory
    old_storage = (
        await session.execute(
            select(BlueprintFile.storage_path)
            .where(BlueprintFile.blueprint_agent_id == blueprint_agent_id, BlueprintFile.path == path)
        )
    ).scalar_one_or_none()
    if old_storage:
        await storage_delete(BUCKET, old_storage)

    derived = _derive_fields(path, name)
    values = {
        "blueprint_agent_id": blueprint_agent_id,
        "path": path,
        "name": name,
        "type": "directory",
        "content": "",
        "storage_path": None,
        "mime_type": "",
        "created_by": created_by,
        **derived,
    }
    update_cols = {k: v for k, v in values.items() if k not in ("blueprint_agent_id", "path")}
    stmt = (
        pg_insert(BlueprintFile)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["blueprint_agent_id", "path"],
            set_=update_cols,
        )
        .returning(BlueprintFile)
    )
    result = await session.execute(stmt)
    await session.commit()
    return _row_to_dict(result.scalar_one())


async def rm(session: AsyncSession, blueprint_agent_id: uuid.UUID, path: str) -> None:
    # Check for storage file to clean up
    check = (
        select(BlueprintFile.storage_path)
        .where(BlueprintFile.blueprint_agent_id == blueprint_agent_id, BlueprintFile.path == path)
    )
    row = (await session.execute(check)).scalar_one_or_none()
    if row:
        await storage_delete(BUCKET, row)

    stmt = (
        delete(BlueprintFile)
        .where(BlueprintFile.blueprint_agent_id == blueprint_agent_id, BlueprintFile.path == path)
    )
    await session.execute(stmt)
    await session.commit()


async def rm_rf(session: AsyncSession, blueprint_agent_id: uuid.UUID, path: str) -> int:
    """Delete a directory and everything under it, including Storage objects."""
    # Collect storage paths to clean up before deleting rows
    storage_stmt = (
        select(BlueprintFile.storage_path)
        .where(
            BlueprintFile.blueprint_agent_id == blueprint_agent_id,
            BlueprintFile.storage_path.is_not(None),
            (BlueprintFile.path == path) | BlueprintFile.path.like(f"{path}/%"),
        )
    )
    storage_rows = (await session.execute(storage_stmt)).scalars().all()
    for sp in storage_rows:
        await storage_delete(BUCKET, sp)

    stmt1 = (
        delete(BlueprintFile)
        .where(
            BlueprintFile.blueprint_agent_id == blueprint_agent_id,
            BlueprintFile.path.like(f"{path}/%"),
        )
        .returning(BlueprintFile.id)
    )
    stmt2 = (
        delete(BlueprintFile)
        .where(BlueprintFile.blueprint_agent_id == blueprint_agent_id, BlueprintFile.path == path)
        .returning(BlueprintFile.id)
    )
    r1 = await session.execute(stmt1)
    r2 = await session.execute(stmt2)
    await session.commit()
    return len(r1.all()) + len(r2.all())


async def mv(
    session: AsyncSession, blueprint_agent_id: uuid.UUID, old_path: str, new_path: str
) -> None:
    """Move/rename a file or directory. Also updates children and Storage paths."""
    new_name = posixpath.basename(new_path)
    new_derived = _derive_fields(new_path, new_name)

    # Handle storage_path update for the moved file itself
    root_check = (
        await session.execute(
            select(BlueprintFile.storage_path, BlueprintFile.mime_type)
            .where(BlueprintFile.blueprint_agent_id == blueprint_agent_id, BlueprintFile.path == old_path)
        )
    ).mappings().first()
    root_updates = {"path": new_path, "name": new_name, **new_derived}
    if root_check and root_check["storage_path"]:
        new_storage = f"blueprints/{blueprint_agent_id}{new_path}"
        await _move_storage_object(root_check["storage_path"], new_storage, root_check["mime_type"])
        root_updates["storage_path"] = new_storage

    stmt = (
        update(BlueprintFile)
        .where(BlueprintFile.blueprint_agent_id == blueprint_agent_id, BlueprintFile.path == old_path)
        .values(**root_updates)
    )
    await session.execute(stmt)

    children_stmt = (
        select(BlueprintFile.id, BlueprintFile.path, BlueprintFile.name, BlueprintFile.storage_path, BlueprintFile.mime_type)
        .where(
            BlueprintFile.blueprint_agent_id == blueprint_agent_id,
            BlueprintFile.path.like(f"{old_path}/%"),
        )
    )
    children = (await session.execute(children_stmt)).mappings().all()
    for child in children:
        child_new_path = new_path + child["path"][len(old_path):]
        child_derived = _derive_fields(child_new_path, child["name"])
        child_updates = {"path": child_new_path, **child_derived}
        if child["storage_path"]:
            new_child_storage = f"blueprints/{blueprint_agent_id}{child_new_path}"
            await _move_storage_object(child["storage_path"], new_child_storage, child["mime_type"])
            child_updates["storage_path"] = new_child_storage
        child_stmt = (
            update(BlueprintFile)
            .where(BlueprintFile.id == child["id"])
            .values(**child_updates)
        )
        await session.execute(child_stmt)

    await session.commit()


async def _move_storage_object(old_storage_path: str, new_storage_path: str, mime_type: str = "application/octet-stream") -> None:
    """Move a Storage object by copying then deleting the original."""
    from app.storage import copy_file
    await copy_file(BUCKET, old_storage_path, new_storage_path, mime_type)
    await storage_delete(BUCKET, old_storage_path)


async def stat(
    session: AsyncSession, blueprint_agent_id: uuid.UUID, path: str
) -> Optional[Dict[str, Any]]:
    stmt = (
        select(
            BlueprintFile.id, BlueprintFile.path, BlueprintFile.name,
            BlueprintFile.type, BlueprintFile.mime_type, BlueprintFile.size_bytes,
            BlueprintFile.file_class, BlueprintFile.created_by,
            BlueprintFile.created_at, BlueprintFile.updated_at,
        )
        .where(
            BlueprintFile.blueprint_agent_id == blueprint_agent_id,
            BlueprintFile.path == path,
        )
    )
    result = await session.execute(stmt)
    row = result.mappings().first()
    return dict(row) if row else None


async def exists(session: AsyncSession, blueprint_agent_id: uuid.UUID, path: str) -> bool:
    stmt = (
        select(BlueprintFile.id)
        .where(BlueprintFile.blueprint_agent_id == blueprint_agent_id, BlueprintFile.path == path)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def tree(
    session: AsyncSession, blueprint_agent_id: uuid.UUID, root: str = "/"
) -> List[Dict[str, Any]]:
    """Flat list of all nodes under root, ordered by path."""
    stmt = (
        select(BlueprintFile.path, BlueprintFile.name, BlueprintFile.type, BlueprintFile.file_class)
        .where(BlueprintFile.blueprint_agent_id == blueprint_agent_id)
    )
    if root != "/":
        stmt = stmt.where(BlueprintFile.path.like(f"{root}/%"))
    stmt = stmt.order_by(BlueprintFile.path)
    result = await session.execute(stmt)
    return [dict(r) for r in result.mappings()]


async def get_all_files(session: AsyncSession, blueprint_agent_id: uuid.UUID) -> List[Dict[str, Any]]:
    """Get all base files (for publish diffing)."""
    stmt = (
        select(
            BlueprintFile.path, BlueprintFile.name, BlueprintFile.content,
            BlueprintFile.file_class, BlueprintFile.storage_path,
        )
        .where(
            BlueprintFile.blueprint_agent_id == blueprint_agent_id,
            BlueprintFile.type == "file",
        )
    )
    result = await session.execute(stmt)
    return [dict(r) for r in result.mappings()]
