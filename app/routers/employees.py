"""
Employee routes — hired agent employees for the active workspace.

GET    /employees                  list hired employees
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
from app.db.queries import agent_employees as employees_q
from app.models.agent import AgentEmployeeResponse

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
