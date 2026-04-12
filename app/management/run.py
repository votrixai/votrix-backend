"""
Build script — provision or sync agents into Anthropic.

Usage:
    python -m app.management.run                        # build all agents in agents/
    python -m app.management.run --agent marketing-agent
    python -m app.management.run --agent marketing-agent --force   # ignore cache, re-provision
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.management.agents import provision, sync

AGENTS_DIR = Path(__file__).parents[2] / "agents"


def build(slug: str, force: bool = False) -> None:
    cache = AGENTS_DIR / slug / ".cache.json"
    if force or not cache.exists():
        provision(slug)
    else:
        sync(slug)


def build_all(force: bool = False) -> None:
    slugs = sorted(d.name for d in AGENTS_DIR.iterdir() if d.is_dir())
    if not slugs:
        print("No agents found in agents/")
        return
    for slug in slugs:
        build(slug, force)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision agents into Anthropic")
    parser.add_argument("--agent", metavar="SLUG", help="Agent slug to build (default: all)")
    parser.add_argument("--force", action="store_true", help="Re-provision even if cached")
    args = parser.parse_args()

    if args.agent:
        build(args.agent, force=args.force)
    else:
        build_all(force=args.force)
