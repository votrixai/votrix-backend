"""
End-to-end test: provision the marketing-agent then send a chat message.

Run from votrix-backend/:
    python scripts/test_agent.py
    python scripts/test_agent.py --force     # re-provision even if cached
    python scripts/test_agent.py --no-build  # skip build, just test chat
"""

from __future__ import annotations

import argparse
import queue
import sys
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

from app.build.run import build
from app.runtime.sessions import _SENTINEL, _load_cache, _stream_in_thread

load_dotenv()

AGENT_ID = "marketing-agent"
TEST_MESSAGE = "Hi! Can you help me draft a short email to a potential client introducing our marketing services?"


# ─── Step 1: Build ────────────────────────────────────────────────────────────

def run_build(force: bool = False) -> None:
    print(f"\n{'─'*60}")
    print(f"[build] provisioning {AGENT_ID} (force={force})")
    print(f"{'─'*60}")
    build(AGENT_ID, force=force)


# ─── Step 2: Chat (direct SDK, no HTTP) ───────────────────────────────────────

def run_chat() -> None:
    cache = _load_cache(AGENT_ID)
    print(f"\n{'─'*60}")
    print(f"[chat] agent_id : {cache['agent_id']}")
    print(f"[chat] env_id   : {cache['env_id']}")
    print(f"[chat] message  : {TEST_MESSAGE}")
    print(f"{'─'*60}\n")

    out: queue.Queue = queue.Queue()
    t = threading.Thread(
        target=_stream_in_thread,
        args=(AGENT_ID, TEST_MESSAGE, out),
        daemon=True,
    )
    t.start()

    tokens: list[str] = []
    t_start = time.perf_counter()
    while True:
        event = out.get()
        if event is _SENTINEL:
            break

        match event["type"]:
            case "token":
                print(event["content"], end="", flush=True)
                tokens.append(event["content"])
            case "tool_start":
                print(f"\n  ↳ [tool: {event['name']}]", flush=True)
            case "tool_end":
                print(f"  ↳ [tool result received]", flush=True)
            case "done":
                elapsed = time.perf_counter() - t_start
                print(f"\n\n{'─'*60}")
                print(f"[done] {len(''.join(tokens))} chars in {elapsed:.1f}s")
                print(f"{'─'*60}")
            case "error":
                print(f"\n[ERROR] {event['message']}", file=sys.stderr)
                sys.exit(1)

    t.join(timeout=5)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Force re-provision")
    parser.add_argument("--no-build", action="store_true", help="Skip build step")
    args = parser.parse_args()

    if not args.no_build:
        run_build(force=args.force)

    run_chat()
