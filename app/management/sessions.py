"""Provider-side session metadata reads.

Thin wrappers around Anthropic's managed-sessions endpoints. Kept here (not in
runtime/) so that when a second provider is introduced, this module is the
natural spot for the `Provider.get_session(...)` seam.
"""

from __future__ import annotations

import logging

from app.client import get_client

logger = logging.getLogger(__name__)


def delete_provider_session(provider_session_id: str) -> None:
    """Best-effort delete of the provider-side session. Logs and swallows errors
    so an orphaned provider record never blocks a local DB delete."""
    try:
        get_client().beta.sessions.delete(provider_session_id)
    except Exception as exc:
        logger.warning("sessions.delete failed [%s]: %s", provider_session_id, exc)
