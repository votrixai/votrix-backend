"""
`download_file` tool — after the agent writes a file in its sandbox
(via `write` or `bash`), it calls this tool with the filename to surface
the file to the user as a download in the UI.

Managed Agents auto-registers every file the sandbox writes as a
session-scoped Files-API entry, so we look the file up by filename/scope
and return its real `file_id`.
"""

from __future__ import annotations

import asyncio
import logging

from app.client import get_client

logger = logging.getLogger(__name__)

_BETA = ["files-api-2025-04-14", "managed-agents-2026-04-01"]

DEFINITIONS = [
    {
        "type": "custom",
        "name": "download_file",
        "description": (
            "Signal that a file you just wrote (via the bash or write tool) is ready for the user to download. "
            "Call this AFTER writing the file to the session filesystem. "
            "Pass the filename only (e.g. 'report.csv') — not the full path. "
            "The backend surfaces the file as a download link in the UI."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Basename of the file you wrote (e.g. 'report.csv'). Must match the saved filename exactly.",
                },
            },
            "required": ["filename"],
        },
    },
]


async def handle(name: str, input: dict, user_id: str, session_id: str | None = None) -> dict:
    filename = (input.get("filename") or "").strip()
    if not filename:
        return {"error": "filename is required"}
    if not session_id:
        return {"error": "session_id is required to look up session-scoped files"}

    # Accept either a basename or a full path; use just the basename for matching.
    basename = filename.rsplit("/", 1)[-1]

    try:
        client = get_client()
        listing = await asyncio.to_thread(
            client.beta.files.list, scope_id=session_id, betas=_BETA,
        )
    except Exception as exc:
        logger.exception("files.list failed for session %s", session_id)
        return {"error": f"Failed to list session files: {exc}"}

    # Pick the most recently created file matching the name.
    match = None
    for f in listing.data:
        if getattr(f, "filename", None) == basename and getattr(f, "downloadable", False):
            if match is None or f.created_at > match.created_at:
                match = f

    if match is None:
        return {
            "error": (
                f"No downloadable file named '{basename}' found in this session. "
                "Write the file with `write` or `bash` first, then call download_file with the exact basename."
            )
        }

    return {
        "file_id": match.id,
        "filename": match.filename,
        "mime_type": getattr(match, "mime_type", None) or "application/octet-stream",
    }
