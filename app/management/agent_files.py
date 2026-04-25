from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

from app.client import get_async_client

logger = logging.getLogger(__name__)

_BETA = ["files-api-2025-04-14", "managed-agents-2026-04-01"]
_AGENTS_DIR = Path(__file__).parents[2] / "agents"


def _resolve_agent_file_path(agent_slug: str, relative_path: str) -> Path:
    files_root = (_AGENTS_DIR / agent_slug / "files").resolve()
    path = (files_root / relative_path).resolve()
    if not str(path).startswith(str(files_root) + "/") and path != files_root:
        raise ValueError(f"Invalid file path outside agent files dir: {relative_path}")
    if not path.is_file():
        raise FileNotFoundError(f"Agent file not found: {path}")
    return path


async def upload_config_files(agent_slug: str, file_configs: list[dict]) -> list[dict]:
    """Upload configured local files and return session resources entries.

    Expected file config format:
      {"path": "relative/path.ext", "mountPath": "/workspace/path.ext"}
    """
    if not file_configs:
        return []

    client = get_async_client()
    resources: list[dict] = []

    for idx, entry in enumerate(file_configs):
        rel_path = (entry or {}).get("path")
        mount_path = (entry or {}).get("mountPath")
        if not rel_path or not mount_path:
            raise ValueError(f"Invalid files[{idx}] config: both 'path' and 'mountPath' are required")
        if not isinstance(mount_path, str) or not mount_path.startswith("/"):
            raise ValueError(f"Invalid mountPath in files[{idx}]: must be an absolute path")

        local_path = _resolve_agent_file_path(agent_slug, rel_path)
        data = local_path.read_bytes()
        mime = mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"

        uploaded = await client.beta.files.upload(
            file=(local_path.name, data, mime),
            betas=_BETA,
        )
        logger.info(
            "Uploaded agent preset file agent=%s local=%s file_id=%s mount=%s",
            agent_slug,
            str(local_path),
            uploaded.id,
            mount_path,
        )
        resources.append(
            {
                "type": "file",
                "file_id": uploaded.id,
                "mount_path": mount_path,
            }
        )

    return resources
