"""Chat tools — read, write, votrix_run as ToolStructure.

Tools resolve org_id/agent_id from the tool context (set before each tool loop).
The db session is retrieved from ctx.db_session.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.db.queries import blueprint_files, agents as agents_q
from app.llm.types import OperationType, RecordFormat, RecordRule, ToolResponse, ToolStructure
from app.tools.command_dispatcher import dispatch_command
from app.tools.tool_context import get_tool_context


class ReadSchema(BaseModel):
    path: str = Field(
        ...,
        description="Path: IDENTITY.md / USER.md / … | skills/<module>/SKILL.md | other relative paths.",
    )


class WriteSchema(BaseModel):
    path: str = Field(..., description="Path to write")
    content: str = Field(..., description="Content to write")


class VotrixRunSchema(BaseModel):
    command: str = Field(..., description="Command: booking.create ..., module.setup_complete <id>, etc.")


_PROMPT_SECTION_MAP = {
    "IDENTITY.md": "identity",
    "SOUL.md": "soul",
    "USER.md": "user",
    "AGENTS.md": "agents",
    "TOOLS.md": "tools",
    "BOOTSTRAP.md": "bootstrap",
}


async def _read_impl(path: str) -> str:
    ctx = get_tool_context()
    if not ctx:
        return "Error: no context"

    session = ctx.db_session
    org_id = ctx.org_id
    agent_id = ctx.agent_id
    name = path.strip().replace("\\", "/").split("/")[-1]

    section = _PROMPT_SECTION_MAP.get(name)
    if section and "/" not in path.strip().strip("/"):
        sections = await agents_q.get_prompt_sections(session, org_id, agent_id)
        return sections.get(section, "")

    normalized = path.strip()
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    file = await blueprint_files.read_file(session, org_id, agent_id, normalized)
    if file:
        return file.get("content", "")

    return f"Error: file not found: {path}"


async def _write_impl(path: str, content: str) -> str:
    ctx = get_tool_context()
    if not ctx:
        return "Error: no context"

    session = ctx.db_session
    org_id = ctx.org_id
    agent_id = ctx.agent_id
    name = path.strip().replace("\\", "/").split("/")[-1]

    section = _PROMPT_SECTION_MAP.get(name)
    if section and "/" not in path.strip().strip("/"):
        await agents_q.set_prompt_section(session, org_id, agent_id, section, content)
        return f"Written to {name}"

    normalized = path.strip()
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    await blueprint_files.write_file(session, org_id, agent_id, normalized, content)
    return f"Written to {path}"


class ChatTools:
    """Chat tools. get_tools() returns List[ToolStructure]."""

    def get_tools(self, enabled_names: Optional[List[str]] = None) -> List[ToolStructure]:
        all_tools = [
            ToolStructure(
                name="read",
                description="Read by path. Prompt files (IDENTITY.md, SOUL.md, etc.) or skill docs (skills/<module>/SKILL.md).",
                func=self.read,
                args_schema=ReadSchema,
                operation_type=OperationType.READ_ONLY,
            ),
            ToolStructure(
                name="write",
                description="Write content by path.",
                func=self.write,
                args_schema=WriteSchema,
                operation_type=OperationType.WRITE,
            ),
            ToolStructure(
                name="votrix_run",
                description="Run a command. NOT a real shell. Available commands are defined by loaded skills.",
                func=self.votrix_run,
                args_schema=VotrixRunSchema,
            ),
        ]
        if enabled_names:
            name_set = set(n.strip().lower() for n in enabled_names if n)
            return [t for t in all_tools if t.name in name_set]
        return all_tools

    async def read(self, path: str) -> ToolResponse:
        try:
            result = await _read_impl(path)
            return ToolResponse(status=True, func_name="read", args={"path": path}, message=result)
        except Exception as e:
            return ToolResponse(status=False, func_name="read", args={"path": path}, message=str(e))

    async def write(self, path: str, content: str) -> ToolResponse:
        try:
            result = await _write_impl(path, content)
            return ToolResponse(status=True, func_name="write", args={"path": path}, message=result)
        except Exception as e:
            return ToolResponse(status=False, func_name="write", args={"path": path, "content": content}, message=str(e))

    async def votrix_run(self, command: str) -> ToolResponse:
        try:
            result = await dispatch_command(command)
            is_error = isinstance(result, str) and result.startswith("Error")
            return ToolResponse(status=not is_error, func_name="votrix_run", args={"command": command}, message=result)
        except Exception as e:
            return ToolResponse(status=False, func_name="votrix_run", args={"command": command}, message=str(e))
