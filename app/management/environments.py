from __future__ import annotations

from app.client import get_client


def get_or_create() -> str:
    client = get_client()
    env = client.beta.environments.create(
        name="votrix",
        config={"type": "cloud"},
    )
    return env.id


def create_session(agent_id: str, env_id: str) -> str:
    """Create a new Anthropic session, return its ID. Call once per conversation."""
    client = get_client()
    session = client.beta.sessions.create(agent=agent_id, environment_id=env_id)
    return session.id
