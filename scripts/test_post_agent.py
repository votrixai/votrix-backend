"""
End-to-end test: provision post-agent for votrix-ai-test, then chat.

Run from votrix-backend/:
    python scripts/test_post_agent.py
    python scripts/test_post_agent.py --force   # re-upload skills even if cached
    python scripts/test_post_agent.py --message "你好，帮我写一篇 Instagram 帖子介绍我们的咖啡厅"
"""

from __future__ import annotations

import argparse
import queue
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from dotenv import load_dotenv
load_dotenv()

AGENT_SLUG   = "post-agent"
USER_ID      = "votrix-ai-test"
DISPLAY_NAME = "Votrix AI Test"
TEST_MESSAGE = "你好！帮我完成 setup，我是一家广州的精品咖啡厅，叫「晨光咖啡」。"


def run_provision(force: bool = False) -> tuple[str, str]:
    """Upload skills + provision per-user agent. Returns (agent_id, env_id)."""
    from app.management import environments, skills, provisioning

    print(f"\n{'─'*60}\n[skills] uploading skills for {AGENT_SLUG}\n{'─'*60}")
    import json
    config = json.loads(
        (Path(__file__).parents[1] / "agents" / AGENT_SLUG / "config.json").read_text()
    )

    if force:
        # Clear registry entries for these skills so they get re-uploaded
        from app.management.skills import _read_registry, _write_registry
        registry = _read_registry()
        for slug in config.get("skills", []):
            if slug in registry:
                del registry[slug]
                print(f"  [skill:{slug}] cleared from registry")
        _write_registry(registry)

    skill_ids = skills.get_or_upload_all(config.get("skills", []))
    for slug, sid in skill_ids.items():
        print(f"  [skill:{slug}] → {sid}")

    print(f"\n{'─'*60}\n[env] getting or creating environment\n{'─'*60}")
    env_id = environments.get_or_create()
    print(f"  env_id → {env_id}")

    print(f"\n{'─'*60}\n[provision] creating agent for user: {USER_ID}\n{'─'*60}")
    agent_id = provisioning.create_user_agent(
        slug=AGENT_SLUG,
        user_id=USER_ID,
        display_name=DISPLAY_NAME,
        composio_user_id=USER_ID,
    )
    print(f"  agent_id → {agent_id}")

    return agent_id, env_id


def run_chat(agent_id: str, env_id: str, message: str) -> None:
    from app.runtime.sessions import create_anthropic_session, _stream_in_thread, _SENTINEL

    print(f"\n{'─'*60}\n[session] creating session\n{'─'*60}")
    session_id = create_anthropic_session(agent_id, env_id)
    print(f"  session_id → {session_id}")

    print(f"\n{'─'*60}")
    print(f"[chat] {message}")
    print(f"{'─'*60}\n")

    out: queue.Queue = queue.Queue()
    t = threading.Thread(
        target=_stream_in_thread,
        args=(message, USER_ID, out, session_id),
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
                print(f"  ↳ [result received]", flush=True)
            case "done":
                elapsed = time.perf_counter() - t_start
                print(f"\n\n{'─'*60}\n[done] {elapsed:.1f}s\n{'─'*60}")
            case "error":
                print(f"\n[ERROR] {event['message']}", file=sys.stderr)
                sys.exit(1)

    t.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force",   action="store_true", help="Re-upload skills even if cached")
    parser.add_argument("--message", default=TEST_MESSAGE, help="Chat message to send")
    args = parser.parse_args()

    agent_id, env_id = run_provision(force=args.force)
    run_chat(agent_id, env_id, args.message)
