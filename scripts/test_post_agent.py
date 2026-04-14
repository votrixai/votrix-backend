"""
Interactive test for post-agent via file-based I/O.

Usage:
    python scripts/test_post_agent.py
    python scripts/test_post_agent.py --force    # re-upload skills
    python scripts/test_post_agent.py --message "..." # single message and exit

How it works:
    - Watches test_input.txt for new lines (append to chat)
    - Streams agent response to test_output.txt and console
    - Ctrl-C to quit

Append a message to start chatting:
    echo "帮我完成 setup，店名叫晨光咖啡" >> scripts/test_input.txt
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

INPUT_FILE  = Path(__file__).parent / "test_input.txt"
OUTPUT_FILE = Path(__file__).parent / "test_output.txt"
_CACHE_FILE = Path(__file__).parent / ".post_agent_cache.json"


def _save_cache(agent_id: str, env_id: str, session_id: str | None = None) -> None:
    import json
    data = {"agent_id": agent_id, "env_id": env_id}
    if session_id:
        data["session_id"] = session_id
    _CACHE_FILE.write_text(json.dumps(data))


def _load_cache() -> tuple[str, str, str | None]:
    import json
    if not _CACHE_FILE.exists():
        return None, None, None
    data = json.loads(_CACHE_FILE.read_text())
    return data.get("agent_id"), data.get("env_id"), data.get("session_id")


# ─── Provision ────────────────────────────────────────────────────────────────

def run_provision(force: bool = False) -> tuple[str, str]:
    """Upload skills + create per-user agent. Returns (agent_id, env_id)."""
    import json
    from app.management import environments, skills, provisioning

    config = json.loads(
        (Path(__file__).parents[1] / "agents" / AGENT_SLUG / "config.json").read_text()
    )
    env_id = config["envId"]

    print(f"\n{'─'*60}\n[skills] uploading for {AGENT_SLUG}\n{'─'*60}")

    skill_ids = skills.get_or_upload_all(config.get("skills", []), force=force)
    for slug, sid in skill_ids.items():
        print(f"  {slug} → {sid}")

    print(f"\n{'─'*60}\n[provision] creating agent for user: {USER_ID}\n{'─'*60}")
    agent_id = provisioning.create_user_agent(AGENT_SLUG, USER_ID, DISPLAY_NAME, force=force)
    print(f"  agent_id → {agent_id}")

    return agent_id, env_id


# ─── Single chat turn ─────────────────────────────────────────────────────────

def chat_turn(message: str, session_id: str, out_file: Path) -> bool:
    """Send one message. Returns True on success, False on rate-limit (caller should retry)."""
    from app.runtime.sessions import _stream_in_thread, _SENTINEL

    sep = "─" * 60

    def emit(text: str, end: str = "\n") -> None:
        print(text, end=end, flush=True)
        with out_file.open("a", encoding="utf-8") as f:
            f.write(text + end)

    emit(f"\n{sep}\n[user] {message}\n{sep}\n")

    q: queue.Queue = queue.Queue()
    t = threading.Thread(
        target=_stream_in_thread,
        args=(message, USER_ID, q, session_id),
        daemon=True,
    )
    t.start()

    t_start = time.perf_counter()
    rate_limited = False
    while True:
        event = q.get()
        if event is _SENTINEL:
            break
        match event["type"]:
            case "token":
                print(event["content"], end="", flush=True)
                with out_file.open("a", encoding="utf-8") as f:
                    f.write(event["content"])
            case "thinking":
                print(".", end="", flush=True)
            case "tool_start":
                emit(f"\n  ↳ [tool: {event['name']}] {event.get('input', '')}")
            case "tool_end":
                output = event.get("output", "")
                emit(f"  ↳ [result] {output[:120]}")
            case "done":
                elapsed = time.perf_counter() - t_start
                emit(f"\n\n{sep}\n[done] {elapsed:.1f}s\n{sep}")
            case "error":
                if "繁忙" in event["message"] or "overloaded" in event["message"].lower():
                    rate_limited = True
                else:
                    emit(f"\n[ERROR] {event['message']}")
                    sys.exit(1)

    t.join(timeout=5)
    return not rate_limited


def chat_turn_with_retry(message: str, agent_id: str, env_id: str, out_file: Path,
                         max_retries: int = 5, retry_wait: int = 15) -> None:
    from app.management.environments import create_session
    for attempt in range(1, max_retries + 1):
        session_id = create_session(agent_id, env_id)
        ok = chat_turn(message, session_id, out_file)
        if ok:
            return
        print(f"\n[rate-limit] attempt {attempt}/{max_retries}, waiting {retry_wait}s...", flush=True)
        time.sleep(retry_wait)
    print("[rate-limit] gave up after max retries", file=sys.stderr)
    sys.exit(1)


# ─── File-watching loop ────────────────────────────────────────────────────────

def watch_loop(agent_id: str, env_id: str, session_id: str | None = None) -> None:
    """Poll test_input.txt; send each new line as a chat message."""
    from app.management.environments import create_session

    INPUT_FILE.touch(exist_ok=True)
    OUTPUT_FILE.touch(exist_ok=True)

    # Track how many lines we've already processed
    with INPUT_FILE.open(encoding="utf-8") as f:
        seen_lines = len(f.readlines())

    def emit_header(text: str) -> None:
        print(text, flush=True)
        with OUTPUT_FILE.open("a", encoding="utf-8") as f:
            f.write(text + "\n")

    if session_id:
        print(f"[resume] reusing session {session_id}", flush=True)
    else:
        session_id = create_session(agent_id, env_id)
        _save_cache(agent_id, env_id, session_id)
    emit_header(f"\n[ready] Watching {INPUT_FILE}")
    emit_header(f"[ready] Output → {OUTPUT_FILE}")
    emit_header(f"[ready] Session {session_id}")
    emit_header(f"[ready] Write a message to test_input.txt to chat. Ctrl-C to quit.\n")

    try:
        while True:
            with INPUT_FILE.open(encoding="utf-8") as f:
                lines = f.readlines()

            new_lines = [l.rstrip("\n") for l in lines[seen_lines:] if l.strip()]
            seen_lines = len(lines)

            for msg in new_lines:
                ok = chat_turn(msg, session_id, OUTPUT_FILE)
                if not ok:
                    # Overloaded — new session and retry
                    wait = 20
                    print(f"\n[overloaded] waiting {wait}s then retrying...", flush=True)
                    time.sleep(wait)
                    session_id = create_session(agent_id, env_id)
                    chat_turn(msg, session_id, OUTPUT_FILE)

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[quit]")


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force",   action="store_true", help="Re-upload skills")
    parser.add_argument("--skip-provision", action="store_true", help="Skip provision, reuse last agent")
    parser.add_argument("--message", default=None, help="Send one message and exit")
    args = parser.parse_args()

    # Provision
    cached_session_id = None
    if args.skip_provision:
        agent_id, env_id, cached_session_id = _load_cache()
        if agent_id:
            print(f"[skip provision] agent_id={agent_id}")
            if cached_session_id:
                print(f"[skip provision] session_id={cached_session_id}")
        else:
            print("[skip provision] no cache found, provisioning...")
            agent_id, env_id = run_provision(force=False)
    else:
        agent_id, env_id = run_provision(force=args.force)
        _save_cache(agent_id, env_id)

    if args.message:
        # Single-shot: always new session
        from app.management.environments import create_session
        session_id = create_session(agent_id, env_id)
        print(f"  session_id → {session_id}")
        chat_turn(args.message, session_id, OUTPUT_FILE)
    else:
        # Watch mode: reuse cached session if available
        watch_loop(agent_id, env_id, session_id=cached_session_id)
