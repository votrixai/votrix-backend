"""
Platform handler — tool schemas, execution closures, and tool assembly.

Local tools (read, write, edit, glob, grep) are backed by the user_files
virtual filesystem (Postgres). Composio-routed tools (web_search, web_fetch,
bash_tool) are delegated to the Composio SDK.

web_search and web_fetch are deferred — not bound to the LLM by default.
The LLM activates them via tool_search, after which they are added to the
session's active_tools and bound on subsequent model calls.
"""

import base64
import fnmatch
import logging
import uuid
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple, Type

from google import genai
from google.genai import types as genai_types
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool, StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.queries import user_files as user_files_q
from app.models.integration import Integration, Tool

logger = logging.getLogger(__name__)

# Tool names that are deferred (not bound to LLM until explicitly activated).
_DEFERRED_TOOL_NAMES: frozenset[str] = frozenset({"web_search", "web_fetch"})


# ── Context ───────────────────────────────────────────────────────────────────

@dataclass
class FileContext:
    session: AsyncSession
    blueprint_agent_id: uuid.UUID
    user_id: uuid.UUID


# ── Pydantic input models ─────────────────────────────────────────────────────

class ReadInput(BaseModel):
    file_path: str = Field(..., description="Absolute path to the file to read")
    limit: Optional[int] = Field(None, description="Number of lines to read", gt=0)
    offset: Optional[int] = Field(None, description="Line number to start reading from (1-based)", ge=0)


class WriteInput(BaseModel):
    file_path: str = Field(..., description="Absolute path to the file to write")
    content: str  = Field(..., description="Content to write to the file")


class EditInput(BaseModel):
    file_path:   str  = Field(..., description="Absolute path to the file to edit")
    old_string:  str  = Field(..., description="Text to replace (must appear exactly once unless replace_all is true)")
    new_string:  str  = Field("",  description="Replacement text (empty string to delete)")
    replace_all: bool = Field(False, description="Replace all occurrences instead of just the first")


class GlobInput(BaseModel):
    pattern: str           = Field(..., description="Glob pattern to match files against, e.g. '**/*.py'")
    path:    Optional[str] = Field(None, description="Root directory to search in (default: /)")


class GrepInput(BaseModel):
    pattern:     str                                          = Field(..., description="Regular expression pattern to search for in file contents")
    path:        Optional[str]                               = Field(None, description="File or directory to search in (default: all files)")
    glob:        Optional[str]                               = Field(None, description="Glob pattern to filter files, e.g. '*.py'")
    output_mode: Literal["content", "files_with_matches", "count"] = Field(
        "files_with_matches", description="Output mode"
    )
    i:          bool = Field(False, alias="-i", description="Case-insensitive search")
    head_limit: int  = Field(250, description="Limit output to first N results", ge=1)

    model_config = {"populate_by_name": True}


class ImageGenerateInput(BaseModel):
    prompt: str = Field(..., description="Description of the image to generate")
    aspect_ratio: Literal["1:1", "9:16", "16:9", "4:5"] = Field(
        "1:1",
        description="Aspect ratio — 1:1 for feed, 9:16 for Stories/Reels, 16:9 for Twitter/LinkedIn, 4:5 for Instagram portrait",
    )


class ImageUploadInput(BaseModel):
    image_data: str = Field(..., description="Base64-encoded image bytes (from image_generate output)")
    storage_path: str = Field(
        ...,
        description="Relative storage path for the image, e.g. 'images/2024-01-15-instagram.png'",
    )
    mime_type: str = Field("image/png", description="MIME type of the image, e.g. 'image/png' or 'image/jpeg'")


class CronCreateInput(BaseModel):
    cron_expr: str = Field(
        ...,
        description=(
            "Standard 5-field cron expression. Minute must be 0, 15, 30, or 45 "
            "(minimum granularity is 15 minutes). Examples: '0 8 * * *' (daily 08:00), "
            "'0 */6 * * *' (every 6 hours), '0 9 * * 1' (Monday 09:00)."
        ),
    )
    message: str = Field(..., description="Message sent to the agent when the job fires, e.g. '[cron] 内容创作'")
    description: str = Field("", description="Human-readable description of what this job does")


class CronDeleteInput(BaseModel):
    job_id: str = Field(..., description="UUID of the schedule job to delete")


class CronListInput(BaseModel):
    pass


class ToolSearchInput(BaseModel):
    query: str = Field(..., description="Keyword to search for relevant tools (e.g. 'web search', 'browser')")
    limit: int = Field(5, description="Maximum number of tools to return", ge=1, le=20)


class _ToolSearchRankResponse(BaseModel):
    """Structured LLM output: exact deferred-tool names only."""

    tool_names: List[str] = Field(
        ...,
        description="Tool names exactly as listed in the catalog, most relevant first",
    )


# slug → Pydantic input class (used directly as LangChain args_schema)
_INPUT_SCHEMAS: Dict[str, Type[BaseModel]] = {
    "read":            ReadInput,
    "write":           WriteInput,
    "edit":            EditInput,
    "glob":            GlobInput,
    "grep":            GrepInput,
    "cron_create":     CronCreateInput,
    "cron_delete":     CronDeleteInput,
    "cron_list":       CronListInput,
    "image_generate":  ImageGenerateInput,
    "image_upload":    ImageUploadInput,
}


# ── Tool catalog ──────────────────────────────────────────────────────────────

_PLATFORM_TOOLS = [
    Tool(
        name="read",
        description="Read a file's content. Optionally specify limit (number of lines) and offset (start line).",
        input_schema=ReadInput.model_json_schema(),
    ),
    Tool(
        name="write",
        description="Write content to a file, creating it if it doesn't exist or overwriting it if it does.",
        input_schema=WriteInput.model_json_schema(),
    ),
    Tool(
        name="edit",
        description=(
            "Replace a string in a file with another string. "
            "old_string must match exactly. Use replace_all=true to replace every occurrence."
        ),
        input_schema=EditInput.model_json_schema(),
    ),
    Tool(
        name="glob",
        description="Find files by glob pattern (e.g. '**/*.py'). Returns matching paths sorted by modification time.",
        input_schema=GlobInput.model_json_schema(),
    ),
    Tool(
        name="grep",
        description=(
            "Search file contents with a regular expression. "
            "output_mode controls whether to return matching lines (content), "
            "file paths (files_with_matches), or counts (count)."
        ),
        input_schema=GrepInput.model_json_schema(),
    ),
    Tool(
        name="web_search",
        description="Search the web",
        input_schema={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        },
        provider_slug="composio",
        provider_config={"app_id": "TAVILY", "action": "TAVILY_SEARCH"},
    ),
    Tool(
        name="web_fetch",
        description="Fetch the contents of a web page at a given URL.",
        input_schema={
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL to fetch"}},
            "required": ["url"],
        },
        provider_slug="composio",
        provider_config={"app_id": "FIRECRAWL", "action": "SCRAPE_URL"},
    ),
    Tool(
        name="bash_tool",
        description="Run a bash command in the container",
        input_schema={
            "type": "object",
            "properties": {
                "command":     {"type": "string", "description": "Bash command to run"},
                "description": {"type": "string", "description": "Why I'm running this command"},
            },
            "required": ["command"],
        },
        provider_slug="composio",
        provider_config={"app_id": "REMOTE_BASH", "action": "EXEC_COMMAND"},
    ),
    Tool(
        name="image_generate",
        description=(
            "Generate an image from a text prompt using Gemini image generation. "
            "Returns a base64-encoded PNG. Use for social media post images, ad creatives, and branded graphics. "
            "Supports aspect ratios: 1:1 (feed), 9:16 (Stories/Reels), 16:9 (Twitter/LinkedIn), 4:5 (Instagram portrait)."
        ),
        input_schema=ImageGenerateInput.model_json_schema(),
    ),
    Tool(
        name="image_upload",
        description=(
            "Upload a base64-encoded image to Supabase Storage and return a public URL. "
            "Use after image_generate to get a URL suitable for Instagram, Facebook, or any platform "
            "that requires a hosted image URL instead of base64 data."
        ),
        input_schema=ImageUploadInput.model_json_schema(),
    ),
    Tool(
        name="cron_create",
        description=(
            "Create a recurring scheduled job. The platform will send `message` to this agent "
            "at the times defined by `cron_expr` (minimum granularity: 15 minutes). "
            "Returns a job_id for future management."
        ),
        input_schema=CronCreateInput.model_json_schema(),
    ),
    Tool(
        name="cron_delete",
        description="Delete (permanently remove) a scheduled job by its job_id.",
        input_schema=CronDeleteInput.model_json_schema(),
    ),
    Tool(
        name="cron_list",
        description="List all active scheduled jobs for the current agent and user.",
        input_schema=CronListInput.model_json_schema(),
    ),
]

PLATFORM_INTEGRATION = Integration(
    slug="platform",
    display_name="Platform",
    description="Platform-native tools built into the runtime",
    provider_slug="platform",
    provider_config={},
    deferred=False,
    tools=_PLATFORM_TOOLS,
)


def make_tool_search(deferred_tools: List[BaseTool]) -> BaseTool:
    """
    Build tool_search (injected by ToolAssembler whenever deferred tools exist).

    Ranks deferred tools with Gemini 3 Flash from a name/description catalog, then falls
    back to substring match if the API key is missing or the call fails.

    The returned dict uses the `__activate_tools__` protocol key so that
    tools_node can apply the state update without coupling to this tool's name.
    """
    async def handler(query: str, limit: int = 5) -> dict:
        matches: List[BaseTool] = []

        if deferred_tools:
            by_name = {t.name: t for t in deferred_tools}
            catalog_lines = [
                f"- {t.name}: {(t.description or '').strip().replace(chr(10), ' ')}"
                for t in deferred_tools
            ]
            catalog = "\n".join(catalog_lines)
            llm = ChatGoogleGenerativeAI(
                model="gemini-3-flash-preview",
                temperature=0,
            )
            structured = llm.with_structured_output(_ToolSearchRankResponse)
            sys = SystemMessage(
                content=(
                    "You pick which tools best match the user's search query. "
                    "You MUST only output tool names that appear verbatim in the catalog "
                    f"(the token after '- ' and before ':'). Return at most {limit} names, "
                    "most relevant first. If none apply, return an empty list."
                )
            )
            human = HumanMessage(content=f"Query:\n{query}\n\nCatalog:\n{catalog}")
            try:
                out: _ToolSearchRankResponse = await structured.ainvoke([sys, human])
                seen: set[str] = set()
                for raw in out.tool_names:
                    name = (raw or "").strip()
                    t = by_name.get(name)
                    if t is None:
                        if name:
                            logger.warning(
                                "tool_search: LLM returned unknown tool name %r (not in catalog)",
                                name,
                            )
                        continue
                    if name not in seen:
                        seen.add(name)
                        matches.append(t)
                        if len(matches) >= limit:
                            break
            except Exception as exc:
                logger.warning("tool_search Gemini ranking failed, using heuristic: %s", exc)
                matches = []

        if not matches:
            q = query.lower()
            matches = [
                t for t in deferred_tools
                if q in t.name.lower() or q in (t.description or "").lower()
            ][:limit]

        return {
            "__activate_tools__": [t.name for t in matches],
            "tools": [{"name": t.name, "description": t.description} for t in matches],
        }

    return StructuredTool(
        name="tool_search",
        description=(
            "Search for and activate deferred tools by keyword. "
            "Call this before using any search or browser tools."
        ),
        args_schema=ToolSearchInput,
        coroutine=handler,
    )


# ── Handler factories ─────────────────────────────────────────────────────────

def _make_read_handler(ctx: FileContext):
    async def handler(file_path: str, limit: Optional[int] = None, offset: Optional[int] = None):
        node = await user_files_q.read_file(
            ctx.session, ctx.blueprint_agent_id, ctx.user_id, file_path
        )
        if not node or node.type != "file":
            return {"status": False, "message": f"File not found: {file_path}"}
        content = node.content or ""
        if offset is not None or limit is not None:
            lines = content.splitlines(keepends=True)
            start = (offset - 1) if offset and offset > 0 else 0
            end = start + limit if limit is not None else None
            content = "".join(lines[start:end])
        return {"status": True, "content": content}
    return handler


def _make_write_handler(ctx: FileContext):
    async def handler(file_path: str, content: str):
        try:
            await user_files_q.write_file(
                ctx.session, ctx.blueprint_agent_id, ctx.user_id, file_path, content
            )
            return {"status": True, "message": f"Wrote {file_path}"}
        except Exception as exc:
            logger.error("write failed: %s", exc)
            return {"status": False, "message": str(exc)}
    return handler


def _make_edit_handler(ctx: FileContext):
    async def handler(file_path: str, old_string: str, new_string: str = "", replace_all: bool = False):
        result = await user_files_q.edit_file(
            ctx.session, ctx.blueprint_agent_id, ctx.user_id,
            file_path, old_string, new_string, replace_all=replace_all,
        )
        if result is None:
            return {"status": False, "message": "old_string not found or file does not exist"}
        return {"status": True, "message": f"Edited {file_path}"}
    return handler


def _make_glob_handler(ctx: FileContext):
    async def handler(pattern: str, path: Optional[str] = None):
        full_pattern = f"{path.rstrip('/')}/{pattern.lstrip('/')}" if path else pattern
        nodes = await user_files_q.glob(
            ctx.session, ctx.blueprint_agent_id, ctx.user_id, full_pattern
        )
        return {
            "status": True,
            "matches": [n.path for n in nodes],
        }
    return handler


def _make_grep_handler(ctx: FileContext):
    async def handler(
        pattern: str,
        path: Optional[str] = None,
        glob: Optional[str] = None,
        output_mode: str = "files_with_matches",
        i: bool = False,
        head_limit: int = 250,
    ):
        rows = await user_files_q.grep(
            ctx.session, ctx.blueprint_agent_id, ctx.user_id, pattern,
            case_insensitive=i,
        )

        # Filter by path prefix
        if path:
            rows = [r for r in rows if r["path"].startswith(path)]

        # Filter by glob pattern on filename
        if glob:
            rows = [r for r in rows if fnmatch.fnmatch(r["name"], glob)]

        # Apply head_limit
        rows = rows[:head_limit]

        if output_mode == "files_with_matches":
            return {"status": True, "matches": [r["path"] for r in rows]}
        elif output_mode == "count":
            return {"status": True, "count": len(rows)}
        else:  # content
            return {
                "status": True,
                "matches": [
                    {"path": r["path"], "lines": r["matches"]}
                    for r in rows
                ],
            }
    return handler


def _make_image_generate_handler(_ctx: FileContext):
    async def handler(prompt: str, aspect_ratio: str = "1:1") -> dict:
        settings = get_settings()
        api_key = getattr(settings, "GEMINI_API_KEY", None) or getattr(settings, "GOOGLE_API_KEY", None)
        if not api_key:
            return {"status": False, "message": "No Gemini API key configured"}

        _RATIO_TO_SIZE = {
            "1:1":  "1024x1024",
            "9:16": "1024x1792",
            "16:9": "1792x1024",
            "4:5":  "896x1120",
        }
        size = _RATIO_TO_SIZE.get(aspect_ratio, "1024x1024")

        try:
            client = genai.Client(api_key=api_key)
            full_prompt = f"{prompt}\n\nImage dimensions: {size}. High quality, suitable for social media."
            response = client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=full_prompt,
                config=genai_types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    b64 = base64.b64encode(part.inline_data.data).decode()
                    return {
                        "status": True,
                        "mime_type": part.inline_data.mime_type,
                        "data": b64,
                        "aspect_ratio": aspect_ratio,
                    }
            return {"status": False, "message": "No image returned from Gemini"}
        except Exception as exc:
            logger.error("image_generate failed: %s", exc)
            return {"status": False, "message": str(exc)}

    return handler


def _make_image_upload_handler(ctx: FileContext):
    async def handler(image_data: str, storage_path: str, mime_type: str = "image/png") -> dict:
        from app.storage import upload_file, get_signed_url, BUCKET

        try:
            raw = base64.b64decode(image_data)
        except Exception as exc:
            return {"status": False, "message": f"Invalid base64 data: {exc}"}

        full_path = f"{ctx.user_id}/{storage_path.lstrip('/')}"

        try:
            await upload_file(BUCKET, full_path, raw, mime_type)
        except Exception as exc:
            logger.error("image_upload failed: %s", exc)
            return {"status": False, "message": str(exc)}

        try:
            # 1-hour signed URL — sufficient for platform APIs to fetch the image
            public_url = get_signed_url(BUCKET, full_path, expires_in=3600)
        except Exception as exc:
            logger.error("image_upload get_signed_url failed: %s", exc)
            return {"status": False, "message": f"Upload succeeded but could not generate URL: {exc}"}

        return {
            "status": True,
            "storage_path": full_path,
            "public_url": public_url,
        }

    return handler


def _make_cron_create_handler(ctx: FileContext):
    async def handler(cron_expr: str, message: str, description: str = "") -> dict:
        from app.db.queries.schedules import create_schedule
        try:
            job = await create_schedule(
                ctx.session, ctx.blueprint_agent_id, ctx.user_id,
                cron_expr=cron_expr, message=message, description=description,
            )
            return {
                "status": True,
                "job_id": str(job.id),
                "next_run_at": job.next_run_at.isoformat(),
            }
        except ValueError as exc:
            return {"status": False, "message": str(exc)}
        except Exception as exc:
            logger.error("cron_create failed: %s", exc)
            return {"status": False, "message": str(exc)}
    return handler


def _make_cron_delete_handler(ctx: FileContext):
    async def handler(job_id: str) -> dict:
        from app.db.queries.schedules import delete_schedule
        try:
            deleted = await delete_schedule(
                ctx.session, uuid.UUID(job_id), ctx.blueprint_agent_id, ctx.user_id
            )
            if deleted:
                return {"status": True, "message": f"Job {job_id} deleted"}
            return {"status": False, "message": "Job not found"}
        except Exception as exc:
            logger.error("cron_delete failed: %s", exc)
            return {"status": False, "message": str(exc)}
    return handler


def _make_cron_list_handler(ctx: FileContext):
    async def handler() -> dict:
        from app.db.queries.schedules import list_schedules
        try:
            jobs = await list_schedules(ctx.session, ctx.blueprint_agent_id, ctx.user_id)
            return {
                "status": True,
                "jobs": [
                    {
                        "job_id": str(j.id),
                        "session_id": str(j.session_id) if j.session_id else None,
                        "message": j.message,
                        "cron_expr": j.cron_expr,
                        "description": j.description,
                        "enabled": j.enabled,
                        "next_run_at": j.next_run_at.isoformat(),
                        "last_run_at": j.last_run_at.isoformat() if j.last_run_at else None,
                    }
                    for j in jobs
                ],
            }
        except Exception as exc:
            logger.error("cron_list failed: %s", exc)
            return {"status": False, "message": str(exc)}
    return handler


_HANDLER_FACTORIES = {
    "read":            _make_read_handler,
    "write":           _make_write_handler,
    "edit":            _make_edit_handler,
    "glob":            _make_glob_handler,
    "grep":            _make_grep_handler,
    "image_generate":  _make_image_generate_handler,
    "image_upload":    _make_image_upload_handler,
    "cron_create":     _make_cron_create_handler,
    "cron_delete":     _make_cron_delete_handler,
    "cron_list":       _make_cron_list_handler,
}


# ── Tool assembly ─────────────────────────────────────────────────────────────

def _make_local_tool(tool: Tool, ctx: FileContext) -> BaseTool:
    return StructuredTool(
        name=tool.name,
        description=tool.description,
        args_schema=_INPUT_SCHEMAS[tool.name],
        coroutine=_HANDLER_FACTORIES[tool.name](ctx),
    )


# ── Entry point ───────────────────────────────────────────────────────────────

async def load_tools(
    integration: Integration,
    enabled_tool_slugs: Optional[List[str]],
    user_id: str,
    agent_id: uuid.UUID,
    session: AsyncSession,
    api_key: str = "",
) -> Tuple[List[BaseTool], List[BaseTool]]:
    """
    Returns (active_tools, deferred_tools).

    Tools whose name is in _DEFERRED_TOOL_NAMES are placed in deferred_tools
    and are not bound to the LLM until the user activates them via tool_search.
    """
    from app.integrations.handlers.composio import load_tools_cached

    slugs = list(enabled_tool_slugs or [])
    tools = [t for t in integration.tools if t.name in slugs]

    ctx = FileContext(
        session=session,
        blueprint_agent_id=agent_id,
        user_id=uuid.UUID(user_id),
    )
    active: List[BaseTool] = []
    deferred: List[BaseTool] = []
    composio_active_actions: List[str] = []
    composio_deferred_actions: List[Tuple[str, str]] = []  # (action, tool_name)

    for tool in tools:
        eff_provider = tool.provider_slug if tool.provider_slug is not None else integration.provider_slug
        is_deferred = tool.name in _DEFERRED_TOOL_NAMES

        if eff_provider == "platform":
            if tool.name not in _HANDLER_FACTORIES:
                logger.warning("No handler for platform tool: %s — skipping", tool.name)
                continue
            lc_tool = _make_local_tool(tool, ctx)
            (deferred if is_deferred else active).append(lc_tool)

        elif eff_provider == "composio":
            cfg = tool.provider_config if tool.provider_config is not None else integration.provider_config
            action = cfg.get("action")
            if action:
                if is_deferred:
                    composio_deferred_actions.append((action, tool.name))
                else:
                    composio_active_actions.append(action)
            else:
                logger.warning("composio tool %s has no action in provider_config", tool.name)

    if composio_active_actions:
        active.extend(await load_tools_cached(api_key, user_id, composio_active_actions))

    if composio_deferred_actions:
        deferred.extend(await load_tools_cached(api_key, user_id, [a for a, _ in composio_deferred_actions]))

    return active, deferred
