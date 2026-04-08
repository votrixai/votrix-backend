"""User file queries — end-user's own independent files.

Pure CRUD scoped by ``(blueprint_agent_id, user_account_id)``.
Row-shaped results use ORM :class:`UserFile` (same philosophy as ``blueprint_files``).
``grep`` returns ``FileGrepRow`` dicts. Routers map ORM → ``app.models.files``.
"""

from __future__ import annotations

import posixpath
import re
import secrets
import uuid
from typing import Any, Dict, List, Optional, cast

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.blueprint_files import NodeType
from app.db.models.user_files import UserFile
from app.db.schemas.fs import FileGrepRow
from app.models.files import classify_file
from app.short_id import encode as encode_short_id
from app.storage import BUCKET, is_text_mime, upload_file as storage_upload, delete_file as storage_delete


def _make_storage_path(user_account_id: uuid.UUID, blueprint_agent_id: uuid.UUID, path: str) -> str:
    """Generate an opaque, unguessable storage path for a public bucket.

    Format: ``users/{user_sid}/{agent_sid}{path}_{salt}``. The short-id prefix
    aids debugging; the random salt makes the URL impossible to guess even if
    both UUIDs and the logical path are known.
    """
    user_sid = encode_short_id(user_account_id)
    agent_sid = encode_short_id(blueprint_agent_id)
    salt = secrets.token_urlsafe(8)
    return f"users/{user_sid}/{agent_sid}{path}_{salt}"


def _derive_fields(path: str, name: str, content: str = "", size_bytes: int = 0) -> Dict[str, Any]:
    """Compute derived columns for a file row."""
    return {
        "parent": posixpath.dirname(path) or "/",
        "ext": name.rsplit(".", 1)[-1] if "." in name else "",
        "depth": path.strip("/").count("/") + 1 if path.strip("/") else 0,
        "size_bytes": size_bytes or (len(content.encode("utf-8")) if content else 0),
        "file_class": classify_file(path, name),
    }


async def _ensure_ancestors(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    user_account_id: uuid.UUID, path: str, created_by: str = "system",
) -> None:
    """Auto-create missing ancestor directory rows (mkdir -p)."""
    parts = path.strip("/").split("/")
    for i in range(1, len(parts)):
        ancestor = "/" + "/".join(parts[:i])
        name = parts[i - 1]
        derived = _derive_fields(ancestor, name)
        values = {
            "blueprint_agent_id": blueprint_agent_id,
            "user_account_id": user_account_id,
            "path": ancestor,
            "name": name,
            "type": "directory",
            "content": "",
            "mime_type": "",
            "created_by": created_by,
            **derived,
        }
        stmt = (
            pg_insert(UserFile)
            .values(**values)
            .on_conflict_do_nothing(
                index_elements=["blueprint_agent_id", "user_account_id", "path"]
            )
        )
        await session.execute(stmt)


# ── Core ops ─────────────────────────────────────────────────


async def ls(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    user_account_id: uuid.UUID, parent: str = "/"
) -> List[UserFile]:
    """List directory contents for an end user."""
    stmt = (
        select(UserFile)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.user_account_id == user_account_id,
            UserFile.parent == parent,
        )
        .order_by(UserFile.type.desc(), UserFile.name)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def read_file(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    user_account_id: uuid.UUID, path: str
) -> Optional[UserFile]:
    """Load full user node row (file or directory) by path."""
    stmt = select(UserFile).where(
        UserFile.blueprint_agent_id == blueprint_agent_id,
        UserFile.user_account_id == user_account_id,
        UserFile.path == path,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def write_file(
    session: AsyncSession,
    blueprint_agent_id: uuid.UUID,
    user_account_id: uuid.UUID,
    path: str,
    content: Optional[str] = None,
    mime_type: str = "text/markdown",
    created_by: str = "system",
    binary_data: Optional[bytes] = None,
) -> UserFile:
    """Write or upsert a user file. Text content goes to Postgres, binary to Storage."""
    name = posixpath.basename(path)
    await _ensure_ancestors(session, blueprint_agent_id, user_account_id, path, created_by)

    # Clean up old storage object if overwriting a binary file
    old_storage = (
        await session.execute(
            select(UserFile.storage_path)
            .where(
                UserFile.blueprint_agent_id == blueprint_agent_id,
                UserFile.user_account_id == user_account_id,
                UserFile.path == path,
            )
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
            storage_path = _make_storage_path(user_account_id, blueprint_agent_id, path)
            await storage_upload(BUCKET, storage_path, binary_data, mime_type)
            content = None
            size = len(binary_data)
    else:
        content = content or ""
        size = len(content.encode("utf-8"))

    derived = _derive_fields(path, name, content or "", size_bytes=size)
    values = {
        "blueprint_agent_id": blueprint_agent_id,
        "user_account_id": user_account_id,
        "path": path,
        "name": name,
        "type": "file",
        "content": content,
        "storage_path": storage_path,
        "mime_type": mime_type,
        "created_by": created_by,
        **derived,
    }
    update_cols = {k: v for k, v in values.items() if k not in ("blueprint_agent_id", "user_account_id", "path")}
    stmt = (
        pg_insert(UserFile)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["blueprint_agent_id", "user_account_id", "path"],
            set_=update_cols,
        )
        .returning(UserFile)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.scalar_one()


async def edit_file(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    user_account_id: uuid.UUID, path: str, old_str: str, new_str: str
) -> Optional[UserFile]:
    """Replace first occurrence of old_str with new_str in file content."""
    file = await read_file(session, blueprint_agent_id, user_account_id, path)
    if not file or not file.content or old_str not in file.content:
        return None
    updated_content = file.content.replace(old_str, new_str, 1)
    return await write_file(
        session, blueprint_agent_id, user_account_id, path, updated_content,
        file.mime_type,
    )


async def grep(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    user_account_id: uuid.UUID, pattern: str, case_insensitive: bool = False
) -> List[FileGrepRow]:
    """Regex search across all user files."""
    stmt = (
        select(
            UserFile.path, UserFile.name, UserFile.file_class,
            UserFile.content, UserFile.storage_path,
        )
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.user_account_id == user_account_id,
            UserFile.type == NodeType.file,
        )
    )
    result = await session.execute(stmt)
    flags = re.IGNORECASE if case_insensitive else 0
    compiled = re.compile(pattern, flags)
    results = []
    for row in result.mappings():
        if row["storage_path"] is not None:
            if compiled.search(row["name"]) or compiled.search(row["path"]):
                results.append(
                    cast(
                        FileGrepRow,
                        {
                            "path": row["path"],
                            "name": row["name"],
                            "file_class": row["file_class"],
                            "matches": ["[binary file]"],
                        },
                    )
                )
        else:
            content = row["content"] or ""
            lines = content.split("\n")
            matching = [line for line in lines if compiled.search(line)]
            if matching:
                results.append(
                    cast(
                        FileGrepRow,
                        {
                            "path": row["path"],
                            "name": row["name"],
                            "file_class": row["file_class"],
                            "matches": matching,
                        },
                    )
                )
    return results


async def glob(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    user_account_id: uuid.UUID, pattern: str
) -> List[UserFile]:
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

    stmt = select(UserFile).where(
        UserFile.blueprint_agent_id == blueprint_agent_id,
        UserFile.user_account_id == user_account_id,
    )
    if prefix:
        stmt = stmt.where(UserFile.path.like(f"{prefix}/%"))
    if name_like != "%":
        stmt = stmt.where(UserFile.name.like(name_like))

    stmt = stmt.order_by(UserFile.updated_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ── Supporting ops ───────────────────────────────────────────


async def mkdir(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    user_account_id: uuid.UUID, path: str, created_by: str = "system"
) -> UserFile:
    name = posixpath.basename(path)
    await _ensure_ancestors(session, blueprint_agent_id, user_account_id, path, created_by)

    # Clean up storage if overwriting a binary file with a directory
    old_storage = (
        await session.execute(
            select(UserFile.storage_path)
            .where(
                UserFile.blueprint_agent_id == blueprint_agent_id,
                UserFile.user_account_id == user_account_id,
                UserFile.path == path,
            )
        )
    ).scalar_one_or_none()
    if old_storage:
        await storage_delete(BUCKET, old_storage)

    derived = _derive_fields(path, name)
    values = {
        "blueprint_agent_id": blueprint_agent_id,
        "user_account_id": user_account_id,
        "path": path,
        "name": name,
        "type": "directory",
        "content": "",
        "storage_path": None,
        "mime_type": "",
        "created_by": created_by,
        **derived,
    }
    update_cols = {k: v for k, v in values.items() if k not in ("blueprint_agent_id", "user_account_id", "path")}
    stmt = (
        pg_insert(UserFile)
        .values(**values)
        .on_conflict_do_update(
            index_elements=["blueprint_agent_id", "user_account_id", "path"],
            set_=update_cols,
        )
        .returning(UserFile)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.scalar_one()


async def rm(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    user_account_id: uuid.UUID, path: str
) -> None:
    # Check for storage file to clean up
    check = (
        select(UserFile.storage_path)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.user_account_id == user_account_id, UserFile.path == path,
        )
    )
    row = (await session.execute(check)).scalar_one_or_none()
    if row:
        await storage_delete(BUCKET, row)

    stmt = (
        delete(UserFile)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.user_account_id == user_account_id, UserFile.path == path,
        )
    )
    await session.execute(stmt)
    await session.commit()


async def rm_rf(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    user_account_id: uuid.UUID, path: str
) -> int:
    """Delete a directory and everything under it, including Storage objects."""
    # Collect storage paths to clean up before deleting rows
    storage_stmt = (
        select(UserFile.storage_path)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.user_account_id == user_account_id,
            UserFile.storage_path.is_not(None),
            (UserFile.path == path) | UserFile.path.like(f"{path}/%"),
        )
    )
    storage_rows = (await session.execute(storage_stmt)).scalars().all()
    for sp in storage_rows:
        await storage_delete(BUCKET, sp)

    stmt1 = (
        delete(UserFile)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.user_account_id == user_account_id, UserFile.path.like(f"{path}/%"),
        )
        .returning(UserFile.id)
    )
    stmt2 = (
        delete(UserFile)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.user_account_id == user_account_id, UserFile.path == path,
        )
        .returning(UserFile.id)
    )
    r1 = await session.execute(stmt1)
    r2 = await session.execute(stmt2)
    await session.commit()
    return len(r1.all()) + len(r2.all())


async def mv(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    user_account_id: uuid.UUID, old_path: str, new_path: str
) -> None:
    """Move/rename a user file or directory.

    Only updates the logical ``path`` columns in Postgres. ``storage_path`` is
    opaque and stays put — the public URL remains valid across renames.
    """
    new_name = posixpath.basename(new_path)
    new_derived = _derive_fields(new_path, new_name)

    stmt = (
        update(UserFile)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.user_account_id == user_account_id,
            UserFile.path == old_path,
        )
        .values(path=new_path, name=new_name, **new_derived)
    )
    await session.execute(stmt)

    children_stmt = (
        select(UserFile.id, UserFile.path, UserFile.name)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.user_account_id == user_account_id,
            UserFile.path.like(f"{old_path}/%"),
        )
    )
    children = (await session.execute(children_stmt)).mappings().all()
    for child in children:
        child_new_path = new_path + child["path"][len(old_path):]
        child_derived = _derive_fields(child_new_path, child["name"])
        child_stmt = (
            update(UserFile)
            .where(UserFile.id == child["id"])
            .values(path=child_new_path, **child_derived)
        )
        await session.execute(child_stmt)

    await session.commit()


async def stat(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    user_account_id: uuid.UUID, path: str
) -> Optional[UserFile]:
    stmt = select(UserFile).where(
        UserFile.blueprint_agent_id == blueprint_agent_id,
        UserFile.user_account_id == user_account_id,
        UserFile.path == path,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def exists(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    user_account_id: uuid.UUID, path: str
) -> bool:
    stmt = (
        select(UserFile.id)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.user_account_id == user_account_id, UserFile.path == path,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def tree(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    user_account_id: uuid.UUID, root: str = "/"
) -> List[UserFile]:
    """Flat list of all nodes under root, ordered by path."""
    stmt = select(UserFile).where(
        UserFile.blueprint_agent_id == blueprint_agent_id,
        UserFile.user_account_id == user_account_id,
    )
    if root != "/":
        stmt = stmt.where(UserFile.path.like(f"{root}/%"))
    stmt = stmt.order_by(UserFile.path)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_user_files(
    session: AsyncSession, blueprint_agent_id: uuid.UUID, user_account_id: uuid.UUID
) -> List[UserFile]:
    """Get all file rows (type=file) for a specific end user."""
    stmt = select(UserFile).where(
        UserFile.blueprint_agent_id == blueprint_agent_id,
        UserFile.user_account_id == user_account_id,
        UserFile.type == NodeType.file,
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def delete_files(
    session: AsyncSession, blueprint_agent_id: uuid.UUID,
    user_account_id: uuid.UUID, paths: Optional[List[str]] = None
) -> int:
    """Delete user files. If paths given, only those; else all for the user."""
    # Collect storage paths to clean up
    storage_stmt = (
        select(UserFile.storage_path)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.user_account_id == user_account_id,
            UserFile.storage_path.is_not(None),
        )
    )
    if paths:
        storage_stmt = storage_stmt.where(UserFile.path.in_(paths))
    storage_rows = (await session.execute(storage_stmt)).scalars().all()
    for sp in storage_rows:
        await storage_delete(BUCKET, sp)

    stmt = (
        delete(UserFile)
        .where(
            UserFile.blueprint_agent_id == blueprint_agent_id,
            UserFile.user_account_id == user_account_id,
        )
        .returning(UserFile.id)
    )
    if paths:
        stmt = stmt.where(UserFile.path.in_(paths))
    result = await session.execute(stmt)
    await session.commit()
    return len(result.all())
