"""fs handler — ls command via blueprint_files."""

import re
from typing import Optional, Dict

from app.db.queries import blueprint_files
from app.tools.tool_context import get_tool_context


def parse(cmd: str) -> Optional[Dict]:
    """Parse: ls [path]"""
    m = re.match(r"^ls(?:\s+(.+))?$", cmd, re.IGNORECASE)
    if not m:
        return None
    path = (m.group(1) or "/").strip()
    return {"path": path}


async def run(path: str = "/") -> str:
    ctx = get_tool_context()
    if not ctx:
        return "Error: no context"

    entries = await blueprint_files.ls(ctx.db_session, ctx.org_id, ctx.agent_id, path)
    if not entries:
        return f"Directory empty or not found: {path}"

    lines = []
    for e in entries:
        marker = "d" if e["type"] == "directory" else "-"
        lines.append(f"{marker} {e['name']}")
    return "\n".join(lines)
