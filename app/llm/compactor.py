"""Context compactor — token-based history trimming.

Simplified from ai-core: no votrix_schema dependency, no backend session writes.
Session compaction events are written to Supabase session_events.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage

from app.utils.chat_manager import _estimate_tokens

if TYPE_CHECKING:
    from app.context.assistant_context import AssistantContext

logger = logging.getLogger(__name__)

COMPACT_TRIGGER_TOKENS = 200_000
COMPACT_KEEP_TURNS = 5
EMERGENCY_KEEP_TURNS = 3


def is_context_too_long(e: Exception) -> bool:
    msg = str(e).lower()
    return any(k in msg for k in [
        "context_length_exceeded",
        "context window",
        "too many tokens",
        "request too large",
        "exceeds the limit",
        "tokens limit",
        "reduce the length",
        "input is too long",
    ])


class ContextCompactor:
    """Manages proactive and emergency history compaction."""

    def __init__(self):
        self._last_token_count = 0

    async def run_if_needed(self, ctx: AssistantContext) -> None:
        """Proactive compact: trim if history is too large."""
        cm = ctx.chat_manager
        messages = cm.build_chat_history(token_budget=10_000_000)
        total = sum(_estimate_tokens(m) for m in messages)
        self._last_token_count = total

        if total < COMPACT_TRIGGER_TOKENS:
            return

        logger.info("Proactive compact: %d tokens, trimming to %d turns", total, COMPACT_KEEP_TURNS)
        cm.trim_history_to_turns(keep=COMPACT_KEEP_TURNS)

    async def run_emergency(self, ctx: AssistantContext) -> None:
        """Emergency compact: aggressive trim after API rejection."""
        logger.warning("Emergency compact: trimming to %d turns", EMERGENCY_KEEP_TURNS)
        ctx.chat_manager.trim_history_to_turns(keep=EMERGENCY_KEEP_TURNS)
