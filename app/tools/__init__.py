from __future__ import annotations

from app.tools import cron, image

# name → full tool definition dict (used by provisioning to build agents.create() tools list)
TOOL_DEFINITIONS: dict[str, dict] = {
    d["name"]: d
    for module in (cron, image)
    for d in module.DEFINITIONS
}


async def execute(name: str, input: dict, user_id: str) -> dict:
    """Dispatch a custom tool call to the correct handler."""
    if name in ("cron_create", "cron_delete", "cron_list"):
        return await cron.handle(name, input, user_id)
    if name == "image_generate":
        return await image.handle(name, input, user_id)
    return {"error": f"Unknown custom tool: {name}"}
