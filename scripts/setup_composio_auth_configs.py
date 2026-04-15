"""
One-time setup: create Composio managed auth_configs for all popular toolkits.

Usage:
    python scripts/setup_composio_auth_configs.py           # dry-run (show what would be created)
    python scripts/setup_composio_auth_configs.py --apply   # actually create missing ones

Idempotent: skips toolkits that already have an auth_config.
Only creates Composio-managed OAuth configs (no API_KEY / self-registered).
"""

from __future__ import annotations

import argparse

from dotenv import load_dotenv
import httpx
from app.config import get_settings

load_dotenv()

_API_BASE = "https://backend.composio.dev/api/v3"

# Curated list: popular toolkits where Composio has managed OAuth
MANAGED_TOOLKITS = [
    # Google 全家桶
    "gmail",
    "googlecalendar",
    "googledrive",
    "googlesheets",
    "googledocs",
    "googleslides",
    "googletasks",
    "googlemeet",
    "google_analytics",
    "youtube",

    # 社交媒体
    "facebook",
    "instagram",
    "linkedin",
    "reddit",

    # 团队协作
    "slack",
    "discord",
    "notion",
    "microsoft_teams",

    # 项目管理
    "github",
    "jira",
    "linear",
    "asana",
    "trello",
    "clickup",

    # CRM / 营销
    "hubspot",
    "salesforce",
    "mailchimp",

    # 文件存储
    "dropbox",
    "one_drive",

    # 视频会议
    "zoom",

    # 其他实用
    "stripe",
    "intercom",
    "zendesk",
    "typeform",
    "todoist",
    "figma",
    "canva",
]


def _headers() -> dict:
    return {"x-api-key": get_settings().composio_api_key}


def _get_existing_auth_configs() -> dict[str, list[dict]]:
    """Return {slug: [auth_config, ...]} for all existing auth_configs."""
    result: dict[str, list] = {}
    page = 1
    while True:
        r = httpx.get(f"{_API_BASE}/auth_configs", headers=_headers(),
                      params={"page": page}, timeout=15)
        r.raise_for_status()
        data = r.json()
        for item in data.get("items", []):
            slug = (item.get("toolkit") or {}).get("slug", "")
            if slug:
                result.setdefault(slug, []).append(item)
        if page >= (data.get("total_pages") or 1):
            break
        page += 1
    return result


def _create_auth_config(slug: str) -> str:
    """Create a Composio-managed OAuth2 auth_config. Returns the new auth_config id."""
    r = httpx.post(
        f"{_API_BASE}/auth_configs",
        headers={**_headers(), "Content-Type": "application/json"},
        json={"toolkit": {"slug": slug}, "auth_scheme": "OAUTH2", "use_composio_managed_auth": True},
        timeout=15,
    )
    if not r.is_success:
        raise RuntimeError(f"Failed to create auth_config for '{slug}': {r.status_code} {r.text}")
    return r.json()["auth_config"]["id"]


def main(apply: bool) -> None:
    print(f"\n{'─'*60}")
    print(f"{'[DRY RUN] ' if not apply else ''}Composio auth_config setup")
    print(f"{'─'*60}\n")

    print("Fetching existing auth_configs...")
    existing = _get_existing_auth_configs()
    print(f"Found {sum(len(v) for v in existing.values())} existing auth_configs across {len(existing)} toolkits\n")

    skipped, created, failed = [], [], []

    for slug in MANAGED_TOOLKITS:
        configs = existing.get(slug, [])
        managed = [c for c in configs if c.get("is_composio_managed")]

        if managed:
            print(f"  ✓ {slug:30s} already has managed auth_config ({managed[0]['id']})")
            skipped.append(slug)
            continue

        if not apply:
            print(f"  → {slug:30s} [would create]")
            continue

        try:
            new_id = _create_auth_config(slug)
            print(f"  + {slug:30s} created → {new_id}")
            created.append(slug)
        except Exception as e:
            print(f"  ✗ {slug:30s} FAILED: {e}")
            failed.append(slug)

    print(f"\n{'─'*60}")
    if apply:
        print(f"Done. skipped={len(skipped)}, created={len(created)}, failed={len(failed)}")
        if failed:
            print(f"Failed: {failed}")
    else:
        print(f"Dry run complete. {len(skipped)} already exist, {len(MANAGED_TOOLKITS) - len(skipped)} would be created.")
        print("Run with --apply to create them.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually create missing auth_configs")
    args = parser.parse_args()
    main(apply=args.apply)
