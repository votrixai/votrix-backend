"""
Files API proxy — upload/list/delete/download files via Anthropic Files API.

POST   /files                       upload a file → {file_id, filename, size}
GET    /files                       list all files in the workspace
DELETE /files/{file_id}             delete a file
GET    /files/{file_id}/content     download an agent-generated file
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.auth import AuthedUser, require_user
from app.client import get_async_client


def _detect_image_mime(data: bytes, declared: str) -> str:
    """Return the actual image MIME type based on magic bytes, falling back to declared."""
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if len(data) > 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in (b"avif", b"avis"):
            return "image/avif"
        if brand in (b"heic", b"heix", b"hevc", b"hevx"):
            return "image/heic"
    return declared

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

_BETA = ["files-api-2025-04-14", "managed-agents-2026-04-01"]


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str


class FileMetaResponse(BaseModel):
    file_id: str
    filename: str
    created_at: str
    downloadable: bool
    mime_type: str | None = None
    size_bytes: int | None = None


@router.post("", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile,
    _: AuthedUser = Depends(require_user),
):
    data = await file.read()
    mime = file.content_type or "application/octet-stream"
    if mime.startswith("image/"):
        mime = _detect_image_mime(data, mime)
    filename = file.filename or "upload"
    # Anthropic only accepts PDF or plaintext for document blocks;
    # browsers often send octet-stream for text-based extensions.
    _TEXT_EXTS = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".xml", ".html", ".htm"}
    if mime == "application/octet-stream":
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext in _TEXT_EXTS:
            mime = "text/plain"

    client = get_async_client()
    try:
        result = await client.beta.files.upload(
            file=(filename, data, mime),
            betas=_BETA,
        )
    except Exception as e:
        logger.exception("Files API upload failed")
        raise HTTPException(status_code=502, detail=f"Anthropic Files API error: {e}")

    return FileUploadResponse(
        file_id=result.id,
        filename=getattr(result, "filename", filename),
    )


@router.get("", response_model=list[FileMetaResponse])
async def list_files(
    _: AuthedUser = Depends(require_user),
):
    client = get_async_client()
    try:
        result = await client.beta.files.list(betas=_BETA)
    except Exception as e:
        logger.exception("Files API list failed")
        raise HTTPException(status_code=502, detail=f"Anthropic Files API error: {e}")

    return [
        FileMetaResponse(
            file_id=f.id,
            filename=getattr(f, "filename", f.id),
            created_at=str(f.created_at),
            downloadable=bool(getattr(f, "downloadable", False)),
            mime_type=getattr(f, "mime_type", None),
            size_bytes=getattr(f, "size_bytes", None),
        )
        for f in result.data
    ]


@router.delete("/{file_id}", status_code=204)
async def delete_file(
    file_id: str,
    _: AuthedUser = Depends(require_user),
):
    client = get_async_client()
    try:
        await client.beta.files.delete(file_id, betas=_BETA)
    except Exception as e:
        logger.exception("Files API delete failed file_id=%s", file_id)
        raise HTTPException(status_code=502, detail=f"Anthropic Files API error: {e}")


@router.get("/{file_id}/content")
async def download_file(
    file_id: str,
    _: AuthedUser = Depends(require_user),
):
    """Download a file. Only works for agent-generated files — user uploads are
    not downloadable by Anthropic's design (one-way API)."""
    client = get_async_client()
    try:
        meta = await client.beta.files.retrieve_metadata(file_id, betas=_BETA)
        if not getattr(meta, "downloadable", False):
            raise HTTPException(
                status_code=403,
                detail="This file was uploaded by a user and cannot be downloaded. Only agent-generated files are downloadable.",
            )
        response = await client.beta.files.download(file_id, betas=_BETA)
        data = await response.read()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Files API download failed file_id=%s", file_id)
        raise HTTPException(status_code=502, detail=f"Anthropic Files API error: {e}")

    mime = getattr(meta, "mime_type", None) or "application/octet-stream"
    filename = getattr(meta, "filename", file_id)

    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
