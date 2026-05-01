"""
File tools — download_file, publish_file, upload_file.

All three require the file to be at /mnt/session/outputs/ first.

- download_file:  surfaces the file as a download card in the UI (no upload)
- publish_file:   uploads to Supabase Storage and returns a public URL
- upload_file:    stages to Composio S3 and returns {s3key, name, mimetype}
                  for use in Composio tool calls (LinkedIn, Twitter, etc.)
"""

from __future__ import annotations

import hashlib
from typing import Any

import httpx
import structlog

from app.client import get_async_client
from app.config import get_settings
from app.storage import upload_file as storage_upload

logger = structlog.get_logger()

_BETA = ["files-api-2025-04-14", "managed-agents-2026-04-01"]
_ALLOWED_PREFIX = "/mnt/session/outputs/"
_COMPOSIO_API = "https://backend.composio.dev/api/v3"

DEFINITIONS = [
    {
        "type": "custom",
        "name": "download_file",
        "description": (
            "Surface a file you wrote as a download card in the user's UI. "
            "The file MUST be at /mnt/session/outputs/<filename>. "
            "Call AFTER writing the file. "
            "Three file tools compared: "
            "download_file → shows a download card in the UI, does NOT upload anywhere; "
            "publish_file → uploads to Supabase and returns a public URL, use when an external API needs a URL; "
            "upload_file → stages to Composio S3, use before any Composio tool that takes a file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Full sandbox path, e.g. '/mnt/session/outputs/report.csv'",
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "type": "custom",
        "name": "publish_file",
        "description": (
            "Upload a sandbox file to Supabase and return a public URL. "
            "Use when an external API needs a URL. "
            "The file MUST be at /mnt/session/outputs/<filename>. "
            "Three file tools compared: "
            "publish_file → uploads to Supabase and returns a public URL, use when an external API needs a URL; "
            "upload_file → stages to Composio S3, use before any Composio tool that takes a file; "
            "download_file → shows a download card in the UI, does NOT upload anywhere."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Full sandbox path, e.g. '/mnt/session/outputs/image.png'",
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "type": "custom",
        "name": "upload_file",
        "description": (
            "Stage a sandbox file to Composio's cloud storage and return the s3key "
            "needed for Composio tool calls that accept file parameters (e.g. "
            "LINKEDIN_CREATE_LINKED_IN_POST images, TWITTER_UPLOAD_MEDIA media). "
            "The file MUST be at /mnt/session/outputs/<filename>. "
            "Call AFTER writing the file. "
            "Returns {s3key, name, mimetype} — pass these directly into the Composio tool's file parameter. "
            "Three file tools compared: "
            "upload_file → stages to Composio S3, use before any Composio tool that takes a file; "
            "publish_file → uploads to Supabase and returns a public URL, use when an external API needs a URL; "
            "download_file → shows a download card in the UI, does NOT upload anywhere."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Full sandbox path, e.g. '/mnt/session/outputs/image.jpeg'",
                },
                "toolkit_slug": {
                    "type": "string",
                    "description": "Composio toolkit slug, e.g. 'linkedin', 'gmail', 'slack'",
                },
                "tool_slug": {
                    "type": "string",
                    "description": "Composio tool slug, e.g. 'LINKEDIN_CREATE_LINKED_IN_POST'",
                },
            },
            "required": ["file_path", "toolkit_slug", "tool_slug"],
        },
    },
]


async def _find_file(file_path: str, session_id: str) -> tuple[Any | None, dict | None]:
    if not file_path.startswith(_ALLOWED_PREFIX):
        return None, {
            "error": (
                f"File must be under {_ALLOWED_PREFIX}. Got: {file_path}. "
                f"Write or move the file there first."
            ),
        }

    basename = file_path.rsplit("/", 1)[-1]
    if not basename:
        return None, {"error": "file_path has no filename component"}

    try:
        client = get_async_client()
        page = await client.beta.files.list(scope_id=session_id, betas=_BETA)
        all_files = []
        while True:
            all_files.extend(page.data)
            if not page.has_next_page():
                break
            page = await page.get_next_page()
    except Exception as exc:
        logger.exception("files.list failed for session %s", session_id)
        return None, {"error": f"Failed to list session files: {exc}"}

    match = max(
        (
            f for f in all_files
            if getattr(f, "filename", None) == basename
            and getattr(f, "downloadable", False)
        ),
        key=lambda f: f.created_at,
        default=None,
    )
    if not match:
        return None, {
            "error": (
                f"No downloadable file '{basename}' found in this session. "
                f"Ensure the file was written to {_ALLOWED_PREFIX}{basename}."
            ),
        }
    return match, None


async def _handle_download(input: dict, user_id: str, session_id: str) -> dict:
    file_path = (input.get("file_path") or "").strip()
    if not file_path:
        return {"error": "file_path is required"}
    if not session_id:
        return {"error": "session_id is required"}

    match, err = await _find_file(file_path, session_id)
    if err:
        return err

    return {
        "file_id": match.id,
        "filename": match.filename,
        "mime_type": getattr(match, "mime_type", None) or "application/octet-stream",
    }


async def _handle_publish(input: dict, user_id: str, session_id: str) -> dict:
    file_path = (input.get("file_path") or "").strip()
    if not file_path:
        return {"error": "file_path is required"}
    if not session_id:
        return {"error": "session_id is required"}

    match, err = await _find_file(file_path, session_id)
    if err:
        return err

    try:
        client = get_async_client()
        response = await client.beta.files.download(match.id, betas=_BETA)
        data = await response.read()
    except Exception as exc:
        logger.exception("files.download failed for %s", match.id)
        return {"error": f"Failed to download file from Anthropic: {exc}"}

    mime = getattr(match, "mime_type", None) or "application/octet-stream"
    try:
        url = await storage_upload(data, mime, user_id, match.filename)
    except Exception as exc:
        logger.exception("Supabase upload failed for %s", match.filename)
        return {"error": f"Failed to upload to cloud storage: {exc}"}

    return {"url": url, "filename": match.filename, "mime_type": mime}


async def _handle_upload(input: dict, user_id: str, session_id: str) -> dict:
    file_path = (input.get("file_path") or "").strip()
    toolkit_slug = (input.get("toolkit_slug") or "").strip()
    tool_slug = (input.get("tool_slug") or "").strip()

    if not all([file_path, toolkit_slug, tool_slug, session_id]):
        return {"error": "file_path, toolkit_slug, tool_slug, and session_id are all required"}

    match, err = await _find_file(file_path, session_id)
    if err:
        return err

    filename = match.filename
    mimetype = getattr(match, "mime_type", None) or "application/octet-stream"

    try:
        client = get_async_client()
        response = await client.beta.files.download(match.id, betas=_BETA)
        data = await response.read()
    except Exception as exc:
        logger.exception("Failed to download file %s from Anthropic", match.id)
        return {"error": f"Failed to download file from Anthropic: {exc}"}

    md5 = hashlib.md5(data).hexdigest()

    settings = get_settings()
    headers = {"x-api-key": settings.composio_api_key, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"{_COMPOSIO_API}/files/upload/request",
                headers=headers,
                json={
                    "toolkit_slug": toolkit_slug,
                    "tool_slug": tool_slug,
                    "filename": filename,
                    "mimetype": mimetype,
                    "md5": md5,
                },
            )
        if not r.is_success:
            return {"error": f"Composio file upload request failed: {r.status_code} {r.text}"}
        upload_info = r.json()
    except Exception as exc:
        logger.exception("Composio file upload request failed")
        return {"error": f"Composio file upload request failed: {exc}"}

    s3key = upload_info.get("key")
    presigned_url = upload_info.get("new_presigned_url")
    storage_backend = (upload_info.get("metadata") or {}).get("storage_backend", "s3")

    if not s3key or not presigned_url:
        return {"error": f"Composio upload/request returned unexpected response: {upload_info}"}

    try:
        put_headers = {"Content-Type": mimetype}
        if storage_backend == "azure_blob_storage":
            put_headers["x-ms-blob-type"] = "BlockBlob"

        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.put(presigned_url, content=data, headers=put_headers)

        if r.status_code not in (200, 201):
            return {"error": f"Failed to upload file to Composio storage: HTTP {r.status_code}"}
    except Exception as exc:
        logger.exception("Failed to PUT file to Composio presigned URL")
        return {"error": f"Failed to upload to Composio storage: {exc}"}

    logger.info("upload_file: staged %s → s3key=%s", filename, s3key)
    return {"s3key": s3key, "name": filename, "mimetype": mimetype}


async def handle(name: str, input: dict, user_id: str, session_id: str | None = None) -> dict:
    if name == "download_file":
        return await _handle_download(input, user_id, session_id)
    if name == "publish_file":
        return await _handle_publish(input, user_id, session_id)
    if name == "upload_file":
        return await _handle_upload(input, user_id, session_id)
    return {"error": f"Unknown file tool: {name}"}
