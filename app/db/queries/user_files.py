"""User file queries — end-user's own independent files.

Pure CRUD scoped by (blueprint_agent_id, end_user_id).
Mirrors blueprint_files.py in API shape.
"""

from __future__ import annotations

import posixpath
import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user_files import UserFile
from app.models.files import classify_file


def _derive_fields(path: str, name: str, content: str = "") -> Dict[str, Any]:
    """Compute derived columns for a file row."""
    return {
        "parent": posixpath.dirname(path) or "/",
        "ext": name.rsplit(".", 1)[-1] if "." in name else "",
        "depth": path.strip("/").count("/") + 1 if path.strip("/") else 0,
        "size_bytes": len(content.encode("utf-8")) if content else 0,
        "file_class": classify_file(path, name),
    }


def _row_to_dict(row) -> Dict[str, Any]:
    if hasattr(row, "__table__"):
        return {c.key: getattr(row, c.key) for c in row.__table__.columns}
    return dict(row)


# ── Core ops ─────────────────────────────────────────────────


async def ls(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    end_user_id: str, parent: str = "/"
) -> List[Dict[str, Any]]:
    """List directory contents for an end user."""
    stmt = (
        select(
            UserFile.id, UserFile.path, UserFile.name, UserFile.type,
            UserFile.mime_type, UserFile.size_bytes, UserFile.file_class,
            UserFile.created_by, UserFile.updated_at,
        )
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.end_user_id == end_user_id,
            UserFile.parent == parent,
        )
        .order_by(UserFile.type.desc(), UserFile.name)
    )
    result = await session.execute(stmt)
    return [dict(r) for r in result.mappings()]


async def read_file(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    end_user_id: str, path: str
) -> Optional[Dict[str, Any]]:
    """Read a user file by path."""
    stmt = (
        select(
            UserFile.content, UserFile.mime_type, UserFile.size_bytes,
            UserFile.file_class, UserFile.name, UserFile.type, UserFile.path,
        )
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.end_user_id == end_user_id,
            UserFile.path == path,
        )
    )
    result = await session.execute(stmt)
    row = result.mappings().first()
    return dict(row) if row else None


async def write_file(
    session: AsyncSession,
    blueprint_agent_id: uuid.UUID,
    end_user_id: str,
    path: str,
    content: str,
    mime_type: str = "text/markdown",
    created_by: str = "system",
) -> Dict[str, Any]:
    """Write or upsert a user file."""
    name = posixpath.basename(path)
    derived = _derive_fields(path, name, content)
    values = {
        "blueprint_agent_id": blueprint_agent_id,
        "end_user_id": end_user_id,
        "path": path,
        "name": name,
        "type": "file",
        "content": content,
        "mime_type": mime_type,
        "created_by": created_by,
        **derived,
    }
    update_cols = {k: v for k, v in values.items() if k not in ("blueprint_agent_id", "end_user_id", "path")}
    stmt = (
        pg_insert(UserFile)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["blueprint_agent_id", "end_user_id", "path"],
            set_=update_cols,
        )
        .returning(UserFile)
    )
    result = await session.execute(stmt)
    await session.commit()
    return _row_to_dict(result.scalar_one())


async def edit_file(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    end_user_id: str, path: str, old_str: str, new_str: str
) -> Optional[Dict[str, Any]]:
    """Replace first occurrence of old_str with new_str in file content."""
    file = await read_file(session, blueprint_agent_id, end_user_id, path)
    if not file or old_str not in file["content"]:
        return None
    updated_content = file["content"].replace(old_str, new_str, 1)
    return await write_file(
        session, blueprint_agent_id, end_user_id, path, updated_content,
        file.get("mime_type", "text/markdown"),
    )


async def grep(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    end_user_id: str, pattern: str, case_insensitive: bool = False
) -> List[Dict[str, Any]]:
    """Regex search across all user files."""
    stmt = (
        select(UserFile.path, UserFile.name, UserFile.file_class, UserFile.content)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.end_user_id == end_user_id,
            UserFile.type == "file",
        )
    )
    result = await session.execute(stmt)
    flags = re.IGNORECASE if case_insensitive else 0
    compiled = re.compile(pattern, flags)
    results = []
    for row in result.mappings():
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
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    end_user_id: str, pattern: str
) -> List[Dict[str, Any]]:
    """Match user files by glob pattern."""
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
            UserFile.path, UserFile.name, UserFile.type,
            UserFile.file_class, UserFile.size_bytes, UserFile.updated_at,
        )
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.end_user_id == end_user_id,
        )
    )
    if prefix:
        stmt = stmt.where(UserFile.path.like(f"{prefix}/%"))
    if name_like != "%":
        stmt = stmt.where(UserFile.name.like(name_like))

    stmt = stmt.order_by(UserFile.updated_at.desc())
    result = await session.execute(stmt)
    return [dict(r) for r in result.mappings()]


# ── Supporting ops ───────────────────────────────────────────


async def mkdir(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    end_user_id: str, path: str, created_by: str = "system"
) -> Dict[str, Any]:
    name = posixpath.basename(path)
    derived = _derive_fields(path, name)
    values = {
        "blueprint_agent_id": blueprint_agent_id,
        "end_user_id": end_user_id,
        "path": path,
        "name": name,
        "type": "directory",
        "content": "",
        "mime_type": "",
        "created_by": created_by,
        **derived,
    }
    update_cols = {k: v for k, v in values.items() if k not in ("blueprint_agent_id", "end_user_id", "path")}
    stmt = (
        pg_insert(UserFile)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["blueprint_agent_id", "end_user_id", "path"],
            set_=update_cols,
        )
        .returning(UserFile)
    )
    result = await session.execute(stmt)
    await session.commit()
    return _row_to_dict(result.scalar_one())


async def rm(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    end_user_id: str, path: str
) -> None:
    stmt = (
        delete(UserFile)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.end_user_id == end_user_id, UserFile.path == path,
        )
    )
    await session.execute(stmt)
    await session.commit()


async def rm_rf(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    end_user_id: str, path: str
) -> int:
    """Delete a directory and everything under it."""
    stmt1 = (
        delete(UserFile)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.end_user_id == end_user_id, UserFile.path.like(f"{path}/%"),
        )
        .returning(UserFile.id)
    )
    stmt2 = (
        delete(UserFile)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.end_user_id == end_user_id, UserFile.path == path,
        )
        .returning(UserFile.id)
    )
    r1 = await session.execute(stmt1)
    r2 = await session.execute(stmt2)
    await session.commit()
    return len(r1.all()) + len(r2.all())


async def stat(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    end_user_id: str, path: str
) -> Optional[Dict[str, Any]]:
    stmt = (
        select(
            UserFile.id, UserFile.path, UserFile.name, UserFile.type,
            UserFile.mime_type, UserFile.size_bytes, UserFile.file_class,
            UserFile.created_by, UserFile.created_at, UserFile.updated_at,
        )
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.end_user_id == end_user_id, UserFile.path == path,
        )
    )
    result = await session.execute(stmt)
    row = result.mappings().first()
    return dict(row) if row else None


async def exists(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    end_user_id: str, path: str
) -> bool:
    stmt = (
        select(UserFile.id)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.end_user_id == end_user_id, UserFile.path == path,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def tree(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    end_user_id: str, root: str = "/"
) -> List[Dict[str, Any]]:
    """Flat list of all nodes under root, ordered by path."""
    stmt = (
        select(UserFile.path, UserFile.name, UserFile.type, UserFile.file_class)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.end_user_id == end_user_id,
        )
    )
    if root != "/":
        stmt = stmt.where(UserFile.path.like(f"{root}/%"))
    stmt = stmt.order_by(UserFile.path)
    result = await session.execute(stmt)
    return [dict(r) for r in result.mappings()]


async def get_user_files(
    session: AsyncSession, blueprint_agent_id: uuid.UUID, end_user_id: str
) -> List[Dict[str, Any]]:
    """Get all files for a specific end user."""
    stmt = (
        select(UserFile.path, UserFile.name, UserFile.content, UserFile.file_class)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.end_user_id == end_user_id, UserFile.type == "file",
        )
    )
    result = await session.execute(stmt)
    return [dict(r) for r in result.mappings()]


async def delete_files(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    end_user_id: str, paths: Optional[List[str]] = None
) -> int:
    """Delete user files. If paths given, only those; else all for the user."""
    stmt = (
        delete(UserFile)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.end_user_id == end_user_id,
        )
        .returning(UserFile.id)
    )
    if paths:
        stmt = stmt.where(UserFile.path.in_(paths))
    result = await session.execute(stmt)
    await session.commit()
    return len(result.all())
