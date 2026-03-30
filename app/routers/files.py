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
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.db.queries import agent_files
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
    end_user_id: Optional[str] = Query(None, description="End user ID for personalized view"),
):
    entries = await agent_files.ls(org_id, agent_id, path, end_user_id=end_user_id)
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
    end_user_id: Optional[str] = Query(None, description="End user ID for personalized view"),
):
    file = await agent_files.read_file(org_id, agent_id, path, end_user_id=end_user_id)
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
    end_user_id: Optional[str] = Query(None, description="End user ID (creates override if set)"),
):
    # Permission guard: if end_user_id, check the base file allows writes
    if end_user_id:
        base = await agent_files.read_file(org_id, agent_id, body.path)
        if base and base.get("end_user_perm") != "rw":
            raise HTTPException(
                status_code=403,
                detail=f"End user does not have write permission on {body.path}",
            )

    row = await agent_files.write_file(
        org_id, agent_id, body.path, body.content,
        mime_type=body.mime_type,
        end_user_perm=body.end_user_perm,
        end_user_id=end_user_id,
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
    end_user_id: Optional[str] = Query(None, description="End user ID (edits override if set)"),
):
    # Permission guard
    if end_user_id:
        base = await agent_files.read_file(org_id, agent_id, body.path)
        if base and base.get("end_user_perm") != "rw":
            raise HTTPException(
                status_code=403,
                detail=f"End user does not have write permission on {body.path}",
            )

    result = await agent_files.edit_file(
        org_id, agent_id, body.path, body.old_str, body.new_str,
        end_user_id=end_user_id,
    )
    if not result:
        raise HTTPException(status_code=404, detail=f"File not found or old_str not present: {body.path}")
    file = await agent_files.read_file(org_id, agent_id, body.path, end_user_id=end_user_id)
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
):
    """Delete a base file. End user overrides are not deleted here (use conflict resolve)."""
    if recursive:
        count = await agent_files.rm_rf(org_id, agent_id, path)
        if count == 0:
            raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    else:
        file_exists = await agent_files.exists(org_id, agent_id, path)
        if not file_exists:
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        await agent_files.rm(org_id, agent_id, path)


@router.post(
    "/orgs/{org_id}/agents/{agent_id}/files/mkdir",
    response_model=FileListEntry,
    status_code=201,
    summary="Create directory",
)
async def mkdir(org_id: str, agent_id: str, body: MkdirRequest):
    row = await agent_files.mkdir(org_id, agent_id, body.path)
    return FileListEntry(**row)


@router.post(
    "/orgs/{org_id}/agents/{agent_id}/files/mv",
    status_code=200,
    summary="Move or rename",
)
async def move(org_id: str, agent_id: str, body: MoveRequest):
    file_exists = await agent_files.exists(org_id, agent_id, body.old_path)
    if not file_exists:
        raise HTTPException(status_code=404, detail=f"Source not found: {body.old_path}")
    await agent_files.mv(org_id, agent_id, body.old_path, body.new_path)
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
    end_user_id: Optional[str] = Query(None, description="End user ID for personalized view"),
):
    results = await agent_files.grep(
        org_id, agent_id, pattern,
        case_insensitive=case_insensitive,
        end_user_id=end_user_id,
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
    end_user_id: Optional[str] = Query(None, description="End user ID for personalized view"),
):
    results = await agent_files.glob(org_id, agent_id, pattern, end_user_id=end_user_id)
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
    end_user_id: Optional[str] = Query(None, description="End user ID for personalized view"),
):
    entries = await agent_files.tree(org_id, agent_id, root, end_user_id=end_user_id)
    return [TreeEntry(**e) for e in entries]
