"""
Interactive test for post-agent via file-based I/O.

Usage:
    python scripts/test_post_agent.py
    python scripts/test_post_agent.py --force    # re-upload skills
    python scripts/test_post_agent.py --message "..." # single message and exit
    python scripts/test_post_agent.py --force --attach /path/to/file.png  # attach file to first message
    python scripts/test_post_agent.py --user-id <uuid>  # use specific user (default: first user in DB)

How it works:
    - Watches test_input.txt for new lines (append to chat)
    - Streams agent response to test_output.txt and console
    - Ctrl-C to quit

Append a message to start chatting:
    echo "帮我完成 setup，店名叫晨光咖啡" >> scripts/test_input.txt
"""

from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from app.client import get_async_client
from app.db.engine import session_scope
from app.db.queries import users as users_q
from app.management.agent_files import upload_config_files
from app.management import provisioning, skills
from app.management.environments import create_session
from app.management.memory_stores import get_or_create as get_or_create_memory_store
from app.models.chat import FileAttachment
from app.runtime.sessions import stream as runtime_stream

load_dotenv()

AGENT_SLUG = "post-agent"

INPUT_FILE  = Path(__file__).parent / "test_input.txt"
OUTPUT_FILE = Path(__file__).parent / "test_output.txt"
_CACHE_FILE = Path(__file__).parent / ".post_agent_cache.json"

_BETA = ["files-api-2025-04-14", "managed-agents-2026-04-01"]


async def upload_attachment(filepath: str) -> FileAttachment:
    """Upload a local file to Anthropic Files API and return a FileAttachment."""
    p = Path(filepath)
    if not p.exists():
        print(f"[error] file not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    data = p.read_bytes()
    name = p.name
    mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    client = get_async_client()
    result = await client.beta.files.upload(file=(name, data, mime), betas=_BETA)
    content_type = "image" if mime.startswith("image/") else "document"
    print(f"  [upload] {name} ({len(data)} bytes, {mime}) → {result.id}")
    return FileAttachment(file_id=result.id, content_type=content_type, filename=name)


def _save_cache(agent_id: str, env_id: str, session_id: str | None = None) -> None:
    data = {"agent_id": agent_id, "env_id": env_id}
    if session_id:
        data["session_id"] = session_id
    _CACHE_FILE.write_text(json.dumps(data))


def _load_cache() -> tuple[str, str, str | None]:
    if not _CACHE_FILE.exists():
        return None, None, None
    data = json.loads(_CACHE_FILE.read_text())
    return data.get("agent_id"), data.get("env_id"), data.get("session_id")


# ─── DB helpers ───────────────────────────────────────────────────────────────

async def resolve_user_id(user_id_arg: str | None) -> str:
    """Return user_id: use arg if given, else pick first user from DB."""
    async with session_scope() as db:
        if user_id_arg:
            import uuid as _uuid
            user = await users_q.get_user(db, _uuid.UUID(user_id_arg))
            if not user:
                print(f"[error] user {user_id_arg} not found in DB", file=sys.stderr)
                sys.exit(1)
            print(f"[user] {user.id}  ({user.display_name})")
            return str(user.id)
        users = await users_q.list_users(db)
        if not users:
            print("[error] no users in DB — create one first", file=sys.stderr)
            sys.exit(1)
        user = users[0]
        print(f"[user] picked first user: {user.id}  ({user.display_name})")
        return str(user.id)


# ─── Provision ────────────────────────────────────────────────────────────────

async def run_provision(user_id: str, force: bool = False) -> tuple[str, str]:
    """Upload skills + create per-user agent. Returns (agent_id, env_id)."""
    config = json.loads(
        (Path(__file__).parents[1] / "agents" / AGENT_SLUG / "config.json").read_text()
    )
    env_id = config.get("envId") or ""

    print(f"\n{'─'*60}\n[skills] uploading for {AGENT_SLUG}\n{'─'*60}")

    skill_ids = await skills.get_or_upload_all(config.get("skills", []), force=force)
    for slug, sid in skill_ids.items():
        print(f"  {slug} → {sid}")

    print(f"\n{'─'*60}\n[provision] creating agent for user: {user_id}\n{'─'*60}")
    agent_id = await provisioning.create_user_agent(AGENT_SLUG, user_id)
    print(f"  agent_id → {agent_id}")

    _save_cache(agent_id, env_id, session_id=None)

    return agent_id, env_id


async def create_session_from_agent_config(agent_id: str, env_id: str, user_id: str) -> str:
    """Create a session and mount files + memory store declared in agents/<slug>/config.json."""
    config = json.loads(
        (Path(__file__).parents[1] / "agents" / AGENT_SLUG / "config.json").read_text()
    )
    resources = await upload_config_files(AGENT_SLUG, config.get("files", []))

    memory_config = config.get("memoryConfig")
    async with session_scope() as db:
        import uuid as _uuid
        store_id = await get_or_create_memory_store(db, _uuid.UUID(user_id), AGENT_SLUG, memory_config)
    if store_id:
        resources.append({
            "type": "memory_store",
            "memory_store_id": store_id,
            "access": "read_write",
            "instructions": memory_config["instructions"],
        })
        print(f"  [memory_store] {store_id}")

    return await create_session(agent_id, env_id, resources=resources)


# ─── Single chat turn ─────────────────────────────────────────────────────────

async def chat_turn(message: str, session_id: str, out_file: Path, user_id: str,
                    attachments: list[FileAttachment] | None = None) -> bool:
    """Send one message. Returns True on success, False on rate-limit (caller should retry)."""
    sep = "─" * 60

    def emit(text: str, end: str = "\n") -> None:
        print(text, end=end, flush=True)
        with out_file.open("a", encoding="utf-8") as f:
            f.write(text + end)

    att_info = f" (+{len(attachments)} attachment(s))" if attachments else ""
    emit(f"\n{sep}\n[user] {message}{att_info}\n{sep}\n")

    t_start = time.perf_counter()
    rate_limited = False
    async for event in runtime_stream(session_id, message, user_id, attachments=attachments):
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
                emit(f"  ↳ [result] {output}")
            case "done":
                elapsed = time.perf_counter() - t_start
                emit(f"\n\n{sep}\n[done] {elapsed:.1f}s\n{sep}")
            case "error":
                if "繁忙" in event["message"] or "overloaded" in event["message"].lower():
                    rate_limited = True
                else:
                    emit(f"\n[ERROR] {event['message']}")
                    sys.exit(1)
    return not rate_limited


# ─── File-watching loop ────────────────────────────────────────────────────────

async def watch_loop(agent_id: str, env_id: str, user_id: str,
                     session_id: str | None = None,
                     attach_path: str | None = None) -> None:
    """Poll test_input.txt; send each new line as a chat message."""
    INPUT_FILE.write_text("")
    OUTPUT_FILE.touch(exist_ok=True)
    seen_lines = 0

    pending_attachment: list[FileAttachment] | None = None
    if attach_path:
        att = await upload_attachment(attach_path)
        pending_attachment = [att]

    def emit_header(text: str) -> None:
        print(text, flush=True)
        with OUTPUT_FILE.open("a", encoding="utf-8") as f:
            f.write(text + "\n")

    if session_id:
        print(f"[resume] reusing session {session_id}", flush=True)
    else:
        session_id = await create_session_from_agent_config(agent_id, env_id, user_id)
        _save_cache(agent_id, env_id, session_id)
    emit_header(f"\n[ready] Watching {INPUT_FILE}")
    emit_header(f"[ready] Output → {OUTPUT_FILE}")
    emit_header(f"[ready] Session {session_id}")
    if pending_attachment:
        emit_header(f"[ready] Attachment: {attach_path} (mounted on first message)")
    emit_header(f"[ready] Write a message to test_input.txt to chat. Ctrl-C to quit.\n")

    try:
        while True:
            with INPUT_FILE.open(encoding="utf-8") as f:
                lines = f.readlines()

            new_lines = [l.rstrip("\n") for l in lines[seen_lines:] if l.strip()]
            seen_lines = len(lines)

            for msg in new_lines:
                ok = await chat_turn(msg, session_id, OUTPUT_FILE, user_id, attachments=pending_attachment)
                pending_attachment = None
                if not ok:
                    wait = 20
                    print(f"\n[overloaded] waiting {wait}s then retrying...", flush=True)
                    await asyncio.sleep(wait)
                    session_id = await create_session_from_agent_config(agent_id, env_id, user_id)
                    await chat_turn(msg, session_id, OUTPUT_FILE, user_id)
                INPUT_FILE.write_text("")
                seen_lines = 0

            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n[quit]")


# ─── Entry point ──────────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force",   action="store_true", help="Re-upload skills")
    parser.add_argument("--skip-provision", action="store_true", help="Skip provision, reuse last agent")
    parser.add_argument("--message", default=None, help="Send one message and exit")
    parser.add_argument("--attach",  default=None, help="File path to upload and attach to first message")
    parser.add_argument("--user-id", default=None, help="User UUID (default: first user in DB)")
    args = parser.parse_args()

    user_id = await resolve_user_id(args.user_id)

    cached_session_id = None
    if args.skip_provision:
        agent_id, env_id, cached_session_id = _load_cache()
        if agent_id:
            print(f"[skip provision] agent_id={agent_id}")
            if cached_session_id:
                print(f"[skip provision] session_id={cached_session_id}")
        else:
            print("[skip provision] no cache found, provisioning...")
            agent_id, env_id = await run_provision(user_id, force=False)
    else:
        agent_id, env_id = await run_provision(user_id, force=args.force)
        _save_cache(agent_id, env_id)

    if args.message:
        session_id = await create_session_from_agent_config(agent_id, env_id, user_id)
        print(f"  session_id → {session_id}")
        atts = [await upload_attachment(args.attach)] if args.attach else None
        await chat_turn(args.message, session_id, OUTPUT_FILE, user_id, attachments=atts)
    else:
        await watch_loop(agent_id, env_id, user_id, session_id=cached_session_id, attach_path=args.attach)


if __name__ == "__main__":
    asyncio.run(main())
