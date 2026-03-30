"""Seed database from local prompt files.

Run once on first boot or via CLI to populate:
  1. Default org + agent
  2. Agent prompt sections (IDENTITY.md, SOUL.md, etc.)
  3. Agent prompt files (skills/*, registry.json)
  4. Global guidelines (TOOL_CALLS.md, SKILLS.md)
"""

import json
import logging
from pathlib import Path
from typing import Dict

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.engine import session_scope
from app.db.models.orgs import Org
from app.db.queries import agents as agents_q, blueprint_files, guidelines as guidelines_q

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
DEFAULT_AGENT_DIR = PROMPTS_DIR / "agents" / "default"
GUIDELINES_DIR = PROMPTS_DIR / "guidelines"

PROMPT_FILE_MAP = {
    "IDENTITY.md": "identity",
    "SOUL.md": "soul",
    "AGENTS.md": "agents",
    "USER.md": "user",
    "TOOLS.md": "tools",
    "BOOTSTRAP.md": "bootstrap",
}


async def seed_default_org(org_id: str = "default") -> None:
    """Create default org if it doesn't exist."""
    async with session_scope() as session:
        stmt = select(Org.id).where(Org.org_id == org_id)
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            logger.info("Org '%s' already exists, skipping", org_id)
            return
        stmt = pg_insert(Org).values(org_id=org_id, display_name="Default Org").on_conflict_do_nothing()
        await session.execute(stmt)
        await session.commit()
        logger.info("Created org '%s'", org_id)


async def seed_default_agent(org_id: str = "default", agent_id: str = "default") -> None:
    """Create default agent with prompt sections from disk."""
    async with session_scope() as session:
        existing = await agents_q.get_agent(session, org_id, agent_id)
        if existing:
            logger.info("Agent '%s/%s' already exists, skipping", org_id, agent_id)
            return

        prompt_cols: Dict[str, str] = {}
        for filename, section_key in PROMPT_FILE_MAP.items():
            filepath = DEFAULT_AGENT_DIR / filename
            if filepath.exists():
                prompt_cols[f"prompt_{section_key}"] = filepath.read_text(encoding="utf-8")

        registry_path = DEFAULT_AGENT_DIR / "registry.json"
        registry = {}
        if registry_path.exists():
            registry = json.loads(registry_path.read_text(encoding="utf-8"))

        await agents_q.create_agent(session, org_id, agent_id, **prompt_cols, registry=registry)
        logger.info("Created agent '%s/%s' with prompt sections", org_id, agent_id)


async def seed_agent_files(org_id: str = "default", agent_id: str = "default") -> None:
    """Seed blueprint_files from disk skills/ directory."""
    skills_dir = DEFAULT_AGENT_DIR / "skills"
    if not skills_dir.exists():
        logger.info("No skills directory found, skipping file seed")
        return

    async with session_scope() as session:
        count = 0
        for file_path in skills_dir.rglob("*"):
            if file_path.is_dir():
                rel = "/" + str(file_path.relative_to(DEFAULT_AGENT_DIR)).replace("\\", "/")
                await blueprint_files.mkdir(session, org_id, agent_id, rel, created_by="seed")
                count += 1
            elif file_path.is_file():
                rel = "/" + str(file_path.relative_to(DEFAULT_AGENT_DIR)).replace("\\", "/")
                content = file_path.read_text(encoding="utf-8")
                mime = "text/markdown" if file_path.suffix == ".md" else "application/json" if file_path.suffix == ".json" else "text/plain"
                await blueprint_files.write_file(session, org_id, agent_id, rel, content, mime_type=mime, created_by="seed")
                count += 1

        registry_path = DEFAULT_AGENT_DIR / "registry.json"
        if registry_path.exists():
            content = registry_path.read_text(encoding="utf-8")
            await blueprint_files.write_file(session, org_id, agent_id, "/registry.json", content, mime_type="application/json", created_by="seed")
            count += 1

        logger.info("Seeded %d agent files for '%s/%s'", count, org_id, agent_id)


async def seed_guidelines() -> None:
    """Seed global guidelines from disk."""
    if not GUIDELINES_DIR.exists():
        logger.info("No guidelines directory found, skipping")
        return

    async with session_scope() as session:
        for filepath in GUIDELINES_DIR.glob("*.md"):
            guideline_id = filepath.stem
            content = filepath.read_text(encoding="utf-8")
            if content.strip().startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    content = parts[2]
            lines = content.strip().split("\n")
            if lines and lines[0].strip().startswith("##"):
                lines = lines[1:]
            content = "\n".join(lines).strip()

            await guidelines_q.upsert(session, guideline_id, content)
            logger.info("Seeded guideline '%s'", guideline_id)


async def seed_all(org_id: str = "default", agent_id: str = "default") -> None:
    """Run full seed: org -> agent -> files -> guidelines."""
    await seed_default_org(org_id)
    await seed_default_agent(org_id, agent_id)
    await seed_agent_files(org_id, agent_id)
    await seed_guidelines()
    logger.info("Seed complete for '%s/%s'", org_id, agent_id)
