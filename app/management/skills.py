"""
Upload skill directories to Anthropic /v1/skills.

Each skill lives in skills/{slug}/ and may contain any files.
All files in the directory are zipped and uploaded as a single skill.

Registry (.skills_registry.json at the project root) tracks
{slug: {skill_id, content_hash}} for all skills.

On first upload: client.beta.skills.create() → creates skill, gets skill_id.
On content change: client.beta.skills.versions.create() → new version, same skill_id.
Agents use version="latest" so they pick up new versions automatically without re-provisioning.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

from app.client import get_client

SKILLS_DIR = Path(__file__).parents[2] / "skills"
_REGISTRY_PATH = Path(__file__).parents[2] / ".skills_registry.json"


def _skill_dir(slug: str) -> Path:
    path = SKILLS_DIR / slug
    if not path.is_dir():
        raise FileNotFoundError(f"Skill directory not found: {path}")
    return path


def _build_zip(skill_dir: Path) -> bytes:
    """Zip all files under skill_dir into a single ZIP with one top-level folder."""
    buf = io.BytesIO()
    folder = skill_dir.name
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(skill_dir.iterdir()):
            if f.is_file():
                zf.writestr(f"{folder}/{f.name}", f.read_bytes())
    return buf.getvalue()


def _content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_registry() -> dict:
    if _REGISTRY_PATH.exists():
        return json.loads(_REGISTRY_PATH.read_text())
    return {}


def _write_registry(registry: dict) -> None:
    _REGISTRY_PATH.write_text(json.dumps(registry, indent=2))


def _upload_new(zip_bytes: bytes, display_title: str) -> str:
    """Create new skill via SDK, returns skill_id."""
    client = get_client()
    result = client.beta.skills.create(
        display_title=display_title,
        files=[("skill.zip", zip_bytes, "application/zip")],
    )
    return result.id


def _upload_version(skill_id: str, zip_bytes: bytes) -> None:
    """Upload new version of existing skill via SDK."""
    client = get_client()
    client.beta.skills.versions.create(
        skill_id,
        files=[("skill.zip", zip_bytes, "application/zip")],
    )


def get_or_upload(slug: str) -> str:
    """
    Return cached skill_id, uploading or versioning as needed.

    - No registry entry: upload new skill → store skill_id + hash
    - Hash unchanged:    return cached skill_id (no-op)
    - Hash changed:      upload new version → update hash, keep skill_id
    """
    skill_dir = _skill_dir(slug)
    zip_bytes = _build_zip(skill_dir)
    chash = _content_hash(zip_bytes)

    registry = _read_registry()
    entry = registry.get(slug, {})

    if not entry.get("skill_id"):
        display_title = slug.replace("-", " ").title()
        skill_id = _upload_new(zip_bytes, display_title)
        registry[slug] = {"skill_id": skill_id, "content_hash": chash}
        _write_registry(registry)
        print(f"  [skill:{slug}] uploaded → {skill_id}")
        return skill_id

    skill_id = entry["skill_id"]

    if entry.get("content_hash") == chash:
        return skill_id

    _upload_version(skill_id, zip_bytes)
    registry[slug] = {"skill_id": skill_id, "content_hash": chash}
    _write_registry(registry)
    print(f"  [skill:{slug}] new version uploaded → {skill_id}")
    return skill_id


def get_or_upload_all(slugs: list[str]) -> dict[str, str]:
    """Upload/version all listed skills; returns {slug: skill_id}."""
    return {slug: get_or_upload(slug) for slug in slugs}
