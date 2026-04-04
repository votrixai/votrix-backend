#!/usr/bin/env python3
"""Exercise POST /agents/{agent_id}/chat (SSE) against a running backend.

Requires: server on BASE_URL (default http://127.0.0.1:8000), valid agent UUID.

Usage:
  export AGENT_ID=39d82133-e14d-426f-adce-7b7972268dab
  python scripts/test_chat_sse.py

  # Or pass explicitly:
  python scripts/test_chat_sse.py --agent-id <uuid> --message "hello"

Environment:
  BASE_URL   — API root (default http://127.0.0.1:8000)
  AGENT_ID   — blueprint agent UUID
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Stream chat SSE from votrix-backend")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BASE_URL", "http://127.0.0.1:8000"),
        help="API base URL",
    )
    parser.add_argument(
        "--agent-id",
        default=os.environ.get("AGENT_ID", ""),
        help="Agent UUID (or set AGENT_ID)",
    )
    parser.add_argument("--message", default="Say hello in one short sentence.", help="User message")
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Overall request timeout in seconds",
    )
    args = parser.parse_args()

    if not args.agent_id:
        print("error: provide --agent-id or set AGENT_ID", file=sys.stderr)
        return 2

    try:
        uuid.UUID(args.agent_id)
    except ValueError:
        print("error: agent_id must be a UUID", file=sys.stderr)
        return 2

    user_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    url = f"{args.base_url.rstrip('/')}/agents/{args.agent_id}/chat"
    payload = {
        "user_id": user_id,
        "session_id": session_id,
        "message": args.message,
    }

    print(f"POST {url}", file=sys.stderr)
    print(f"payload user_id={user_id} session_id={session_id}", file=sys.stderr)

    try:
        with httpx.Client(timeout=args.timeout) as client:
            with client.stream(
                "POST",
                url,
                json=payload,
                headers={
                    "Accept": "text/event-stream",
                    "Content-Type": "application/json",
                },
            ) as resp:
                resp.raise_for_status()
                buf = ""
                for chunk in resp.iter_text():
                    buf += chunk
                    while "\n\n" in buf:
                        line, buf = buf.split("\n\n", 1)
                        for part in line.split("\n"):
                            if part.startswith("data:"):
                                raw = part[5:].strip()
                                if not raw:
                                    continue
                                try:
                                    obj = json.loads(raw)
                                except json.JSONDecodeError:
                                    print(raw)
                                    continue
                                print(json.dumps(obj, ensure_ascii=False))
                                if obj.get("type") in ("done", "error"):
                                    return 0 if obj.get("type") == "done" else 1
                print("(stream ended without done/error event)", file=sys.stderr)
                return 0
    except httpx.HTTPStatusError as e:
        print(f"HTTP {e.response.status_code}: {e.response.text}", file=sys.stderr)
        return 1
    except httpx.RequestError as e:
        print(f"request failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
