"""
Upload skill markdown files to Anthropic /v1/skills.

Each skill lives in skills/{slug}/ with SKILL.md (required) plus any
other .md files (e.g. REFERENCE.md).  A .cache.json file in the same
directory stores {skill_id, content_hash} so we skip re-uploading
unchanged skills.

Uses httpx directly — the Anthropic SDK >=0.49 has a multipart bug
that serialises file objects as their string repr, causing 400 errors.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import httpx

from app.config import get_settings

SKILLS_DIR = Path(__file__).parents[2] / "skills"

_ANTHROPIC_BETA = "skills-2025-10-02"


def _skill_dir(slug: str) -> Path:
    path = SKILLS_DIR / slug
    if not path.is_dir():
        raise FileNotFoundError(f"Skill directory not found: {path}")
    return path


def _build_zip(skill_dir: Path) -> bytes:
    """Zip all .md files under skill_dir into a single ZIP with one top-level folder."""
    buf = io.BytesIO()
    folder = skill_dir.name
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for md_file in sorted(skill_dir.glob("*.md")):
            zf.writestr(f"{folder}/{md_file.name}", md_file.read_text(encoding="utf-8"))
    return buf.getvalue()


def _content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_cache(skill_dir: Path) -> dict:
    cache_path = skill_dir / ".cache.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text())
    return {}


def _write_cache(skill_dir: Path, skill_id: str, content_hash: str) -> None:
    cache_path = skill_dir / ".cache.json"
    cache_path.write_text(json.dumps({"skill_id": skill_id, "content_hash": content_hash}, indent=2))


def _upload(zip_bytes: bytes, display_title: str) -> str:
    """POST /v1/skills — returns skill_id."""
    settings = get_settings()
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            "https://api.anthropic.com/v1/skills",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "anthropic-beta": _ANTHROPIC_BETA,
            },
            data={"display_title": display_title},
            files=[("files[]", ("skill.zip", zip_bytes, "application/zip"))],
        )
    if not resp.is_success:
        raise RuntimeError(f"Skill upload failed {resp.status_code}: {resp.text}")
    return resp.json()["id"]


def get_or_upload(slug: str) -> str:
    """Return cached skill_id or upload the skill and cache the result."""
    skill_dir = _skill_dir(slug)
    zip_bytes = _build_zip(skill_dir)
    chash = _content_hash(zip_bytes)

    cache = _read_cache(skill_dir)
    if cache.get("content_hash") == chash and cache.get("skill_id"):
        print(f"  [skill:{slug}] cached {cache['skill_id']}")
        return cache["skill_id"]

    # skill_id exists but content changed — reuse existing skill, just update hash
    if cache.get("skill_id"):
        print(f"  [skill:{slug}] content changed, reusing existing {cache['skill_id']}")
        _write_cache(skill_dir, cache["skill_id"], chash)
        return cache["skill_id"]

    display_title = slug.replace("-", " ").title()
    skill_id = _upload(zip_bytes, display_title)
    _write_cache(skill_dir, skill_id, chash)
    print(f"  [skill:{slug}] uploaded → {skill_id}")
    return skill_id


def get_or_upload_all(slugs: list[str]) -> dict[str, str]:
    """Upload all listed skills; returns {slug: skill_id}."""
    return {slug: get_or_upload(slug) for slug in slugs}
