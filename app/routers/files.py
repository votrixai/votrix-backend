"""
Files API proxy — upload/list/delete/download files via Anthropic Files API.

POST   /files                       upload a file → {file_id, filename, size}
GET    /files                       list all files in the workspace
DELETE /files/{file_id}             delete a file
GET    /files/{file_id}/content     download an agent-generated file
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth import AuthedUser, require_user
from app.client import get_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

_BETA = ["files-api-2025-04-14"]


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    size: int


class FileMetaResponse(BaseModel):
    file_id: str
    filename: str
    size: int
    created_at: str


@router.post("", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile,
    _: AuthedUser = Depends(require_user),
):
    data = await file.read()
    mime = file.content_type or "application/octet-stream"
    filename = file.filename or "upload"

    client = get_client()
    try:
        result = client.beta.files.upload(
            file=(filename, data, mime),
            betas=_BETA,
        )
    except Exception as e:
        logger.exception("Files API upload failed")
        raise HTTPException(status_code=502, detail=f"Anthropic Files API error: {e}")

    return FileUploadResponse(
        file_id=result.id,
        filename=result.filename,
        size=result.size,
    )


@router.get("", response_model=list[FileMetaResponse])
async def list_files(
    _: AuthedUser = Depends(require_user),
):
    client = get_client()
    try:
        result = client.beta.files.list(betas=_BETA)
    except Exception as e:
        logger.exception("Files API list failed")
        raise HTTPException(status_code=502, detail=f"Anthropic Files API error: {e}")

    return [
        FileMetaResponse(
            file_id=f.id,
            filename=f.filename,
            size=f.size,
            created_at=str(f.created_at),
        )
        for f in result.data
    ]


@router.delete("/{file_id}", status_code=204)
async def delete_file(
    file_id: str,
    _: AuthedUser = Depends(require_user),
):
    client = get_client()
    try:
        client.beta.files.delete(file_id, betas=_BETA)
    except Exception as e:
        logger.exception("Files API delete failed file_id=%s", file_id)
        raise HTTPException(status_code=502, detail=f"Anthropic Files API error: {e}")


@router.get("/{file_id}/content")
async def download_file(
    file_id: str,
    _: AuthedUser = Depends(require_user),
):
    """Download an agent-generated file (produced by code execution or a skill)."""
    client = get_client()
    try:
        meta = client.beta.files.retrieve_metadata(file_id, betas=_BETA)
        content = client.beta.files.download(file_id, betas=_BETA)
    except Exception as e:
        logger.exception("Files API download failed file_id=%s", file_id)
        raise HTTPException(status_code=502, detail=f"Anthropic Files API error: {e}")

    mime = getattr(meta, "mime_type", None) or "application/octet-stream"
    filename = getattr(meta, "filename", file_id)

    return StreamingResponse(
        content,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
