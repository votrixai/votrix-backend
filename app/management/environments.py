from __future__ import annotations

from app.client import get_async_client


async def get_or_create() -> str:
    client = get_async_client()
    env = await client.beta.environments.create(
        name="votrix",
        config={"type": "cloud"},
    )
    return env.id


async def create_session(
    agent_id: str,
    env_id: str,
    resources: list[dict] | None = None,
) -> str:
    """Create a new Anthropic session, return its ID. Call once per conversation."""
    client = get_async_client()
    session = await client.beta.sessions.create(
        agent=agent_id,
        environment_id=env_id,
        resources=resources or [],
    )
    return session.id
