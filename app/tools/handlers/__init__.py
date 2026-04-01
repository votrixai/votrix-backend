"""
Platform native tool handlers: create_file, str_replace, view.

web_search, web_fetch, bash_tool route through Composio and have no local handler.
"""

import logging
import os
import subprocess
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


async def handle_create_file(
    description: str,
    path: str,
    file_text: str,
) -> Dict:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(file_text)
        return {"status": True, "message": f"Created {path}"}
    except Exception as exc:
        logger.error("create_file failed: %s", exc)
        return {"status": False, "message": str(exc)}


async def handle_str_replace(
    description: str,
    path: str,
    old_str: str,
    new_str: str = "",
) -> Dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        count = content.count(old_str)
        if count == 0:
            return {"status": False, "message": "old_str not found in file"}
        if count > 1:
            return {"status": False, "message": f"old_str appears {count} times — must be unique"}

        with open(path, "w", encoding="utf-8") as f:
            f.write(content.replace(old_str, new_str, 1))

        return {"status": True, "message": f"Replaced in {path}"}
    except Exception as exc:
        logger.error("str_replace failed: %s", exc)
        return {"status": False, "message": str(exc)}


async def handle_view(
    description: str,
    path: str,
    view_range: Optional[List[int]] = None,
) -> Dict:
    try:
        if os.path.isdir(path):
            entries = sorted(os.listdir(path))
            return {"status": True, "entries": entries}

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if view_range:
            start, end = view_range[0] - 1, view_range[1]
            lines = lines[max(0, start):end]

        return {"status": True, "content": "".join(lines)}
    except Exception as exc:
        logger.error("view failed: %s", exc)
        return {"status": False, "message": str(exc)}


# ---------------------------------------------------------------------------
# Lookup table — only tools with local handlers
# ---------------------------------------------------------------------------

PLATFORM_HANDLERS = {
    "create_file": handle_create_file,
    "str_replace":  handle_str_replace,
    "view":         handle_view,
}
