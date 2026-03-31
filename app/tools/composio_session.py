"""Composio Tool Router session management.

One Composio client per process (module-level singleton).
Each AI conversation gets a fresh tool_router session with the user's entity_id.
"""

import asyncio
from typing import List

from composio import Composio
from composio_langchain import LangchainProvider

_client: Composio | None = None


def _get_client(api_key: str) -> Composio:
    global _client
    if _client is None:
        _client = Composio(api_key=api_key, provider=LangchainProvider())
    return _client


def _build_tools_sync(api_key: str, user_id: str, toolkits: List[str]) -> list:
    """Sync SDK call — runs in thread pool via asyncio.to_thread."""
    client = _get_client(api_key)
    session = client.tool_router.create(
        user_id=user_id,
        toolkits=toolkits,
        manage_connections={"enable": True},
    )
    return session.tools()


async def get_tools(api_key: str, user_id: str, toolkits: List[str]) -> list:
    """Return LangChain meta-tools for this user + toolkits.

    Composio SDK is sync; we offload to a thread to avoid blocking the event loop.
    Returns the 4 Tool Router meta-tools (SEARCH, EXECUTE, GET_SCHEMAS, MANAGE_CONNECTIONS).
    """
    return await asyncio.to_thread(_build_tools_sync, api_key, user_id, toolkits)
