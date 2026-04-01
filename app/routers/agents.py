"""Blueprint agent CRUD API.

Routes:
  POST   /orgs/{org_id}/agents          — create agent (org-scoped)
  GET    /orgs/{org_id}/agents          — list agents (org-scoped)
  GET    /agents/{agent_id}             — get agent detail
  PATCH  /agents/{agent_id}             — update agent
  DELETE /agents/{agent_id}             — delete agent
"""

import logging
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_session
from app.db.queries import agents as agents_q, blueprint_files
from app.db.queries.blueprint_files import _derive_fields
from app.storage import BUCKET, download_file
from app.models.agent import (
    AgentDetail,
    AgentSummary,
    CreateAgentRequest,
    UpdateAgentRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agents"])

_404 = {404: {"description": "Agent not found"}}
_400 = {400: {"description": "Bad request"}}

_DEFAULT_BLUEPRINT_FILES_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

# Loaded once at startup via load_default_blueprint_files()
_default_blueprint_cache: list[dict] | None = None


def load_default_blueprint_files() -> None:
    """Read prompt files from disk into memory. Called once at app startup."""
    global _default_blueprint_cache
    if not _DEFAULT_BLUEPRINT_FILES_DIR.is_dir():
        _default_blueprint_cache = []
        return

    rows: list[dict] = []
    for disk_path in sorted(_DEFAULT_BLUEPRINT_FILES_DIR.rglob("*")):
        virtual = "/" + str(disk_path.relative_to(_DEFAULT_BLUEPRINT_FILES_DIR))
        name = disk_path.name
        if disk_path.is_dir():
            rows.append({
                "path": virtual,
                "name": name,
                "type": "directory",
                "content": "",
                "storage_path": None,
                "mime_type": "",
                "created_by": "system",
                **_derive_fields(virtual, name),
            })
        elif disk_path.is_file():
            content = disk_path.read_text(encoding="utf-8")
            suffix = disk_path.suffix.lower()
            mime = "application/json" if suffix == ".json" else "text/markdown"
            rows.append({
                "path": virtual,
                "name": name,
                "type": "file",
                "content": content,
                "storage_path": None,
                "mime_type": mime,
                "created_by": "system",
                **_derive_fields(virtual, name, content),
            })
    _default_blueprint_cache = rows
    logger.info("Loaded %d default blueprint files from disk", len(rows))


def _to_detail(row: dict) -> AgentDetail:
    return AgentDetail(
        id=str(row.get("id", "")),
        org_id=str(row.get("org_id", "")),
        display_name=row.get("display_name", ""),
        deleted_at=row.get("deleted_at"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


@router.post("/orgs/{org_id}/agents", response_model=AgentDetail, status_code=201,
             summary="Create agent",
             responses={404: {"description": "Seed source agent not found"}})
async def create_agent(
    org_id: uuid.UUID,
    body: CreateAgentRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new blueprint agent. Optionally seed from an existing agent."""
    kwargs = {}
    if body.display_name:
        kwargs["display_name"] = body.display_name

    if body.seed_from:
        source = await agents_q.get_agent(session, body.seed_from)
        if not source:
            raise HTTPException(status_code=404, detail=f"Seed source agent '{body.seed_from}' not found")
        if "display_name" not in kwargs:
            kwargs["display_name"] = source.get("display_name", "")

    row = await agents_q.create_agent(session, org_id, **kwargs)

    if body.seed_from:
        source_id = uuid.UUID(body.seed_from)
        new_id = row["id"]
        source_files = await blueprint_files.tree(session, source_id)
        for f in source_files:
            if f["type"] == "directory":
                await blueprint_files.mkdir(session, new_id, f["path"])
            else:
                content_row = await blueprint_files.read_file(session, source_id, f["path"])
                if content_row:
                    if content_row.get("storage_path"):
                        data = await download_file(BUCKET, content_row["storage_path"])
                        await blueprint_files.write_file(
                            session, new_id, f["path"],
                            mime_type=content_row.get("mime_type", "application/octet-stream"),
                            binary_data=data,
                        )
                    else:
                        await blueprint_files.write_file(
                            session, new_id, f["path"],
                            content_row.get("content") or "",
                            mime_type=content_row.get("mime_type", "text/markdown"),
                        )
    elif not body.skip_defaults and _default_blueprint_cache:
        new_id = row["id"]
        bulk_rows = [{"blueprint_agent_id": new_id, **entry} for entry in _default_blueprint_cache]
        await blueprint_files.bulk_insert(session, bulk_rows)

    return _to_detail(row)


@router.get("/orgs/{org_id}/agents", response_model=List[AgentSummary], summary="List agents")
async def list_agents(org_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """List all blueprint agents in an org."""
    rows = await agents_q.list_agents(session, org_id)
    return [AgentSummary(id=str(r["id"]), display_name=r["display_name"], created_at=r["created_at"], updated_at=r["updated_at"]) for r in rows]


@router.get("/agents/{agent_id}", response_model=AgentDetail, summary="Get agent", responses=_404)
async def get_agent(agent_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Return full agent detail including integrations."""
    row = await agents_q.get_agent(session, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _to_detail(row)


@router.patch("/agents/{agent_id}", response_model=AgentDetail, summary="Update agent",
              responses={**_404, **_400})
async def update_agent(
    agent_id: uuid.UUID,
    body: UpdateAgentRequest,
    session: AsyncSession = Depends(get_session),
):
    """Partial update — display_name."""
    updates = {}
    if body.display_name is not None:
        updates["display_name"] = body.display_name

    if updates:
        row = await agents_q.update_agent(session, agent_id, **updates)
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
    else:
        row = await agents_q.get_agent(session, agent_id)
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")

    return _to_detail(row)


@router.delete("/agents/{agent_id}", status_code=204, summary="Delete agent", responses=_404)
async def delete_agent(
    agent_id: uuid.UUID,
    soft: bool = Query(False, description="Soft delete — hide from lists but keep files"),
    session: AsyncSession = Depends(get_session),
):
    """Delete a blueprint agent. Use ?soft=true to soft-delete (hide but keep files)."""
    if soft:
        deleted = await agents_q.soft_delete_agent(session, agent_id)
    else:
        deleted = await agents_q.delete_agent(session, agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")
