"""Provider-side session metadata reads.

Thin wrappers around Anthropic's managed-sessions endpoints. Kept here (not in
runtime/) so that when a second provider is introduced, this module is the
natural spot for the `Provider.get_session(...)` seam.
"""

from __future__ import annotations

import re

import structlog

from app.client import get_async_client

logger = structlog.get_logger()

DEFAULT_SESSION_TITLE = "New Conversation"
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_HEX_ID_RE = re.compile(r"^[0-9a-f]{8,}$", re.IGNORECASE)
_PROVIDER_ID_RE = re.compile(r"^(?:sess|sesn|session|evt|sevt|msg)_[A-Za-z0-9_-]{8,}$")


def usable_provider_title(title: str | None, provider_session_id: str) -> str | None:
    """Return a provider title only when it looks displayable."""
    if not title:
        return None
    cleaned = title.strip()
    if not cleaned:
        return None
    if cleaned == provider_session_id:
        return None
    if (
        _UUID_RE.fullmatch(cleaned)
        or _HEX_ID_RE.fullmatch(cleaned)
        or _PROVIDER_ID_RE.fullmatch(cleaned)
    ):
        return None
    return cleaned


def title_from_message(message: str | None) -> str | None:
    title = (message or "").strip()[:100]
    return title or None


def fallback_session_title(message: str | None) -> str:
    return title_from_message(message) or DEFAULT_SESSION_TITLE


async def get_provider_session_title(provider_session_id: str) -> str | None:
    """Fetch the provider-assigned session title, or None on failure."""
    try:
        session = await get_async_client().beta.sessions.retrieve(provider_session_id)
    except Exception as exc:
        logger.warning("sessions.retrieve failed [%s]: %s", provider_session_id, exc)
        return None
    return usable_provider_title(session.title, provider_session_id)


async def delete_provider_session(provider_session_id: str) -> None:
    """Best-effort delete of the provider-side session. Logs and swallows errors
    so an orphaned provider record never blocks a local DB delete."""
    try:
        await get_async_client().beta.sessions.delete(provider_session_id)
    except Exception as exc:
        logger.warning("sessions.delete failed [%s]: %s", provider_session_id, exc)
