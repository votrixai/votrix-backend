"""Blueprint file queries — admin/member-owned virtual filesystem.

Core ops (fast path): ls, read_file, write_file, edit_file, grep, glob
Supporting ops: mkdir, rm, rm_rf, mv, stat, tree
"""

import posixpath
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.blueprint_files import BlueprintFile
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
    session: AsyncSession, org_id: str, agent_id: str, parent: str = "/"
) -> List[Dict[str, Any]]:
    """List directory contents (base files only)."""
    stmt = (
        select(
            BlueprintFile.id, BlueprintFile.path, BlueprintFile.name,
            BlueprintFile.type, BlueprintFile.mime_type, BlueprintFile.size_bytes,
            BlueprintFile.file_class, BlueprintFile.created_by, BlueprintFile.updated_at,
        )
        .where(
            BlueprintFile.org_id == org_id,
            BlueprintFile.agent_id == agent_id,
            BlueprintFile.parent == parent,
        )
        .order_by(BlueprintFile.type.desc(), BlueprintFile.name)
    )
    result = await session.execute(stmt)
    return [dict(r) for r in result.mappings()]


async def read_file(
    session: AsyncSession, org_id: str, agent_id: str, path: str
) -> Optional[Dict[str, Any]]:
    """Read a base file by path."""
    stmt = (
        select(
            BlueprintFile.content, BlueprintFile.mime_type, BlueprintFile.size_bytes,
            BlueprintFile.file_class, BlueprintFile.name, BlueprintFile.type, BlueprintFile.path,
        )
        .where(
            BlueprintFile.org_id == org_id,
            BlueprintFile.agent_id == agent_id,
            BlueprintFile.path == path,
        )
    )
    result = await session.execute(stmt)
    row = result.mappings().first()
    return dict(row) if row else None


async def write_file(
    session: AsyncSession,
    org_id: str,
    agent_id: str,
    path: str,
    content: str,
    mime_type: str = "text/markdown",
    created_by: str = "system",
) -> Dict[str, Any]:
    """Write or upsert a base file."""
    name = posixpath.basename(path)
    derived = _derive_fields(path, name, content)
    values = {
        "org_id": org_id,
        "agent_id": agent_id,
        "path": path,
        "name": name,
        "type": "file",
        "content": content,
        "mime_type": mime_type,
        "created_by": created_by,
        **derived,
    }
    update_cols = {k: v for k, v in values.items() if k not in ("org_id", "agent_id", "path")}
    stmt = (
        pg_insert(BlueprintFile)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["org_id", "agent_id", "path"],
            set_=update_cols,
        )
        .returning(BlueprintFile)
    )
    result = await session.execute(stmt)
    await session.commit()
    return _row_to_dict(result.scalar_one())


async def edit_file(
    session: AsyncSession, org_id: str, agent_id: str, path: str, old_str: str, new_str: str
) -> Optional[Dict[str, Any]]:
    """Replace first occurrence of old_str with new_str in file content."""
    file = await read_file(session, org_id, agent_id, path)
    if not file or old_str not in file["content"]:
        return None
    updated_content = file["content"].replace(old_str, new_str, 1)
    return await write_file(
        session, org_id, agent_id, path, updated_content,
        file.get("mime_type", "text/markdown"),
    )


async def grep(
    session: AsyncSession, org_id: str, agent_id: str,
    pattern: str, case_insensitive: bool = False
) -> List[Dict[str, Any]]:
    """Regex search across all base files. Returns matching paths + lines."""
    stmt = (
        select(BlueprintFile.path, BlueprintFile.name, BlueprintFile.file_class, BlueprintFile.content)
        .where(
            BlueprintFile.org_id == org_id,
            BlueprintFile.agent_id == agent_id,
            BlueprintFile.type == "file",
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
    session: AsyncSession, org_id: str, agent_id: str, pattern: str
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
        .where(
            BlueprintFile.org_id == org_id,
            BlueprintFile.agent_id == agent_id,
        )
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
    session: AsyncSession, org_id: str, agent_id: str,
    path: str, created_by: str = "system"
) -> Dict[str, Any]:
    name = posixpath.basename(path)
    derived = _derive_fields(path, name)
    values = {
        "org_id": org_id,
        "agent_id": agent_id,
        "path": path,
        "name": name,
        "type": "directory",
        "content": "",
        "mime_type": "",
        "created_by": created_by,
        **derived,
    }
    update_cols = {k: v for k, v in values.items() if k not in ("org_id", "agent_id", "path")}
    stmt = (
        pg_insert(BlueprintFile)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["org_id", "agent_id", "path"],
            set_=update_cols,
        )
        .returning(BlueprintFile)
    )
    result = await session.execute(stmt)
    await session.commit()
    return _row_to_dict(result.scalar_one())


async def rm(session: AsyncSession, org_id: str, agent_id: str, path: str) -> None:
    stmt = (
        delete(BlueprintFile)
        .where(BlueprintFile.org_id == org_id, BlueprintFile.agent_id == agent_id, BlueprintFile.path == path)
    )
    await session.execute(stmt)
    await session.commit()


async def rm_rf(session: AsyncSession, org_id: str, agent_id: str, path: str) -> int:
    """Delete a directory and everything under it."""
    stmt1 = (
        delete(BlueprintFile)
        .where(
            BlueprintFile.org_id == org_id,
            BlueprintFile.agent_id == agent_id,
            BlueprintFile.path.like(f"{path}/%"),
        )
        .returning(BlueprintFile.id)
    )
    stmt2 = (
        delete(BlueprintFile)
        .where(BlueprintFile.org_id == org_id, BlueprintFile.agent_id == agent_id, BlueprintFile.path == path)
        .returning(BlueprintFile.id)
    )
    r1 = await session.execute(stmt1)
    r2 = await session.execute(stmt2)
    await session.commit()
    return len(r1.all()) + len(r2.all())


async def mv(
    session: AsyncSession, org_id: str, agent_id: str, old_path: str, new_path: str
) -> None:
    """Move/rename a file or directory. Also updates children."""
    new_name = posixpath.basename(new_path)
    new_derived = _derive_fields(new_path, new_name)

    stmt = (
        update(BlueprintFile)
        .where(BlueprintFile.org_id == org_id, BlueprintFile.agent_id == agent_id, BlueprintFile.path == old_path)
        .values(path=new_path, name=new_name, **new_derived)
    )
    await session.execute(stmt)

    children_stmt = (
        select(BlueprintFile.id, BlueprintFile.path, BlueprintFile.name)
        .where(
            BlueprintFile.org_id == org_id,
            BlueprintFile.agent_id == agent_id,
            BlueprintFile.path.like(f"{old_path}/%"),
        )
    )
    children = (await session.execute(children_stmt)).mappings().all()
    for child in children:
        child_new_path = new_path + child["path"][len(old_path):]
        child_derived = _derive_fields(child_new_path, child["name"])
        child_stmt = (
            update(BlueprintFile)
            .where(BlueprintFile.id == child["id"])
            .values(path=child_new_path, **child_derived)
        )
        await session.execute(child_stmt)

    await session.commit()


async def stat(
    session: AsyncSession, org_id: str, agent_id: str, path: str
) -> Optional[Dict[str, Any]]:
    stmt = (
        select(
            BlueprintFile.id, BlueprintFile.path, BlueprintFile.name,
            BlueprintFile.type, BlueprintFile.mime_type, BlueprintFile.size_bytes,
            BlueprintFile.file_class, BlueprintFile.created_by,
            BlueprintFile.created_at, BlueprintFile.updated_at,
        )
        .where(
            BlueprintFile.org_id == org_id,
            BlueprintFile.agent_id == agent_id,
            BlueprintFile.path == path,
        )
    )
    result = await session.execute(stmt)
    row = result.mappings().first()
    return dict(row) if row else None


async def exists(session: AsyncSession, org_id: str, agent_id: str, path: str) -> bool:
    stmt = (
        select(BlueprintFile.id)
        .where(BlueprintFile.org_id == org_id, BlueprintFile.agent_id == agent_id, BlueprintFile.path == path)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def tree(
    session: AsyncSession, org_id: str, agent_id: str, root: str = "/"
) -> List[Dict[str, Any]]:
    """Flat list of all nodes under root, ordered by path."""
    stmt = (
        select(BlueprintFile.path, BlueprintFile.name, BlueprintFile.type, BlueprintFile.file_class)
        .where(BlueprintFile.org_id == org_id, BlueprintFile.agent_id == agent_id)
    )
    if root != "/":
        stmt = stmt.where(BlueprintFile.path.like(f"{root}/%"))
    stmt = stmt.order_by(BlueprintFile.path)
    result = await session.execute(stmt)
    return [dict(r) for r in result.mappings()]


async def get_all_files(session: AsyncSession, org_id: str, agent_id: str) -> List[Dict[str, Any]]:
    """Get all base files (for publish diffing)."""
    stmt = (
        select(BlueprintFile.path, BlueprintFile.name, BlueprintFile.content, BlueprintFile.file_class)
        .where(
            BlueprintFile.org_id == org_id,
            BlueprintFile.agent_id == agent_id,
            BlueprintFile.type == "file",
        )
    )
    result = await session.execute(stmt)
    return [dict(r) for r in result.mappings()]
