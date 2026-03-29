"""registry handler — read/write registry fields."""

import json
import re
from typing import Optional, Dict

from app.db.queries import agents as agents_q
from app.tools.tool_context import get_tool_context


def parse(cmd: str) -> Optional[Dict]:
    """Parse: registry.get [field] | registry.set <field> <value>"""
    m = re.match(r"^registry\.get(?:\s+(\S+))?$", cmd, re.IGNORECASE)
    if m:
        return {"action": "get", "field": m.group(1)}

    m = re.match(r"^registry\.set\s+(\S+)\s+(.+)$", cmd, re.IGNORECASE)
    if m:
        return {"action": "set", "field": m.group(1), "value": m.group(2)}

    return None


async def run(action: str, field: Optional[str] = None, value: Optional[str] = None) -> str:
    ctx = get_tool_context()
    if not ctx:
        return "Error: no context"

    org_id = ctx.org_id
    agent_id = ctx.agent_id

    if action == "get":
        reg = await agents_q.get_registry(org_id, agent_id)
        if field:
            return json.dumps(reg.get(field, None), ensure_ascii=False, indent=2)
        return json.dumps(reg, ensure_ascii=False, indent=2)

    if action == "set":
        # Try to parse value as JSON, fallback to string
        try:
            parsed_value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            parsed_value = value
        await agents_q.set_registry_field(org_id, agent_id, field, parsed_value)
        return f"registry.{field} = {value}"

    return f"Error: unknown action '{action}'"
