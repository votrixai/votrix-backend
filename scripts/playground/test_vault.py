"""
Vault approach test: ONE shared agent + per-user vault with Composio credentials.

Previous failure: URL had both ?api_key=xxx AND vault injected Bearer {api_key} → conflict.
Fix: remove api_key from URL, let vault inject it as bearer token only.

Three variants tested (controlled by --variant):
  A  base URL only (no query params) + vault bearer → tests if API key alone routes user
  B  URL with ?user_id only + vault bearer          → tests split: vault=auth, URL=user routing
  C  URL with ?user_id + ?api_key (no vault)        → reference baseline, known to work

Run from votrix-backend/:
    python scripts/test_vault.py --variant B   # recommended first
    python scripts/test_vault.py --variant A
    python scripts/test_vault.py --force       # re-create agent/env/vault
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import anthropic
import httpx
from dotenv import load_dotenv

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────────────────

_DIR = Path(__file__).parent
_CACHE_FILE = _DIR / ".vault_test_cache.json"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY", "")

# Composio MCP server ID (org-level, shared)
COMPOSIO_SERVER_ID = "5a629a28-ec72-4601-b192-cf705ecc6d01"

# ── URL variants ──────────────────────────────────────────────────────────────

_BASE = f"https://backend.composio.dev/v3/mcp/{COMPOSIO_SERVER_ID}/mcp"
TEST_USER_ID = "votrix-claude-managed-agent-test"

# Variant A: no query params — vault bearer token alone, Composio must infer user from token
COMPOSIO_URL_A = _BASE

# Variant B: user_id in URL (user routing), NO api_key — vault injects bearer for auth
COMPOSIO_URL_B = f"{_BASE}?user_id={TEST_USER_ID}"

# Variant C: both in URL, no vault — baseline known to work
COMPOSIO_URL_C = f"{_BASE}?user_id={TEST_USER_ID}&api_key={COMPOSIO_API_KEY}"

VARIANTS = {"A": COMPOSIO_URL_A, "B": COMPOSIO_URL_B, "C": COMPOSIO_URL_C}

_STREAM_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)
TEST_MESSAGE = "What Gmail tools do you have access to? List them briefly."


# ─── Cache helpers ────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    return json.loads(_CACHE_FILE.read_text()) if _CACHE_FILE.exists() else {}


def _save_cache(data: dict) -> None:
    _CACHE_FILE.write_text(json.dumps(data, indent=2))


# ─── Step 1: Shared agent (no user_id in MCP URL) ────────────────────────────

def get_or_create_agent(client: anthropic.Anthropic, mcp_url: str, force: bool = False) -> str:
    cache = _load_cache()
    # Bust cache if URL changed (variant switch)
    if not force and cache.get("agent_id") and cache.get("agent_mcp_url") == mcp_url:
        print(f"[agent]  {cache['agent_id']} (cached, url={mcp_url})")
        return cache["agent_id"]

    print(f"[agent]  creating shared agent...")
    print(f"[agent]  mcp_url = {mcp_url}")
    agent = client.beta.agents.create(
        name="vault-test-agent",
        model="claude-sonnet-4-6",
        system=(
            "You are a Gmail assistant. "
            "You can search, read, and draft emails on behalf of the user. "
            "Always confirm before sending."
        ),
        mcp_servers=[
            {"type": "url", "name": "composio_gmail", "url": mcp_url}
        ],
        tools=[
            {
                "type": "agent_toolset_20260401",
                "default_config": {"permission_policy": {"type": "always_allow"}},
            },
            {
                "type": "mcp_toolset",
                "mcp_server_name": "composio_gmail",
                "default_config": {"permission_policy": {"type": "always_allow"}},
            },
        ],
    )
    cache["agent_id"] = agent.id
    cache["agent_mcp_url"] = mcp_url
    _save_cache(cache)
    print(f"[agent]  {agent.id} (created v{agent.version})")
    return agent.id


# ─── Step 2: Environment ──────────────────────────────────────────────────────

def get_or_create_env(client: anthropic.Anthropic, force: bool = False) -> str:
    cache = _load_cache()
    if not force and cache.get("env_id"):
        print(f"[env]    {cache['env_id']} (cached)")
        return cache["env_id"]

    print("[env]    creating environment...")
    env = client.beta.environments.create(
        name="vault-test-env",
        config={"type": "cloud"},
    )
    cache["env_id"] = env.id
    _save_cache(cache)
    print(f"[env]    {env.id} (created)")
    return env.id


# ─── Step 3: Per-user vault ───────────────────────────────────────────────────

def get_or_create_vault(client: anthropic.Anthropic, mcp_url: str, force: bool = False) -> str:
    """
    Vault holds the Composio API key as a static bearer credential.
    The mcp_server_url must match the agent's mcp_servers[].url EXACTLY
    for Anthropic to inject the token when connecting.

    Anthropic injects: Authorization: Bearer {COMPOSIO_API_KEY}
    """
    cache = _load_cache()
    if not force and cache.get("vault_id") and cache.get("vault_mcp_url") == mcp_url:
        print(f"[vault]  {cache['vault_id']} (cached)")
        return cache["vault_id"]

    print(f"[vault]  creating vault...")
    vault = client.beta.vaults.create(
        display_name="vault-test-composio",
        metadata={"user_id": TEST_USER_ID},
    )
    print(f"[vault]  {vault.id} (created)")

    # mcp_server_url must match agent's URL exactly — this is how Anthropic matches credentials
    print(f"[cred]   adding static_bearer → mcp_server_url={mcp_url}")
    cred = client.beta.vaults.credentials.create(
        vault.id,
        display_name="composio-api-key",
        auth={
            "type": "static_bearer",
            "token": COMPOSIO_API_KEY,   # Composio API key → injected as Authorization: Bearer
            "mcp_server_url": mcp_url,  # must match agent URL exactly
        },
    )
    print(f"[cred]   {cred.id} (created)")

    cache["vault_id"] = vault.id
    cache["cred_id"] = cred.id
    cache["vault_mcp_url"] = mcp_url
    _save_cache(cache)
    return vault.id


# ─── Step 4: Chat via session + vault ─────────────────────────────────────────

_SENTINEL = object()


def _stream_in_thread(
    client: anthropic.Anthropic,
    agent_id: str,
    env_id: str,
    vault_id: str | None,
    message: str,
    out: queue.Queue,
) -> None:
    try:
        kwargs = {"agent": agent_id, "environment_id": env_id}
        if vault_id:
            kwargs["vault_ids"] = [vault_id]
        print(f"[session] creating{' with vault' if vault_id else ' (no vault)'}...")
        session = client.beta.sessions.create(**kwargs)
        print(f"[session] {session.id}")

        idle = False
        first = True
        while not idle:
            with client.beta.sessions.events.stream(
                session.id, timeout=_STREAM_TIMEOUT
            ) as stream:
                if first:
                    client.beta.sessions.events.send(
                        session.id,
                        events=[{"type": "user.message", "content": [{"type": "text", "text": message}]}],
                    )
                    first = False

                for event in stream:
                    match event.type:
                        case "agent.message":
                            for block in event.content:
                                if block.type == "text" and block.text:
                                    out.put({"type": "token", "content": block.text})
                        case "agent.mcp_tool_use":
                            out.put({"type": "tool_start", "name": getattr(event, "name", "?")})
                        case "agent.mcp_tool_result":
                            out.put({"type": "tool_end"})
                        case "session.status_idle":
                            out.put({"type": "done"})
                            idle = True
                            break
                        case "session.error" | "error":
                            out.put({"type": "error", "message": str(event)})
                            idle = True
                            break

            if not idle:
                time.sleep(1)

    except Exception as exc:
        out.put({"type": "error", "message": str(exc)})
    finally:
        out.put(_SENTINEL)


def run_chat(client: anthropic.Anthropic, agent_id: str, env_id: str, vault_id: str | None, message: str) -> None:
    print(f"\n{'─'*60}")
    print(f"[chat]   agent  : {agent_id}")
    print(f"[chat]   env    : {env_id}")
    print(f"[chat]   vault  : {vault_id or '(none)'}")
    print(f"[chat]   message: {message}")
    print(f"{'─'*60}\n")

    out: queue.Queue = queue.Queue()
    t = threading.Thread(
        target=_stream_in_thread,
        args=(client, agent_id, env_id, vault_id, message, out),
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
                print(f"[done]   elapsed={elapsed:.1f}s")
                print(f"{'─'*60}")
            case "error":
                print(f"\n[ERROR] {event['message']}", file=sys.stderr)
                print(f"\n{'─'*60}")
                print("RESULT: Vault approach FAILED — Composio likely doesn't accept bearer token.")
                print("Fallback needed: per-user agents with ?user_id= in MCP URL.")
                print(f"{'─'*60}")

    t.join(timeout=5)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force",   action="store_true", help="Re-create agent/env/vault")
    parser.add_argument("--message", default=TEST_MESSAGE, help="Test message to send")
    parser.add_argument(
        "--variant", choices=["A", "B", "C"], default="B",
        help=(
            "A = base URL only (vault auth, no user_id in URL)\n"
            "B = user_id in URL + vault auth (no api_key in URL) [default]\n"
            "C = user_id + api_key in URL, no vault [baseline]"
        ),
    )
    args = parser.parse_args()

    if not ANTHROPIC_API_KEY.strip() or not COMPOSIO_API_KEY.strip():
        print(
            "Missing ANTHROPIC_API_KEY or COMPOSIO_API_KEY. "
            "Set them in .env (see .env.example) or the environment.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    mcp_url = VARIANTS[args.variant]
    print(f"\n[variant {args.variant}] mcp_url = {mcp_url}\n")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    agent_id = get_or_create_agent(client, mcp_url, force=args.force)
    env_id   = get_or_create_env(client, force=args.force)

    if args.variant in ("A", "B"):
        vault_id = get_or_create_vault(client, mcp_url, force=args.force)
        run_chat(client, agent_id, env_id, vault_id, args.message)
    else:
        # Variant C: no vault, baseline test
        print("[variant C] skipping vault — using URL-embedded credentials")
        run_chat(client, agent_id, env_id, vault_id=None, message=args.message)
