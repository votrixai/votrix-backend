"""
Downloadable-file tool — given a file_id produced by code execution,
retrieve its metadata from the Anthropic Files API so the frontend can
offer a download link.
"""

from __future__ import annotations

import asyncio
import logging

from app.client import get_client

logger = logging.getLogger(__name__)

_BETA = ["files-api-2025-04-14"]

DEFINITIONS = [
    {
        "type": "custom",
        "name": "create_downloadable_file",
        "description": (
            "Make a file created by code execution available for the user to download. "
            "Call this AFTER writing a file via code execution. "
            "Pass the file_id that code execution returned."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "The file_id returned by code execution after writing a file.",
                },
            },
            "required": ["file_id"],
        },
    },
]


async def handle(name: str, input: dict, user_id: str) -> dict:
    file_id = input.get("file_id", "")
    if not file_id:
        return {"error": "file_id is required"}

    try:
        client = get_client()
        meta = await asyncio.to_thread(
            client.beta.files.retrieve_metadata, file_id, betas=_BETA,
        )
        filename = getattr(meta, "filename", file_id)
        mime_type = getattr(meta, "mime_type", None) or "application/octet-stream"
        downloadable = bool(getattr(meta, "downloadable", False))

        if not downloadable:
            return {"error": f"File {file_id} is not downloadable. Only files created by code execution are downloadable."}

        return {
            "file_id": file_id,
            "filename": filename,
            "mime_type": mime_type,
        }
    except Exception as exc:
        logger.exception("create_downloadable_file failed for file_id=%s", file_id)
        return {"error": str(exc)}
