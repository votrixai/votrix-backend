"""Token counting and message trimming utilities.

Used by llm_node (proactive window trimming) and summarize_node (compaction threshold check).
Approximates tokens as len(content) // 4 — avoids a tiktoken dependency while being
accurate enough for threshold decisions (±20%).
"""

from langchain_core.messages import AnyMessage, trim_messages


def count_tokens(messages: list[AnyMessage]) -> int:
    """Approximate token count across a list of messages."""
    total = 0
    for m in messages:
        content = m.content
        if isinstance(content, str):
            total += len(content) // 4
        elif isinstance(content, list):
            # Anthropic-style content blocks: [{"type": "text", "text": "..."}]
            for block in content:
                if isinstance(block, dict):
                    total += len(block.get("text", "")) // 4
        # Add a small fixed overhead per message for role/metadata
        total += 4
    return total


def trim_to_window(messages: list[AnyMessage], max_tokens: int) -> list[AnyMessage]:
    """Trim messages to fit within max_tokens using the 'last' strategy.

    Keeps the most recent messages. Ensures the result starts with a human
    message and ends with a human or tool message (no dangling AI message).
    """
    return trim_messages(
        messages,
        max_tokens=max_tokens,
        token_counter=count_tokens,
        strategy="last",
        start_on="human",
        end_on=("human", "tool"),
        include_system=False,
    )


def is_context_too_long(error: Exception) -> bool:
    """Check if an exception is a context-length error from the LLM provider."""
    msg = str(error).lower()
    patterns = [
        "context_length_exceeded",
        "context window",
        "maximum context",
        "too many tokens",
        "input too long",
        "prompt is too long",
        "exceeds the maximum",
        "reduce your prompt",
    ]
    return any(p in msg for p in patterns)
