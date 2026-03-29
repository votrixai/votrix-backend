"""bootstrap / module / connection handler — setup lifecycle commands."""

import re
from typing import Optional, Dict

from app.db.queries import agents as agents_q
from app.tools.tool_context import get_tool_context


def parse(cmd: str) -> Optional[Dict]:
    """Parse bootstrap/module/connection commands.

    Recognized:
      bootstrap.complete
      module.setup_complete <module_id>
      module.reset <module_id>
      connection.set <connection_id> [value]
      connection.reset <connection_id>
    """
    cmd = cmd.strip()

    # bootstrap.complete / votrix onboard complete
    if re.match(r"^(bootstrap\.complete|votrix\s+onboard\s+complete)$", cmd, re.IGNORECASE):
        return {"action": "bootstrap_complete"}

    # module.setup_complete <id>
    m = re.match(r"^module\.setup_complete\s+(\S+)$", cmd, re.IGNORECASE)
    if m:
        return {"action": "module_setup_complete", "module_id": m.group(1)}

    # module.reset <id>
    m = re.match(r"^module\.reset\s+(\S+)$", cmd, re.IGNORECASE)
    if m:
        return {"action": "module_reset", "module_id": m.group(1)}

    # connection.set <id> [value]
    m = re.match(r"^connection\.set\s+(\S+)(?:\s+(.+))?$", cmd, re.IGNORECASE)
    if m:
        return {"action": "connection_set", "connection_id": m.group(1), "value": m.group(2) or "true"}

    # connection.reset <id>
    m = re.match(r"^connection\.reset\s+(\S+)$", cmd, re.IGNORECASE)
    if m:
        return {"action": "connection_reset", "connection_id": m.group(1)}

    return None


async def run(action: str, **kwargs) -> str:
    ctx = get_tool_context()
    if not ctx:
        return "Error: no context"

    org_id = ctx.org_id
    agent_id = ctx.agent_id

    if action == "bootstrap_complete":
        reg = await agents_q.get_registry(org_id, agent_id)
        reg["bootstrap_complete"] = True
        await agents_q.set_registry(org_id, agent_id, reg)
        return "Bootstrap complete. Agent is now fully configured."

    if action == "module_setup_complete":
        module_id = kwargs["module_id"]
        reg = await agents_q.get_registry(org_id, agent_id)
        modules = reg.setdefault("modules", {})
        modules[module_id] = True
        await agents_q.set_registry(org_id, agent_id, reg)
        return f"Module '{module_id}' marked as set up."

    if action == "module_reset":
        module_id = kwargs["module_id"]
        reg = await agents_q.get_registry(org_id, agent_id)
        modules = reg.get("modules", {})
        modules.pop(module_id, None)
        await agents_q.set_registry(org_id, agent_id, reg)
        return f"Module '{module_id}' reset."

    if action == "connection_set":
        conn_id = kwargs["connection_id"]
        value = kwargs.get("value", "true")
        reg = await agents_q.get_registry(org_id, agent_id)
        connections = reg.setdefault("connections", {})
        connections[conn_id] = value
        await agents_q.set_registry(org_id, agent_id, reg)
        return f"Connection '{conn_id}' set."

    if action == "connection_reset":
        conn_id = kwargs["connection_id"]
        reg = await agents_q.get_registry(org_id, agent_id)
        connections = reg.get("connections", {})
        connections.pop(conn_id, None)
        await agents_q.set_registry(org_id, agent_id, reg)
        return f"Connection '{conn_id}' reset."

    return f"Error: unknown action '{action}'"
