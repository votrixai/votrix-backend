"""
File output tools — download_file and publish_file.

Both tools require the agent to write files to /mnt/session/outputs/ first.
Anthropic Managed Agents auto-registers files in that directory as
session-scoped, downloadable Files API entries.

- download_file: surfaces the file as a download card in the UI (private)
- publish_file:  uploads to Supabase Storage and returns a public URL
"""

from __future__ import annotations

import logging
from typing import Any

from app.client import get_async_client
from app.storage import upload_file as storage_upload

logger = logging.getLogger(__name__)

_BETA = ["files-api-2025-04-14", "managed-agents-2026-04-01"]
_ALLOWED_PREFIX = "/mnt/session/outputs/"

DEFINITIONS = [
    {
        "type": "custom",
        "name": "download_file",
        "description": (
            "Surface a file you wrote as a download card in the user's UI. "
            "The file MUST be at /mnt/session/outputs/<filename>. "
            "Call AFTER writing the file."
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
            "Upload a sandbox file to cloud storage and return a public URL. "
            "Use when you need a URL to pass to external APIs. "
            "The file MUST be at /mnt/session/outputs/<filename>."
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
]


async def _find_file(file_path: str, session_id: str) -> tuple[Any | None, dict | None]:
    """Validate path prefix and look up the file in the Anthropic Files API.

    Returns (file_meta, None) on success or (None, error_dict) on failure.
    """
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
        listing = await client.beta.files.list(scope_id=session_id, betas=_BETA)
    except Exception as exc:
        logger.exception("files.list failed for session %s", session_id)
        return None, {"error": f"Failed to list session files: {exc}"}

    match = max(
        (
            f for f in listing.data
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


async def handle(name: str, input: dict, user_id: str, session_id: str | None = None) -> dict:
    if name == "download_file":
        return await _handle_download(input, user_id, session_id)
    if name == "publish_file":
        return await _handle_publish(input, user_id, session_id)
    return {"error": f"Unknown file tool: {name}"}
