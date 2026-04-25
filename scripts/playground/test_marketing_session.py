"""
End-to-end test: create user → create marketing-agent session → chat.

Run from votrix-backend/:
    python scripts/test_marketing_session.py
    python scripts/test_marketing_session.py --message "帮我起草一封推广邮件"
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx

BASE_URL = "http://127.0.0.1:8000"
TEST_MESSAGE = "你好！介绍一下你自己，你能帮我做什么？"

_client = httpx.Client(trust_env=False, timeout=60.0)


def create_user(display_name: str = "Test User") -> dict:
    r = _client.post(f"{BASE_URL}/users", json={"display_name": display_name})
    r.raise_for_status()
    user = r.json()
    print(f"[user]    {user['id']} ({user['display_name']})")
    return user


def create_session(user_id: str) -> dict:
    r = _client.post(
        f"{BASE_URL}/users/{user_id}/sessions",
        json={"agent_id": "marketing-agent", "display_name": "E2E Test Session"},
        timeout=120.0,
    )
    r.raise_for_status()
    session = r.json()
    print(f"[session] id={session['id']}")
    print(f"[session] provider_session_id={session['session_id']}")
    return session


def chat(user_id: str, session_id: str, message: str) -> None:
    print(f"\n[chat]    sending: {message!r}\n{'─'*60}")
    with httpx.Client(trust_env=False).stream(
        "POST",
        f"{BASE_URL}/agents/marketing-agent/chat",
        json={"user_id": user_id, "session_id": session_id, "message": message},
        timeout=120.0,
    ) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            match event["type"]:
                case "token":
                    print(event["content"], end="", flush=True)
                case "tool_start":
                    print(f"\n  ↳ [tool: {event['name']}] input={event.get('input', {})}", flush=True)
                case "tool_end":
                    print(f"  ↳ [result]: {str(event.get('output', ''))[:120]}", flush=True)
                case "done":
                    print(f"\n{'─'*60}\n[done]")
                case "error":
                    print(f"\n[ERROR] {event['message']}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", default=TEST_MESSAGE)
    args = parser.parse_args()

    user = create_user()
    session = create_session(user["id"])
    chat(user["id"], session["id"], args.message)
