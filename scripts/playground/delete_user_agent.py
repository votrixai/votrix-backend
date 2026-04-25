"""
Delete all provisioned Anthropic agents for a given user_id.

Steps:
  1. Query user_agents table for the user
  2. Call client.beta.agents.delete() on each Anthropic agent
  3. Remove the user_agents rows from DB

Usage:
  uv run python scripts/delete_user_agent.py <user_id>
  uv run python scripts/delete_user_agent.py <user_id> --dry-run
"""

import asyncio
import sys
import uuid

import anthropic
from sqlalchemy import delete, select

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parents[1]))

from app.client import get_client
from app.config import get_settings
from app.db.engine import session_scope
from app.db.models.user_agents import UserAgent


async def delete_user_agents(user_id: uuid.UUID, dry_run: bool = False) -> None:
    client = get_client()

    async with session_scope() as db:
        rows = (
            await db.execute(
                select(UserAgent).where(UserAgent.user_id == user_id)
            )
        ).scalars().all()

    if not rows:
        print(f"No provisioned agents found for user {user_id}")
        return

    print(f"Found {len(rows)} agent(s) for user {user_id}:")
    for row in rows:
        print(f"  slug={row.agent_slug}  anthropic_agent_id={row.agent_id}")

    if dry_run:
        print("\n[dry-run] No changes made.")
        return

    for row in rows:
        # Delete from Anthropic
        try:
            client.beta.agents.delete(row.agent_id)
            print(f"  ✓ Deleted Anthropic agent {row.agent_id} (slug={row.agent_slug})")
        except anthropic.NotFoundError:
            print(f"  ~ Agent {row.agent_id} not found on Anthropic (already gone)")
        except Exception as exc:
            print(f"  ✗ Failed to delete Anthropic agent {row.agent_id}: {exc}")

    # Remove DB rows
    async with session_scope() as db:
        await db.execute(
            delete(UserAgent).where(UserAgent.user_id == user_id)
        )
        await db.commit()
    print(f"\nRemoved {len(rows)} row(s) from user_agents table.")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv

    if not args:
        print("Usage: uv run python scripts/delete_user_agent.py <user_id> [--dry-run]")
        sys.exit(1)

    try:
        user_id = uuid.UUID(args[0])
    except ValueError:
        print(f"Invalid UUID: {args[0]}")
        sys.exit(1)

    # Settings are loaded from .env automatically
    get_settings()

    asyncio.run(delete_user_agents(user_id, dry_run=dry_run))


if __name__ == "__main__":
    main()
