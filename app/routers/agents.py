"""
Agent template routes — reads from agents/ directory on disk.

GET    /agents                         list all agent templates
GET    /agents/blueprints              list provisioned blueprints with hire status
GET    /agents/{agent_id}              get config
POST   /agents/{agent_id}/reprovision  update-or-create agent on Anthropic
"""

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import WorkspaceContext, require_workspace
from app.db.engine import get_session
from app.db.queries import agent_blueprints as blueprints_q
from app.db.queries import agent_employees as employees_q
from app.management.memory_stores import sync_memory_stores_for_blueprint
from app.management.provisioning import create_user_agent, update_user_agent, _read_config
from app.models.agent import AgentBlueprintResponse, AgentConfig

router = APIRouter(prefix="/agents", tags=["agents"])

AGENTS_DIR = Path(__file__).parents[2] / "agents"
EXCLUDED_AGENT_DIRS = {"TEMPLATE"}


def _load_config(agent_id: str) -> AgentConfig:
    config_path = AGENTS_DIR / agent_id / "config.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    data = json.loads(config_path.read_text())
    return AgentConfig(slug=agent_id, **{k: v for k, v in data.items() if k not in ("agentId", "envId")})


def _parse_blueprint_id(agent_id: str) -> uuid.UUID:
    config = _read_config(agent_id)
    raw = config.get("agentId")
    if not raw:
        raise HTTPException(status_code=422, detail=f"Agent '{agent_id}' has no agentId in config.json")
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Agent '{agent_id}' has invalid agentId (must be UUID)")


@router.get("", response_model=list[AgentConfig])
async def list_agents():
    agent_ids = sorted(
        d.name for d in AGENTS_DIR.iterdir()
        if d.is_dir() and d.name not in EXCLUDED_AGENT_DIRS
    )
    return [_load_config(agent_id) for agent_id in agent_ids]


@router.get("/blueprints", response_model=list[AgentBlueprintResponse])
async def list_blueprints(
    db: AsyncSession = Depends(get_session),
    ctx: WorkspaceContext = Depends(require_workspace),
):
    agent_ids = sorted(
        d.name for d in AGENTS_DIR.iterdir()
        if d.is_dir() and d.name not in EXCLUDED_AGENT_DIRS
    )

    result = []
    for agent_id in agent_ids:
        config_path = AGENTS_DIR / agent_id / "config.json"
        if not config_path.exists():
            continue
        config = json.loads(config_path.read_text())
        raw_id = config.get("agentId")
        if not raw_id:
            continue
        try:
            blueprint_id = uuid.UUID(raw_id)
        except ValueError:
            continue

        bp = await blueprints_q.get(db, blueprint_id)
        if not bp:
            continue

        employee = await employees_q.get(db, ctx.workspace_id, bp.id)

        result.append(AgentBlueprintResponse(
            id=str(bp.id),
            display_name=bp.display_name,
            provider=bp.provider,
            slug=agent_id,
            skills=config.get("skills", []),
            model=config.get("model", ""),
            is_hired=employee is not None,
            employee_id=str(employee.id) if employee else None,
        ))

    return result


@router.get("/{agent_id}", response_model=AgentConfig)
async def get_agent(agent_id: str):
    return _load_config(agent_id)


@router.post("/{agent_id}/reprovision")
async def reprovision_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_session),
):
    _load_config(agent_id)  # 404 guard
    config = _read_config(agent_id)
    blueprint_id = _parse_blueprint_id(agent_id)

    existing_bp = await blueprints_q.get(db, blueprint_id)

    if existing_bp:
        # Update Anthropic agent in-place — provider_agent_id stays the same
        await update_user_agent(agent_id, existing_bp.provider_agent_id)
        bp = existing_bp
    else:
        # First provision — create on Anthropic, then persist to DB
        provider_agent_id = await create_user_agent(agent_id)
        bp = await blueprints_q.create(
            db,
            blueprint_id=blueprint_id,
            provider_agent_id=provider_agent_id,
            display_name=config.get("name", agent_id),
        )

    memory_configs = config.get("memoryConfigs", [])
    memory_stats = await sync_memory_stores_for_blueprint(db, bp.id, memory_configs)

    return {
        "blueprint_id": str(bp.id),
        "provider_agent_id": bp.provider_agent_id,
        "memory_stores": memory_stats,
    }
