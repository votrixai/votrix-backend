from __future__ import annotations

import structlog

from app.integrations.composio import get_async_session_resource
from app.tools import cron, file, image, preview, video

logger = structlog.get_logger()

# name → full tool definition dict (used by provisioning to build agents.create() tools list)
TOOL_DEFINITIONS: dict[str, dict] = {
    d["name"]: d
    for module in (cron, file, image, preview, video)
    for d in module.DEFINITIONS
}


async def execute(
    name: str,
    input: dict,
    user_id: str,
    session_id: str | None = None,
    composio_session_id: str | None = None,
) -> dict:
    """Dispatch a custom tool call to the correct handler."""
    if name in ("cron_create", "cron_delete", "cron_list"):
        return await cron.handle(name, input, user_id, session_id=session_id)
    if name in ("download_file", "publish_file", "upload_file"):
        return await file.handle(name, input, user_id, session_id=session_id)
    if name == "image_generate":
        return await image.handle(name, input, user_id, session_id=session_id)
    if name == "video_generate":
        return await video.handle(name, input, user_id)
    if name == "show_post_preview":
        return await preview.handle(name, input, user_id, session_id=session_id)

    # Composio tool fallback — handles all COMPOSIO_* meta tools and any action slugs
    if composio_session_id:
        try:
            resource = get_async_session_resource()
            result = await resource.execute(
                composio_session_id,
                tool_slug=name,
                arguments=input,
            )
            if result.error:
                return {"error": result.error}
            return result.data if isinstance(result.data, dict) else {"result": result.data}
        except Exception as exc:
            logger.error("composio execute failed [%s]: %s", name, exc)
            return {"error": str(exc)}

    return {"error": f"Unknown custom tool: {name}"}
