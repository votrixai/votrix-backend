#!/usr/bin/env python3
"""
Safe alembic baseline reset.

Collapses all existing alembic migrations into a single baseline revision
that contains the current database schema as raw SQL, so fresh environments
can bootstrap in one step instead of replaying hundreds of revisions.

================================================================
WHEN TO RUN THIS — read before using
================================================================
This is a coordination-heavy operation, not a tidiness tool.  Every
environment (staging, CI, every developer laptop) needs manual stamping
after the baseline is applied, or they will diverge.

Rough rules of thumb:
  - < 50 migrations:   don't run this.  Keeping history is ~free.
  - 50 – 500:          probably still not worth it — consider only at
                       major release boundaries.
  - 500 – 1000:        start evaluating.  Bootstrap time and dead-schema
                       references in old revisions become real pain.
  - 1000+:             yes, periodic baseline resets are standard here.
  - multi-thousand,
    multi-service:     also evaluate declarative schema tooling
                       (Atlas, Skeema, sqldef) — you may be outgrowing
                       alembic's imperative migration model entirely.

The value of a baseline reset is almost entirely in faster fresh-DB
bootstrap and lower cognitive load for new contributors.  It does NOT
meaningfully speed up `alembic upgrade` on existing envs (alembic
skips applied revisions in milliseconds each).

If you're reading this on a repo with < 50 migrations: close the file.
================================================================

Usage:
    python scripts/alembic_baseline_reset.py            # dry-run (default)
    python scripts/alembic_baseline_reset.py --apply    # destructive

Preconditions (enforced):
  - alembic has exactly one head
  - the target DB is currently at that head (no pending upgrades)
  - pg_dump is in PATH

Dry-run writes the new baseline file into alembic/versions/ so you can
review the SQL before committing to --apply.  No other files are moved
and the DB is not touched.

With --apply:
  1. Moves every pre-baseline migration file into
     alembic/versions/_archive_<ts>/ (preserved, not deleted).
  2. alembic stamps the DB to the new baseline revision.
  3. Prints a coordination checklist for other environments.

Coordinating other envs (staging, CI, every dev laptop):
  1. Pull the branch with the new baseline file.
  2. Verify alembic current == old head.
  3. Run:   alembic stamp <new_baseline_rev>
  4. Verify alembic current == new head.
  Anyone who runs `alembic upgrade` without stamping first will hit
  "Can't locate revision" and must manually stamp.  Long-lived feature
  branches whose migrations chain off a now-archived parent will also
  break — those branches must rebase their migrations onto the new
  baseline.

Refuses to run if:
  - multiple alembic heads exist (merge them first)
  - DB is not at head (upgrade first)
  - the new baseline filename already exists

IMPORTANT: take a DB backup before --apply.  The stamp itself is reversible
(stamp back to old head), but the archived migration files' chain is broken
once --apply runs — you need the archive folder to roll back.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from urllib.parse import urlparse

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "alembic" / "versions"
ALEMBIC_INI = ROOT / "alembic.ini"


def _sync_url(db_url: str) -> str:
    return db_url.replace("+asyncpg", "").replace("+psycopg", "")


def assert_single_head(cfg: Config) -> str:
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    if len(heads) != 1:
        sys.exit(f"ERROR: alembic has {len(heads)} heads: {heads}. Run `alembic merge` first.")
    return heads[0]


def assert_db_at_head(db_url: str, head: str) -> None:
    engine = create_engine(_sync_url(db_url))
    with engine.connect() as conn:
        try:
            rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
        except Exception as e:
            sys.exit(f"ERROR: cannot read alembic_version table: {e}")
    current = sorted(r[0] for r in rows)
    if current != [head]:
        sys.exit(
            f"ERROR: DB is at {current}, expected [{head}].\n"
            f"Run `alembic upgrade head` first, then re-run this script."
        )


def dump_schema(db_url: str) -> str:
    u = urlparse(_sync_url(db_url))
    env = {**os.environ, "PGPASSWORD": u.password or ""}
    cmd = [
        "pg_dump",
        "--schema-only",
        "--no-owner",
        "--no-privileges",
        "--no-comments",
        "-h", u.hostname or "localhost",
        "-p", str(u.port or 5432),
        "-U", u.username or os.environ.get("USER", "postgres"),
        (u.path or "/").lstrip("/"),
    ]
    print(f"[run] {' '.join(cmd[:1] + cmd[1:5])} ...")
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
    return result.stdout


def strip_alembic_version(sql: str) -> str:
    """Remove CREATE TABLE alembic_version and related statements.

    The new baseline migration itself populates alembic_version via stamp(),
    so we don't want the SQL dump to re-create that table.
    """
    out: list[str] = []
    in_alembic_block = False
    for line in sql.splitlines():
        if "alembic_version" in line and ("CREATE TABLE" in line or "ALTER TABLE" in line):
            in_alembic_block = True
            continue
        if in_alembic_block:
            if line.strip() == ");":
                in_alembic_block = False
            continue
        if "alembic_version" in line:
            # skip stray constraint / index lines
            continue
        out.append(line)
    return "\n".join(out)


def new_baseline_revision_id() -> str:
    return "baseline_" + dt.datetime.now().strftime("%Y%m%d")


def write_baseline(rev_id: str, sql: str) -> Path:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M")
    path = VERSIONS / f"{ts}_baseline.py"
    if path.exists():
        sys.exit(f"ERROR: {path} already exists; delete or rename it first")

    # Double-check no triple-quote collision; pg_dump output shouldn't contain them
    # but guard against pathological string literals in the DB schema.
    if '"""' in sql:
        sys.exit("ERROR: schema dump contains triple-quote — inline embedding would break.")

    body = textwrap.dedent(f'''\
        """baseline: squashed history collapsed into one revision

        Revision ID: {rev_id}
        Revises: None
        Create Date: {dt.datetime.now().isoformat()}

        This revision contains the entire schema as of the squash date,
        dumped via `pg_dump --schema-only`.  Fresh databases run this
        single migration to reach the same state as replaying the full
        archived history.
        """
        from alembic import op

        revision = "{rev_id}"
        down_revision = None
        branch_labels = None
        depends_on = None


        BASELINE_SQL = """
''') + sql + textwrap.dedent('''\
        """


        def upgrade() -> None:
            op.execute(BASELINE_SQL)


        def downgrade() -> None:
            raise NotImplementedError(
                "baseline cannot be downgraded — restore from DB backup instead"
            )
    ''')
    path.write_text(body)
    return path


def archive_old_migrations(new_baseline: Path) -> tuple[Path, list[str]]:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M")
    archive = VERSIONS / f"_archive_{ts}"
    archive.mkdir(exist_ok=False)
    moved: list[str] = []
    for f in sorted(VERSIONS.glob("*.py")):
        if f == new_baseline:
            continue
        shutil.move(str(f), archive / f.name)
        moved.append(f.name)
    return archive, moved


def main() -> None:
    p = argparse.ArgumentParser(description="Safe alembic baseline reset")
    p.add_argument("--apply", action="store_true",
                   help="Archive old migrations and stamp DB (destructive). Default is dry-run.")
    p.add_argument("--db-url", default=os.environ.get("DATABASE_URL"),
                   help="Override DB URL (defaults to env or app.config)")
    args = p.parse_args()

    if not args.db_url:
        from app.config import get_settings
        args.db_url = get_settings().database_url

    # Redact credentials in output
    redacted = args.db_url.split("@")[-1] if "@" in args.db_url else args.db_url
    mode = "APPLY (destructive)" if args.apply else "DRY-RUN"
    print(f"[cfg] target DB: {redacted}")
    print(f"[cfg] mode:      {mode}")
    print()

    cfg = Config(str(ALEMBIC_INI))
    head = assert_single_head(cfg)
    print(f"[ok] single alembic head: {head}")

    assert_db_at_head(args.db_url, head)
    print("[ok] DB matches alembic head")

    print("[step] dumping schema via pg_dump ...")
    sql = dump_schema(args.db_url)
    sql = strip_alembic_version(sql)
    print(f"[ok] dumped {len(sql)} bytes of SQL")

    rev = new_baseline_revision_id()
    baseline = write_baseline(rev, sql)
    print(f"[ok] wrote baseline file: {baseline.relative_to(ROOT)}")
    print(f"     revision id: {rev}")

    if not args.apply:
        print()
        print("-" * 64)
        print("DRY-RUN complete — no migrations moved, DB not stamped.")
        print("-" * 64)
        print(f"Review the baseline SQL in: {baseline.relative_to(ROOT)}")
        print("If the dump looks correct and complete, re-run with --apply.")
        print("To abort, delete the baseline file and re-run:")
        print(f"  rm {baseline.relative_to(ROOT)}")
        return

    archive, moved = archive_old_migrations(baseline)
    print(f"[ok] archived {len(moved)} old migration files to {archive.relative_to(ROOT)}")

    print(f"[step] stamping DB to {rev} ...")
    command.stamp(cfg, rev)
    print(f"[ok] DB stamped to {rev}")

    print()
    print("=" * 64)
    print("LOCAL baseline reset COMPLETE.")
    print("=" * 64)
    print("Coordination checklist for OTHER environments:")
    print("  (staging, CI, every dev laptop — do this before anyone runs")
    print("   `alembic upgrade` against that env)")
    print()
    print("  1. Pull the branch that contains the new baseline file.")
    print("  2. Verify the env's DB is at the OLD head:")
    print(f"       alembic current       # expected: {head}")
    print("     If not at head, upgrade first: `alembic upgrade head`.")
    print("  3. Stamp WITHOUT running migrations:")
    print(f"       alembic stamp {rev}")
    print("  4. Verify:")
    print(f"       alembic current       # expected: {rev}")
    print()
    print(f"Old migrations preserved at: {archive.relative_to(ROOT)}")
    print("Delete that folder only after every env is confirmed on the new baseline.")
    print()
    print("Fresh DB bootstrap:  `alembic upgrade head` now applies the single")
    print("baseline revision and reaches the same schema state.")


if __name__ == "__main__":
    main()
