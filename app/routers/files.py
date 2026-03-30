"""Agent files API — virtual filesystem CRUD.

Routes:
  GET    /orgs/{org_id}/agents/{agent_id}/files              — ls (query: path, end_user_id)
  GET    /orgs/{org_id}/agents/{agent_id}/files/read          — read file (query: path, end_user_id)
  POST   /orgs/{org_id}/agents/{agent_id}/files               — write/create file
  PATCH  /orgs/{org_id}/agents/{agent_id}/files               — edit file (surgical replace)
  DELETE /orgs/{org_id}/agents/{agent_id}/files               — delete file (query: path)
  POST   /orgs/{org_id}/agents/{agent_id}/files/mkdir         — create directory
  POST   /orgs/{org_id}/agents/{agent_id}/files/mv            — move/rename
  GET    /orgs/{org_id}/agents/{agent_id}/files/grep          — regex search (query: pattern)
  GET    /orgs/{org_id}/agents/{agent_id}/files/glob          — glob match (query: pattern)
  GET    /orgs/{org_id}/agents/{agent_id}/files/tree          — full tree (query: root)

When end_user_id is provided, routes target user_files directly.
When absent, routes target blueprint_files.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import blueprint_files, user_files
from app.models.files import (
    EditFileRequest,
    FileContent,
    FileListEntry,
    GrepMatch,
    MkdirRequest,
    MoveRequest,
    TreeEntry,
    WriteFileRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/orgs/{org_id}/agents/{agent_id}/files",
    response_model=List[FileListEntry],
    summary="List directory contents",
)
async def ls(
    org_id: str,
    agent_id: str,
    path: str = Query("/", description="Directory path to list"),
    end_user_id: Optional[str] = Query(None, description="End user ID for user files"),
    session: AsyncSession = Depends(get_session),
):
    if end_user_id:
        entries = await user_files.ls(session, org_id, agent_id, end_user_id, path)
    else:
        entries = await blueprint_files.ls(session, org_id, agent_id, path)
    return [FileListEntry(**e) for e in entries]


@router.get(
    "/orgs/{org_id}/agents/{agent_id}/files/read",
    response_model=FileContent,
    summary="Read file content",
)
async def read_file(
    org_id: str,
    agent_id: str,
    path: str = Query(..., description="File path to read"),
    end_user_id: Optional[str] = Query(None, description="End user ID for user files"),
    session: AsyncSession = Depends(get_session),
):
    if end_user_id:
        file = await user_files.read_file(session, org_id, agent_id, end_user_id, path)
    else:
        file = await blueprint_files.read_file(session, org_id, agent_id, path)
    if not file:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    return FileContent(path=path, **file)


@router.post(
    "/orgs/{org_id}/agents/{agent_id}/files",
    response_model=FileListEntry,
    status_code=201,
    summary="Create or overwrite file",
)
async def write_file(
    org_id: str,
    agent_id: str,
    body: WriteFileRequest,
    end_user_id: Optional[str] = Query(None, description="End user ID (writes to user_files if set)"),
    session: AsyncSession = Depends(get_session),
):
    if end_user_id:
        row = await user_files.write_file(
            session, org_id, agent_id, end_user_id, body.path, body.content,
            mime_type=body.mime_type,
        )
    else:
        row = await blueprint_files.write_file(
            session, org_id, agent_id, body.path, body.content,
            mime_type=body.mime_type,
        )
    return FileListEntry(**row)


@router.patch(
    "/orgs/{org_id}/agents/{agent_id}/files",
    response_model=FileContent,
    summary="Edit file (surgical replace)",
)
async def edit_file(
    org_id: str,
    agent_id: str,
    body: EditFileRequest,
    end_user_id: Optional[str] = Query(None, description="End user ID (edits user file if set)"),
    session: AsyncSession = Depends(get_session),
):
    if end_user_id:
        result = await user_files.edit_file(
            session, org_id, agent_id, end_user_id,
            body.path, body.old_str, body.new_str,
        )
        if not result:
            raise HTTPException(status_code=404, detail=f"File not found or old_str not present: {body.path}")
        file = await user_files.read_file(session, org_id, agent_id, end_user_id, body.path)
    else:
        result = await blueprint_files.edit_file(
            session, org_id, agent_id, body.path, body.old_str, body.new_str,
        )
        if not result:
            raise HTTPException(status_code=404, detail=f"File not found or old_str not present: {body.path}")
        file = await blueprint_files.read_file(session, org_id, agent_id, body.path)
    return FileContent(path=body.path, **file)


@router.delete(
    "/orgs/{org_id}/agents/{agent_id}/files",
    status_code=204,
    summary="Delete file or directory",
)
async def delete_file(
    org_id: str,
    agent_id: str,
    path: str = Query(..., description="Path to delete"),
    recursive: bool = Query(False, description="If true, delete directory and all contents"),
    end_user_id: Optional[str] = Query(None, description="End user ID (deletes from user_files if set)"),
    session: AsyncSession = Depends(get_session),
):
    if end_user_id:
        if recursive:
            count = await user_files.rm_rf(session, org_id, agent_id, end_user_id, path)
            if count == 0:
                raise HTTPException(status_code=404, detail=f"Path not found: {path}")
        else:
            file_exists = await user_files.exists(session, org_id, agent_id, end_user_id, path)
            if not file_exists:
                raise HTTPException(status_code=404, detail=f"File not found: {path}")
            await user_files.rm(session, org_id, agent_id, end_user_id, path)
    else:
        if recursive:
            count = await blueprint_files.rm_rf(session, org_id, agent_id, path)
            if count == 0:
                raise HTTPException(status_code=404, detail=f"Path not found: {path}")
        else:
            file_exists = await blueprint_files.exists(session, org_id, agent_id, path)
            if not file_exists:
                raise HTTPException(status_code=404, detail=f"File not found: {path}")
            await blueprint_files.rm(session, org_id, agent_id, path)


@router.post(
    "/orgs/{org_id}/agents/{agent_id}/files/mkdir",
    response_model=FileListEntry,
    status_code=201,
    summary="Create directory",
)
async def mkdir(
    org_id: str,
    agent_id: str,
    body: MkdirRequest,
    end_user_id: Optional[str] = Query(None, description="End user ID"),
    session: AsyncSession = Depends(get_session),
):
    if end_user_id:
        row = await user_files.mkdir(session, org_id, agent_id, end_user_id, body.path)
    else:
        row = await blueprint_files.mkdir(session, org_id, agent_id, body.path)
    return FileListEntry(**row)


@router.post(
    "/orgs/{org_id}/agents/{agent_id}/files/mv",
    status_code=200,
    summary="Move or rename",
)
async def move(
    org_id: str,
    agent_id: str,
    body: MoveRequest,
    session: AsyncSession = Depends(get_session),
):
    """Move/rename a blueprint file."""
    file_exists = await blueprint_files.exists(session, org_id, agent_id, body.old_path)
    if not file_exists:
        raise HTTPException(status_code=404, detail=f"Source not found: {body.old_path}")
    await blueprint_files.mv(session, org_id, agent_id, body.old_path, body.new_path)
    return {"old_path": body.old_path, "new_path": body.new_path}


@router.get(
    "/orgs/{org_id}/agents/{agent_id}/files/grep",
    response_model=List[GrepMatch],
    summary="Regex search across files",
)
async def grep(
    org_id: str,
    agent_id: str,
    pattern: str = Query(..., description="Regex pattern to search for"),
    case_insensitive: bool = Query(False, description="Case insensitive search"),
    end_user_id: Optional[str] = Query(None, description="End user ID for user files"),
    session: AsyncSession = Depends(get_session),
):
    if end_user_id:
        results = await user_files.grep(
            session, org_id, agent_id, end_user_id, pattern,
            case_insensitive=case_insensitive,
        )
    else:
        results = await blueprint_files.grep(
            session, org_id, agent_id, pattern,
            case_insensitive=case_insensitive,
        )
    return [GrepMatch(**r) for r in results]


@router.get(
    "/orgs/{org_id}/agents/{agent_id}/files/glob",
    response_model=List[FileListEntry],
    summary="Find files by glob pattern",
)
async def glob(
    org_id: str,
    agent_id: str,
    pattern: str = Query(..., description="Glob pattern, e.g. skills/**/*.md or *.json"),
    end_user_id: Optional[str] = Query(None, description="End user ID for user files"),
    session: AsyncSession = Depends(get_session),
):
    if end_user_id:
        results = await user_files.glob(session, org_id, agent_id, end_user_id, pattern)
    else:
        results = await blueprint_files.glob(session, org_id, agent_id, pattern)
    return [FileListEntry(**r) for r in results]


@router.get(
    "/orgs/{org_id}/agents/{agent_id}/files/tree",
    response_model=List[TreeEntry],
    summary="Get file tree",
)
async def tree(
    org_id: str,
    agent_id: str,
    root: str = Query("/", description="Root path for tree"),
    end_user_id: Optional[str] = Query(None, description="End user ID for user files"),
    session: AsyncSession = Depends(get_session),
):
    if end_user_id:
        entries = await user_files.tree(session, org_id, agent_id, end_user_id, root)
    else:
        entries = await blueprint_files.tree(session, org_id, agent_id, root)
    return [TreeEntry(**e) for e in entries]
