"""
End-to-end test: create user → provision agent → chat (send email draft).

Tests the full flow:
  1. Build marketing-agent template (skip if cached)
  2. Create a test user in DB
  3. POST /users/{id}/provision → creates per-user Anthropic agent with Composio MCP
  4. POST /agents/marketing-agent/chat → stream a request to draft an email

Run from votrix-backend/:
    python scripts/test_provision_and_chat.py
    python scripts/test_provision_and_chat.py --force-build   # re-provision template
    python scripts/test_provision_and_chat.py --no-build      # skip template build
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from dotenv import load_dotenv
load_dotenv()

AGENT_SLUG   = "marketing-agent"
TEST_MESSAGE = (
    "Draft a short email to a potential client named John at Acme Corp, "
    "introducing our marketing services. Keep it under 150 words."
)


# ─── Step 1: Build template agent ─────────────────────────────────────────────

def run_build(force: bool = False) -> None:
    from app.management.run import build
    print(f"\n{'─'*60}\n[build] provisioning template: {AGENT_SLUG}\n{'─'*60}")
    build(AGENT_SLUG, force=force)


# ─── Step 2 + 3: Create user + provision per-user agent ───────────────────────

async def run_provision() -> tuple[uuid.UUID, str]:
    """Create test user in DB, then provision their Anthropic agent."""
    from app.db.queries import users as users_q
    from app.management import provisioning

    print(f"\n{'─'*60}\n[provision] creating test user...\n{'─'*60}")

    from app.db.engine import session_scope
    async with session_scope() as db:
        user = await users_q.create_user(
            db,
            display_name="Test User (E2E)",
            agent_slug=AGENT_SLUG,
        )
        print(f"[provision] user created: {user.id}")

    print(f"[provision] provisioning per-user agent...")
    agent_id = provisioning.create_user_agent(
        slug=AGENT_SLUG,
        user_id=str(user.id),
        display_name=user.display_name,
    )
    print(f"[provision] anthropic_agent_id = {agent_id}")

    async with session_scope() as db:
        await users_q.set_anthropic_agent_id(db, user.id, agent_id)
        print(f"[provision] saved to DB")

    return user.id, agent_id


# ─── Step 4: Chat ─────────────────────────────────────────────────────────────

def run_chat(anthropic_agent_id: str, env_id: str) -> None:
    import queue
    import threading
    from app.runtime.sessions import _stream_in_thread, _SENTINEL

    print(f"\n{'─'*60}")
    print(f"[chat] agent_id : {anthropic_agent_id}")
    print(f"[chat] env_id   : {env_id}")
    print(f"[chat] message  : {TEST_MESSAGE}")
    print(f"{'─'*60}\n")

    out: queue.Queue = queue.Queue()
    t = threading.Thread(
        target=_stream_in_thread,
        args=(anthropic_agent_id, env_id, TEST_MESSAGE, out),
        daemon=True,
    )
    t.start()

    t_start = time.perf_counter()
    while True:
        event = out.get()
        if event is _SENTINEL:
            break
        match event["type"]:
            case "token":
                print(event["content"], end="", flush=True)
            case "tool_start":
                print(f"\n  ↳ [tool: {event['name']}]", flush=True)
            case "tool_end":
                print(f"  ↳ [tool result received]", flush=True)
            case "done":
                elapsed = time.perf_counter() - t_start
                print(f"\n\n{'─'*60}")
                print(f"[done] {elapsed:.1f}s")
                print(f"{'─'*60}")
            case "error":
                print(f"\n[ERROR] {event['message']}", file=sys.stderr)
                sys.exit(1)

    t.join(timeout=5)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-build", action="store_true", help="Force re-provision template agent")
    parser.add_argument("--no-build",    action="store_true", help="Skip template build step")
    args = parser.parse_args()

    # Step 1: build template
    if not args.no_build:
        run_build(force=args.force_build)

    # Step 2+3: create user + provision
    user_id, anthropic_agent_id = asyncio.run(run_provision())

    # Read env_id from template cache
    from app.management.agents import _read_cache
    template_cache = _read_cache(AGENT_SLUG)
    env_id = template_cache["env_id"]

    # Step 4: chat
    run_chat(anthropic_agent_id, env_id)
