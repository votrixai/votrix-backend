"""
File-based interactive test: provision marketing-agent → chat loop via files.

Usage:
    python scripts/test_email_and_image.py [--force] [--agent-id ID]

    # In another terminal, write a message to trigger a turn:
    echo "Generate a 1:1 coffee brand image for 'Morning Spark'" >> scripts/test_input.txt

Output is appended to scripts/test_output.txt.
The script watches test_input.txt and processes each new line as a user message.
Ctrl-C to stop.
"""

from __future__ import annotations

import argparse
import queue
import sys
import time
import threading
from pathlib import Path

from dotenv import load_dotenv
from app.client import get_client
from app.management import environments, provisioning
from app.management.environments import get_or_create
from app.runtime.sessions import _SENTINEL, _stream_in_thread

load_dotenv()

AGENT_SLUG       = "marketing-agent"
COMPOSIO_USER_ID = "votrix-claude-managed-agent-test"

INPUT_FILE  = Path(__file__).parent / "test_input.txt"
OUTPUT_FILE = Path(__file__).parent / "test_output.txt"


# ── helpers ──────────────────────────────────────────────────────────────────

def _out(text: str) -> None:
    """Append text to the output file and also print to stdout."""
    print(text, end="", flush=True)
    with OUTPUT_FILE.open("a", encoding="utf-8") as f:
        f.write(text)


def provision(display_name: str = "E2E Test User") -> tuple[str, str]:
    _out(f"\n{'─'*60}\n")
    _out(f"[provision] slug={AGENT_SLUG}  composio_user={COMPOSIO_USER_ID}\n")
    _out(f"{'─'*60}\n")

    agent_id = provisioning.create_user_agent(
        slug=AGENT_SLUG,
        user_id=COMPOSIO_USER_ID,
        display_name=display_name,
        composio_user_id=COMPOSIO_USER_ID,
    )
    env_id = environments.get_or_create()

    _out(f"[provision] agent_id = {agent_id}\n")
    _out(f"[provision] env_id   = {env_id}\n")
    return agent_id, env_id


def chat(agent_id: str, env_id: str, message: str, session_id: str | None = None) -> None:
    _out(f"\n{'─'*60}\n")
    _out(f"[user] {message}\n")
    _out(f"{'─'*60}\n\n")

    out: queue.Queue = queue.Queue()
    t = threading.Thread(
        target=_stream_in_thread,
        args=(agent_id, env_id, message, COMPOSIO_USER_ID, out),
        kwargs={"session_id": session_id},
        daemon=True,
    )
    t.start()

    t0 = time.perf_counter()
    while True:
        event = out.get()
        if event is _SENTINEL:
            break
        match event["type"]:
            case "token":
                _out(event["content"])
            case "tool_start":
                _out(f"\n  ↳ [tool: {event['name']}] {event.get('input', '')}\n")
            case "tool_end":
                _out(f"  ↳ [result] {str(event.get('output', ''))[:200]}\n")
            case "done":
                _out(f"\n\n{'─'*60}\n")
                _out(f"[done] {time.perf_counter() - t0:.1f}s\n")
                _out(f"{'─'*60}\n")
            case "error":
                _out(f"\n[ERROR] {event['message']}\n")

    t.join(timeout=5)


# ── main loop ─────────────────────────────────────────────────────────────────

def watch_and_chat(agent_id: str, env_id: str) -> None:
    """
    Tail test_input.txt.  Each non-empty line triggers one chat() call.
    Already-existing lines at startup are skipped.
    A single Anthropic session is shared across all turns for conversation continuity.
    """
    # Ensure input file exists
    INPUT_FILE.touch()

    # Create one session for the whole conversation
    client = get_client()
    session = client.beta.sessions.create(agent=agent_id, environment_id=env_id)
    session_id = session.id

    _out(f"\n[ready] Watching {INPUT_FILE}\n")
    _out(f"[ready] Output → {OUTPUT_FILE}\n")
    _out(f"[ready] Session {session_id}\n")
    _out(f"[ready] Write a message to {INPUT_FILE.name} to chat. Ctrl-C to quit.\n\n")

    # Seek to end so we only react to new lines
    with INPUT_FILE.open("r", encoding="utf-8") as f:
        f.seek(0, 2)  # seek to EOF

        try:
            while True:
                line = f.readline()
                if line:
                    message = line.rstrip("\n")
                    if message.strip():
                        chat(agent_id, env_id, message, session_id=session_id)
                else:
                    time.sleep(0.3)
        except KeyboardInterrupt:
            _out("\n[stopped]\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force",    action="store_true", help="Re-provision agent even if cached")
    parser.add_argument("--agent-id", help="Skip provisioning, use existing agent_id")
    args = parser.parse_args()

    # Clear output file at start
    OUTPUT_FILE.write_text("", encoding="utf-8")

    if args.agent_id:
        agent_id = args.agent_id
        env_id   = get_or_create()
        _out(f"[skip provision] using agent_id={agent_id}\n")
    else:
        agent_id, env_id = provision()

    watch_and_chat(agent_id, env_id)
