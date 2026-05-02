"""
Employee routes — hired agent employees for the active workspace.

GET    /employees                  list hired employees
POST   /employees                  hire an employee from an agent template
DELETE /employees/{employee_id}    fire an employee
"""

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import WorkspaceContext, require_workspace
from app.db.engine import get_session
from app.db.models.agent_blueprints import AgentBlueprint
from app.db.models.agent_employees import AgentEmployee
from app.db.queries import agent_blueprints as blueprints_q
from app.db.queries import agent_employees as employees_q
from app.management.memory_stores import create_for_employee
from app.management.provisioning import _read_config
from app.models.agent import AgentEmployeeCreateRequest, AgentEmployeeResponse

router = APIRouter(prefix="/employees", tags=["employees"])

AGENTS_DIR = Path(__file__).parents[2] / "agents"
EXCLUDED_AGENT_DIRS = {"TEMPLATE"}


def _build_blueprint_config_map() -> dict[uuid.UUID, dict]:
    """Return {blueprint_uuid: {slug, model}} from disk configs."""
    result = {}
    for agent_dir in AGENTS_DIR.iterdir():
        if not agent_dir.is_dir() or agent_dir.name in EXCLUDED_AGENT_DIRS:
            continue
        config_path = agent_dir / "config.json"
        if not config_path.exists():
            continue
        config = json.loads(config_path.read_text())
        raw_id = config.get("agentId")
        if not raw_id:
            continue
        try:
            bp_id = uuid.UUID(raw_id)
        except ValueError:
            continue
        result[bp_id] = {
            "slug": agent_dir.name,
            "model": config.get("model", ""),
        }
    return result


def _load_config(agent_slug: str) -> dict:
    config_path = AGENTS_DIR / agent_slug / "config.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"Agent '{agent_slug}' not found")
    return json.loads(config_path.read_text())


def _parse_blueprint_id(agent_slug: str) -> uuid.UUID:
    config = _read_config(agent_slug)
    raw = config.get("agentId")
    if not raw:
        raise HTTPException(
            status_code=422,
            detail=f"Agent '{agent_slug}' has no agentId in config.json",
        )
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Agent '{agent_slug}' has invalid agentId (must be UUID)",
        )


@router.get("", response_model=list[AgentEmployeeResponse])
async def list_employees(
    db: AsyncSession = Depends(get_session),
    ctx: WorkspaceContext = Depends(require_workspace),
):
    rows = await db.execute(
        select(AgentEmployee, AgentBlueprint)
        .join(AgentBlueprint, AgentEmployee.agent_blueprint_id == AgentBlueprint.id)
        .where(AgentEmployee.workspace_id == ctx.workspace_id)
    )
    pairs = rows.all()
    if not pairs:
        return []

    config_map = _build_blueprint_config_map()

    return [
        AgentEmployeeResponse(
            id=str(emp.id),
            workspace_id=str(emp.workspace_id),
            agent_blueprint_id=str(emp.agent_blueprint_id),
            display_name=bp.display_name,
            slug=config_map.get(emp.agent_blueprint_id, {}).get("slug", ""),
            model=config_map.get(emp.agent_blueprint_id, {}).get("model", ""),
            created_at=emp.created_at.isoformat(),
        )
        for emp, bp in pairs
    ]


@router.post("", status_code=201)
async def hire_employee(
    body: AgentEmployeeCreateRequest,
    db: AsyncSession = Depends(get_session),
    ctx: WorkspaceContext = Depends(require_workspace),
):
    agent_slug = body.agent_slug

    config = _load_config(agent_slug)
    blueprint_id = _parse_blueprint_id(agent_slug)

    bp = await blueprints_q.get(db, blueprint_id)
    if not bp:
        raise HTTPException(
            status_code=422,
            detail=f"Agent '{agent_slug}' has not been provisioned yet. Run reprovision first.",
        )

    existing = await employees_q.get(db, ctx.workspace_id, blueprint_id)
    if existing:
        return {
            "employee_id": str(existing.id),
            "workspace_id": str(ctx.workspace_id),
            "blueprint_id": str(blueprint_id),
        }

    employee = await employees_q.create(db, ctx.workspace_id, blueprint_id)

    for mc in config.get("memoryConfigs", []):
        await create_for_employee(db, employee.id, mc)

    return {
        "employee_id": str(employee.id),
        "workspace_id": str(ctx.workspace_id),
        "blueprint_id": str(blueprint_id),
    }


@router.delete("/{employee_id}", status_code=204)
async def fire_employee(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    ctx: WorkspaceContext = Depends(require_workspace),
):
    employee = await employees_q.get_by_id(db, employee_id)
    if not employee or employee.workspace_id != ctx.workspace_id:
        raise HTTPException(status_code=404, detail="Employee not found")

    await employees_q.delete(db, employee.id)
