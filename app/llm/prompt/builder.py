from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.queries import user_files

SYSTEM_PROMPTS_DIR = "/system-prompts"


async def build_system_prompt(
    agent_id: UUID,
    user_id: UUID,
    session: AsyncSession,
) -> list[str]:
    """Load system prompt messages from the /system-prompts virtual folder.

    Each file in /system-prompts becomes one system message, ordered by filename.
    Returns an empty list if the folder doesn't exist or contains no text files.
    """
    nodes = await user_files.ls(session, agent_id, user_id, SYSTEM_PROMPTS_DIR)
    # ls returns (directories first, then files) ordered by name within each type.
    # Filter to text files only (skip directories and binary-only nodes).
    return [
        node.content
        for node in nodes
        if node.type == "file" and node.content
    ]
