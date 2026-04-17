"""Provider-side session metadata reads.

Thin wrappers around Anthropic's managed-sessions endpoints. Kept here (not in
runtime/) so that when a second provider is introduced, this module is the
natural spot for the `Provider.get_session(...)` seam.
"""

from __future__ import annotations

import logging

from app.client import get_client

logger = logging.getLogger(__name__)


def get_provider_session_title(provider_session_id: str) -> str | None:
    """Fetch the provider-assigned session title, or None on failure."""
    try:
        session = get_client().beta.sessions.retrieve(provider_session_id)
    except Exception as exc:
        logger.warning("sessions.retrieve failed [%s]: %s", provider_session_id, exc)
        return None
    return session.title or None
