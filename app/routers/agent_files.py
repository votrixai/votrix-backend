"""Blueprint files API — virtual filesystem CRUD.

Routes:
  GET    /agents/{agent_id}/files              — ls
  GET    /agents/{agent_id}/files/read          — read file
  POST   /agents/{agent_id}/files               — write/create file
  PATCH  /agents/{agent_id}/files               — edit file
  DELETE /agents/{agent_id}/files               — delete file
  POST   /agents/{agent_id}/files/mkdir         — create directory
  POST   /agents/{agent_id}/files/mv            — move/rename
  POST   /agents/{agent_id}/files/cp            — copy file or directory
  POST   /agents/{agent_id}/files/bulk-delete   — delete multiple paths
  POST   /agents/{agent_id}/files/bulk-mv       — move/rename multiple paths
  GET    /agents/{agent_id}/files/grep          — regex search
  GET    /agents/{agent_id}/files/glob          — glob match
  GET    /agents/{agent_id}/files/tree          — full tree
"""

from __future__ import annotations

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import blueprint_files
from app.models.files import (
    BulkDeleteRequest,
    BulkMoveRequest,
    CopyRequest,
    EditFileRequest,
    FileContent,
    FileListEntry,
    GrepMatch,
    MkdirRequest,
    MoveRequest,
    TreeEntry,
    WriteFileRequest,
    file_content_from_blueprint,
    file_list_entry_from_blueprint,
    tree_entry_from_blueprint,
)
from app.storage import BUCKET, get_public_url, is_text_mime

logger = logging.getLogger(__name__)

router = APIRouter(tags=["blueprint-files"])

PREFIX = "/agents/{agent_id}/files"

_404 = {404: {"description": "File or path not found"}}


@router.get(PREFIX, response_model=List[FileListEntry], summary="List directory contents")
async def ls(
    agent_id: uuid.UUID,
    path: str = Query("/", description="Directory path to list"),
    session: AsyncSession = Depends(get_session),
):
    """List files and subdirectories at the given path."""
    entries = await blueprint_files.ls(session, agent_id, path)
    return [file_list_entry_from_blueprint(e) for e in entries]


@router.get(f"{PREFIX}/read", response_model=FileContent, summary="Read file content", responses=_404)
async def read_file(
    agent_id: uuid.UUID,
    path: str = Query(..., description="File path to read"),
    session: AsyncSession = Depends(get_session),
):
    """Return the full content and metadata of a single file."""
    file = await blueprint_files.read_file(session, agent_id, path)
    if not file:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    download_url = (
        get_public_url(BUCKET, file.storage_path) if file.storage_path else None
    )
    return file_content_from_blueprint(file, download_url=download_url)


@router.post(PREFIX, response_model=FileListEntry, status_code=201, summary="Create or overwrite file")
async def write_file(
    agent_id: uuid.UUID,
    body: WriteFileRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new file or overwrite an existing one at the given path (text content)."""
    row = await blueprint_files.write_file(
        session, agent_id, body.path, body.content or "",
        mime_type=body.mime_type,
    )
    return file_list_entry_from_blueprint(row)


@router.post(f"{PREFIX}/upload", response_model=FileListEntry, status_code=201, summary="Upload binary file")
async def upload_file(
    agent_id: uuid.UUID,
    path: str = Form(..., description="File path, e.g. /assets/logo.png"),
    mime_type: str = Form("application/octet-stream", description="MIME type"),
    file: UploadFile = File(..., description="Binary file to upload"),
    session: AsyncSession = Depends(get_session),
):
    """Upload a binary file via multipart form data."""
    data = await file.read()
    actual_mime = mime_type or file.content_type or "application/octet-stream"
    row = await blueprint_files.write_file(
        session, agent_id, path,
        mime_type=actual_mime,
        binary_data=data,
    )
    return file_list_entry_from_blueprint(row)


@router.patch(PREFIX, response_model=FileContent, summary="Edit file (surgical replace)", responses=_404)
async def edit_file(
    agent_id: uuid.UUID,
    body: EditFileRequest,
    session: AsyncSession = Depends(get_session),
):
    """Replace a unique string in a file. old_str must appear exactly once."""
    result = await blueprint_files.edit_file(
        session, agent_id, body.path, body.old_str, body.new_str,
    )
    if not result:
        raise HTTPException(status_code=404, detail=f"File not found or old_str not present: {body.path}")
    file = await blueprint_files.read_file(session, agent_id, body.path)
    if not file:
        raise HTTPException(status_code=404, detail=f"File not found: {body.path}")
    download_url = (
        get_public_url(BUCKET, file.storage_path) if file.storage_path else None
    )
    return file_content_from_blueprint(file, download_url=download_url)


@router.delete(PREFIX, status_code=204, summary="Delete file or directory", responses=_404)
async def delete_file(
    agent_id: uuid.UUID,
    path: str = Query(..., description="Path to delete"),
    recursive: bool = Query(False, description="If true, delete directory and all contents"),
    session: AsyncSession = Depends(get_session),
):
    """Delete a file. Pass recursive=true to delete a directory tree."""
    if recursive:
        count = await blueprint_files.rm_rf(session, agent_id, path)
        if count == 0:
            raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    else:
        file_exists = await blueprint_files.exists(session, agent_id, path)
        if not file_exists:
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        await blueprint_files.rm(session, agent_id, path)


@router.post(f"{PREFIX}/mkdir", response_model=FileListEntry, status_code=201, summary="Create directory")
async def mkdir(
    agent_id: uuid.UUID,
    body: MkdirRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a directory entry at the given path."""
    row = await blueprint_files.mkdir(session, agent_id, body.path)
    return file_list_entry_from_blueprint(row)


@router.post(f"{PREFIX}/mv", status_code=200, summary="Move or rename", responses=_404)
async def move(
    agent_id: uuid.UUID,
    body: MoveRequest,
    session: AsyncSession = Depends(get_session),
):
    """Move or rename a file or directory."""
    file_exists = await blueprint_files.exists(session, agent_id, body.old_path)
    if not file_exists:
        raise HTTPException(status_code=404, detail=f"Source not found: {body.old_path}")
    await blueprint_files.mv(session, agent_id, body.old_path, body.new_path)
    return {"old_path": body.old_path, "new_path": body.new_path}


@router.post(f"{PREFIX}/cp", response_model=List[FileListEntry], status_code=201, summary="Copy file or directory")
async def copy(
    agent_id: uuid.UUID,
    body: CopyRequest,
    session: AsyncSession = Depends(get_session),
):
    """Copy a file or directory (including children) to a new path."""
    source_exists = await blueprint_files.exists(session, agent_id, body.source_path)
    if not source_exists:
        raise HTTPException(status_code=404, detail=f"Source not found: {body.source_path}")
    rows = await blueprint_files.cp(session, agent_id, body.source_path, body.dest_path)
    return [file_list_entry_from_blueprint(r) for r in rows]


@router.post(f"{PREFIX}/bulk-delete", status_code=200, summary="Delete multiple files/directories")
async def bulk_delete(
    agent_id: uuid.UUID,
    body: BulkDeleteRequest,
    session: AsyncSession = Depends(get_session),
):
    """Delete multiple paths in a single request."""
    count = await blueprint_files.bulk_delete(session, agent_id, body.paths, recursive=body.recursive)
    return {"deleted": count}


@router.post(f"{PREFIX}/bulk-mv", status_code=200, summary="Move/rename multiple files")
async def bulk_move(
    agent_id: uuid.UUID,
    body: BulkMoveRequest,
    session: AsyncSession = Depends(get_session),
):
    """Move/rename multiple files or directories in a single request."""
    results = []
    for move in body.moves:
        file_exists = await blueprint_files.exists(session, agent_id, move.old_path)
        if not file_exists:
            raise HTTPException(status_code=404, detail=f"Source not found: {move.old_path}")
        await blueprint_files.mv(session, agent_id, move.old_path, move.new_path)
        results.append({"old_path": move.old_path, "new_path": move.new_path})
    return results


@router.get(f"{PREFIX}/grep", response_model=List[GrepMatch], summary="Regex search across files")
async def grep(
    agent_id: uuid.UUID,
    pattern: str = Query(..., description="Regex pattern to search for"),
    case_insensitive: bool = Query(False, description="Case insensitive search"),
    session: AsyncSession = Depends(get_session),
):
    """Search file contents with a regex pattern. Returns matching lines with context."""
    results = await blueprint_files.grep(
        session, agent_id, pattern,
        case_insensitive=case_insensitive,
    )
    return [GrepMatch(**r) for r in results]


@router.get(f"{PREFIX}/glob", response_model=List[FileListEntry], summary="Find files by glob pattern")
async def glob(
    agent_id: uuid.UUID,
    pattern: str = Query(..., description="Glob pattern, e.g. skills/**/*.md or *.json"),
    session: AsyncSession = Depends(get_session),
):
    """Find files matching a glob pattern."""
    results = await blueprint_files.glob(session, agent_id, pattern)
    return [file_list_entry_from_blueprint(r) for r in results]


@router.get(f"{PREFIX}/tree", response_model=List[TreeEntry], summary="Get file tree")
async def tree(
    agent_id: uuid.UUID,
    root: str = Query("/", description="Root path for tree"),
    session: AsyncSession = Depends(get_session),
):
    """Return the full directory tree as a flat list of lightweight entries."""
    entries = await blueprint_files.tree(session, agent_id, root)
    return [tree_entry_from_blueprint(e) for e in entries]
