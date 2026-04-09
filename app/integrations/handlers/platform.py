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
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple, Type

from google import genai
from google.genai import types as genai_types
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool, StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.db.queries import agents as agents_q
from app.db.queries import user_files as user_files_q
from app.db.queries.schedules import create_schedule, delete_schedule, list_schedules
from app.config import get_settings
from app.integrations.handlers.composio import execute_action, initiate_connection, load_tools_cached_for_session
from app.models.integration import Integration, Tool
from app.storage import BUCKET, get_public_url, upload_file

logger = logging.getLogger(__name__)

# Tool names that are deferred (not bound to LLM until explicitly activated).
_DEFERRED_TOOL_NAMES: frozenset[str] = frozenset({"web_search", "web_fetch"})


# ── Context ───────────────────────────────────────────────────────────────────

@dataclass
class PlatformContext:
    session_factory: async_sessionmaker[AsyncSession]
    blueprint_agent_id: uuid.UUID
    user_id: uuid.UUID
    session_id: uuid.UUID
    api_key: str = ""
    official_user_id: str = ""
    # Shared mutable ref populated by ToolAssembler after all integrations load.
    # _make_tool_search_handler closes over this list; it is empty at build time
    # but fully populated by the time any user message arrives at runtime.
    deferred_tools_ref: List[BaseTool] = field(default_factory=list)


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


class WebSearchInput(BaseModel):
    query: str = Field(..., description="Search query")
    search_depth: Literal["basic", "advanced"] = Field("basic", description="basic is faster; advanced is more thorough")
    max_results: int = Field(5, ge=1, le=10, description="Maximum number of results")
    include_domains: Optional[List[str]] = Field(None, description="Restrict results to these domains")
    exclude_domains: Optional[List[str]] = Field(None, description="Exclude results from these domains")


class WebFetchInput(BaseModel):
    url: str = Field(..., description="URL to extract content from")


class WebCrawlInput(BaseModel):
    url: str = Field(..., description="Starting URL to crawl from")
    max_depth: int = Field(2, ge=1, le=5, description="Maximum link depth to follow")
    max_pages: int = Field(
        10,
        ge=1,
        le=50,
        description=(
            "Cap on how many links the crawler may process (maps to Tavily crawl `limit`). "
            "Not every site yields pages—SPAs or pages with few discoverable links often return []."
        ),
    )
    instructions: Optional[str] = Field(None, description="Natural language guidance for which pages to prioritize")


class ToolSearchInput(BaseModel):
    query: str = Field(..., description="Keyword to search for relevant tools (e.g. 'web search', 'browser')")
    limit: int = Field(5, description="Maximum number of tools to return", ge=1, le=20)


class ManageConnectionInput(BaseModel):
    toolkit: str = Field(
        ...,
        description="Composio toolkit slug to connect via OAuth, e.g. 'gmail', 'googlecalendar', 'notion'",
    )


class SearchToolkitsInput(BaseModel):
    query: Optional[str] = Field(
        None,
        description="Keyword to find relevant toolkits (name or slug). Leave empty to list all enabled toolkits.",
    )
    limit: int = Field(10, ge=1, le=50, description="Maximum number of toolkits to return")


class _ToolSearchRankResponse(BaseModel):
    """Structured LLM output: exact deferred-tool names only."""

    tool_names: List[str] = Field(
        ...,
        description="Tool names exactly as listed in the catalog, most relevant first",
    )


class _ToolkitSearchRankResponse(BaseModel):
    """Structured LLM output: exact toolkit slugs from the agent's enabled catalog."""

    toolkit_slugs: List[str] = Field(
        ...,
        description="Toolkit slugs exactly as listed in the catalog, most relevant first",
    )


# slug → Pydantic input class (used directly as LangChain args_schema)
_INPUT_SCHEMAS: Dict[str, Type[BaseModel]] = {
    "read":            ReadInput,
    "write":           WriteInput,
    "edit":            EditInput,
    "glob":            GlobInput,
    "grep":            GrepInput,
    "web_search":      WebSearchInput,
    "web_fetch":       WebFetchInput,
    "web_crawl":       WebCrawlInput,
    "cron_create":        CronCreateInput,
    "cron_delete":        CronDeleteInput,
    "cron_list":          CronListInput,
    "image_generate":     ImageGenerateInput,
    "manage_connection":  ManageConnectionInput,
    "search_toolkits":    SearchToolkitsInput,
    "tool_search":        ToolSearchInput,
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
        description=(
            "Search the web. Supports depth control (basic/advanced), result count, "
            "and domain allow/block lists."
        ),
        input_schema=WebSearchInput.model_json_schema(),
    ),
    Tool(
        name="web_fetch",
        description="Extract clean text content from a web page at a given URL.",
        input_schema=WebFetchInput.model_json_schema(),
    ),
    Tool(
        name="web_crawl",
        description=(
            "Crawl a website starting from a URL, following links across multiple pages. "
            "Use when you need content from several pages of a site, not just one. "
            "Many JavaScript-heavy sites return no pages—use web_fetch on specific URLs if crawl is empty. "
            "Supports depth and natural-language crawl instructions."
        ),
        input_schema=WebCrawlInput.model_json_schema(),
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
    Tool(
        name="tool_search",
        description=(
            "Discover and activate additional tools that are not yet available. "
            "Call this when you need a capability you currently lack. "
            "Activated tools become available immediately in the same session."
        ),
        input_schema=ToolSearchInput.model_json_schema(),
    ),
    Tool(
        name="manage_connection",
        description=(
            "Authorize a service integration for the user. "
            "Call this before using an integration that requires account access. "
            "Returns an authorization URL — share it with the user to complete the connection."
        ),
        input_schema=ManageConnectionInput.model_json_schema(),
    ),
    Tool(
        name="search_toolkits",
        description=(
            "List or search the integrations enabled for this agent. "
            "Call this to discover which services are available and what actions each supports."
        ),
        input_schema=SearchToolkitsInput.model_json_schema(),
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


def _make_tool_search_handler(ctx: PlatformContext):
    """
    Handler factory for tool_search.

    Reads ctx.deferred_tools_ref — a shared mutable list that ToolAssembler
    populates (in-place) after all integrations have been loaded. Because the
    handler is only called at runtime (on a user message), the list is fully
    populated by then even though it was empty when this handler was registered.

    Returns __activate_tools__ so tools_node can bind them to the LLM.
    """
    async def handler(query: str, limit: int = 5) -> dict:
        deferred_tools = ctx.deferred_tools_ref
        matches: List[BaseTool] = []

        if deferred_tools:
            by_name = {t.name: t for t in deferred_tools}
            catalog_lines = [
                f"- {t.name}: {(t.description or '').strip().replace(chr(10), ' ')}"
                for t in deferred_tools
            ]
            catalog = "\n".join(catalog_lines)
            llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)
            structured = llm.with_structured_output(_ToolSearchRankResponse)
            try:
                out: _ToolSearchRankResponse = await structured.ainvoke([
                    SystemMessage(content=(
                        "You pick which tools best match the user's search query. "
                        "You MUST only output tool names that appear verbatim in the catalog "
                        f"(the token after '- ' and before ':'). Return at most {limit} names, "
                        "most relevant first. If none apply, return an empty list."
                    )),
                    HumanMessage(content=f"Query:\n{query}\n\nCatalog:\n{catalog}"),
                ])
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
    return handler


# ── Handler factories ─────────────────────────────────────────────────────────

def _make_read_handler(ctx: PlatformContext):
    async def handler(file_path: str, limit: Optional[int] = None, offset: Optional[int] = None):
        async with ctx.session_factory() as session:
            node = await user_files_q.read_file(
                session, ctx.blueprint_agent_id, ctx.user_id, file_path
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


def _make_write_handler(ctx: PlatformContext):
    async def handler(file_path: str, content: str):
        try:
            async with ctx.session_factory() as session:
                await user_files_q.write_file(
                    session, ctx.blueprint_agent_id, ctx.user_id, file_path, content
                )
            return {"status": True, "message": f"Wrote {file_path}"}
        except Exception as exc:
            logger.error("write failed: %s", exc)
            return {"status": False, "message": str(exc)}
    return handler


def _make_edit_handler(ctx: PlatformContext):
    async def handler(file_path: str, old_string: str, new_string: str = "", replace_all: bool = False):
        async with ctx.session_factory() as session:
            result = await user_files_q.edit_file(
                session, ctx.blueprint_agent_id, ctx.user_id,
                file_path, old_string, new_string, replace_all=replace_all,
            )
        if result is None:
            return {"status": False, "message": "old_string not found or file does not exist"}
        return {"status": True, "message": f"Edited {file_path}"}
    return handler


def _make_glob_handler(ctx: PlatformContext):
    async def handler(pattern: str, path: Optional[str] = None):
        full_pattern = f"{path.rstrip('/')}/{pattern.lstrip('/')}" if path else f"/{pattern.lstrip('/')}"
        async with ctx.session_factory() as session:
            nodes = await user_files_q.glob(
                session, ctx.blueprint_agent_id, ctx.user_id, full_pattern
            )
        return {
            "status": True,
            "matches": [n.path for n in nodes],
        }
    return handler


def _make_grep_handler(ctx: PlatformContext):
    async def handler(
        pattern: str,
        path: Optional[str] = None,
        glob: Optional[str] = None,
        output_mode: str = "files_with_matches",
        i: bool = False,
        head_limit: int = 250,
    ):
        async with ctx.session_factory() as session:
            rows = await user_files_q.grep(
                session, ctx.blueprint_agent_id, ctx.user_id, pattern,
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


def _make_web_search_handler(ctx: PlatformContext):
    async def handler(
        query: str,
        search_depth: str = "basic",
        max_results: int = 5,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> dict:
        params = {"query": query, "search_depth": search_depth, "max_results": max_results}
        if include_domains:
            params["include_domains"] = include_domains
        if exclude_domains:
            params["exclude_domains"] = exclude_domains
        return await execute_action(ctx.api_key, ctx.official_user_id, "TAVILY_SEARCH", params)
    return handler


def _make_web_fetch_handler(ctx: PlatformContext):
    async def handler(url: str) -> dict:
        return await execute_action(ctx.api_key, ctx.official_user_id, "TAVILY_EXTRACT", {"urls": [url]})
    return handler


def _make_web_crawl_handler(ctx: PlatformContext):
    async def handler(
        url: str,
        max_depth: int = 2,
        max_pages: int = 10,
        instructions: Optional[str] = None,
    ) -> dict:
        # Composio Tavily crawl expects `limit` (links to process), not `max_pages`.
        params = {"url": url, "max_depth": max_depth, "limit": max_pages}
        if instructions:
            params["instructions"] = instructions
        return await execute_action(ctx.api_key, ctx.official_user_id, "TAVILY_CRAWL", params)
    return handler


def _make_image_generate_handler(ctx: PlatformContext):
    async def handler(prompt: str, aspect_ratio: str = "1:1") -> dict:
        settings = get_settings()
        api_key = getattr(settings, "google_api_key", None) or getattr(settings, "GEMINI_API_KEY", None)
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
                model="gemini-3.1-flash-image-preview",
                contents=full_prompt,
                config=genai_types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    raw = part.inline_data.data
                    mime_type = part.inline_data.mime_type
                    ext = mime_type.split("/")[-1]
                    storage_path = f"{ctx.user_id}/images/{uuid.uuid4()}.{ext}"
                    try:
                        await upload_file(BUCKET, storage_path, raw, mime_type)
                        public_url = get_public_url(BUCKET, storage_path)
                    except Exception as upload_exc:
                        logger.error("image_generate: upload failed: %s", upload_exc)
                        return {"status": False, "message": f"Upload failed: {upload_exc}"}
                    return {
                        "status": True,
                        "public_url": public_url,
                        "aspect_ratio": aspect_ratio,
                    }
            return {"status": False, "message": "No image returned from Gemini"}
        except Exception as exc:
            logger.error("image_generate failed: %s", exc)
            return {"status": False, "message": str(exc)}

    return handler


def _make_cron_create_handler(ctx: PlatformContext):
    async def handler(cron_expr: str, message: str, description: str = "") -> dict:
        try:
            async with ctx.session_factory() as session:
                job = await create_schedule(
                    session, ctx.blueprint_agent_id, ctx.user_id,
                    cron_expr=cron_expr, message=message, description=description,
                    session_id=ctx.session_id,
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


def _make_cron_delete_handler(ctx: PlatformContext):
    async def handler(job_id: str) -> dict:
        try:
            async with ctx.session_factory() as session:
                deleted = await delete_schedule(
                    session, uuid.UUID(job_id), ctx.blueprint_agent_id, ctx.user_id
                )
            if deleted:
                return {"status": True, "message": f"Job {job_id} deleted"}
            return {"status": False, "message": "Job not found"}
        except Exception as exc:
            logger.error("cron_delete failed: %s", exc)
            return {"status": False, "message": str(exc)}
    return handler


def _make_cron_list_handler(ctx: PlatformContext):
    async def handler() -> dict:
        try:
            async with ctx.session_factory() as session:
                jobs = await list_schedules(session, ctx.blueprint_agent_id, ctx.user_id)
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


def _make_manage_connection_handler(ctx: PlatformContext):
    async def handler(toolkit: str) -> dict:
        result = await initiate_connection(ctx.api_key, toolkit, str(ctx.user_id))
        if "error" in result:
            return {"status": False, "message": result["error"]}
        if result.get("already_connected"):
            return {
                "status": True,
                "already_connected": True,
                "message": f"{toolkit} is already connected. You can use its tools directly.",
            }
        if result.get("no_auth_required"):
            return {
                "status": True,
                "no_auth_required": True,
                "message": f"{toolkit} does not require authorization. You can use its tools directly.",
            }
        if result.get("custom_auth_required"):
            return {
                "status": False,
                "custom_auth_required": True,
                "message": f"{toolkit} requires custom OAuth credentials and cannot be connected automatically. Ask the user to configure it.",
            }
        redirect_url = result.get("redirect_url")
        if redirect_url:
            return {
                "status": True,
                "already_connected": False,
                "connection_id": result.get("connection_id"),
                "redirect_url": redirect_url,
                "message": f"Please visit this URL to connect {toolkit}: {redirect_url}",
            }
        return {
            "status": True,
            "already_connected": False,
            "connection_id": result.get("connection_id"),
            "redirect_url": None,
            "message": f"Connection initiated for {toolkit}. No browser redirect required.",
        }
    return handler


def _make_search_toolkits_handler(ctx: PlatformContext):
    async def handler(query: Optional[str] = None, limit: int = 10) -> dict:
        # lazy import to avoid circular dependency (catalog imports PLATFORM_INTEGRATION from this file)
        from app.integrations.catalog import get_cached_toolkit_meta

        # 1. Pull this agent's enabled integrations from DB, strip platform itself
        async with ctx.session_factory() as session:
            rows = await agents_q.get_agent_integrations(session, ctx.blueprint_agent_id)
        rows = [r for r in rows if r.integration_slug != "platform"]

        # 2. Enrich each row with catalog metadata
        catalog_items = []
        for r in rows:
            meta = get_cached_toolkit_meta(r.integration_slug) or {}
            catalog_items.append({
                "slug": r.integration_slug,
                "name": meta.get("name", r.integration_slug),
                "description": meta.get("description", ""),
                "enabled_tools": list(r.enabled_tool_slugs or []),
            })

        # No query → return everything
        if not query:
            return {"status": True, "toolkits": catalog_items[:limit], "total": len(catalog_items)}

        # 3. LLM ranking (same pattern as make_tool_search)
        by_slug = {item["slug"]: item for item in catalog_items}
        catalog_lines = [
            f"- {item['slug']}: {(item['name'] + '. ' + item['description']).strip()}"
            for item in catalog_items
        ]
        catalog = "\n".join(catalog_lines)

        matches: List[dict] = []
        llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0)
        structured = llm.with_structured_output(_ToolkitSearchRankResponse)
        try:
            out: _ToolkitSearchRankResponse = await structured.ainvoke([
                SystemMessage(content=(
                    "Pick which toolkits best match the query. "
                    "Only output slugs that appear verbatim in the catalog "
                    f"(token after '- ' and before ':'). Return at most {limit}, most relevant first. "
                    "If none apply, return an empty list."
                )),
                HumanMessage(content=f"Query:\n{query}\n\nCatalog:\n{catalog}"),
            ])
            seen: set[str] = set()
            for slug in out.toolkit_slugs:
                slug = (slug or "").strip()
                item = by_slug.get(slug)
                if item is None:
                    if slug:
                        logger.warning("search_toolkits: LLM returned unknown slug %r", slug)
                    continue
                if slug not in seen:
                    seen.add(slug)
                    matches.append(item)
                    if len(matches) >= limit:
                        break
        except Exception as exc:
            logger.warning("search_toolkits LLM ranking failed, using heuristic: %s", exc)

        # 4. Fallback to substring match
        if not matches:
            q = query.lower()
            matches = [
                item for item in catalog_items
                if q in item["slug"].lower()
                or q in item["name"].lower()
                or q in item["description"].lower()
            ][:limit]

        return {"status": True, "toolkits": matches, "total": len(matches)}
    return handler


_HANDLER_FACTORIES = {
    "read":               _make_read_handler,
    "write":              _make_write_handler,
    "edit":               _make_edit_handler,
    "glob":               _make_glob_handler,
    "grep":               _make_grep_handler,
    "web_search":         _make_web_search_handler,
    "web_fetch":          _make_web_fetch_handler,
    "web_crawl":          _make_web_crawl_handler,
    "image_generate":     _make_image_generate_handler,
    "cron_create":        _make_cron_create_handler,
    "cron_delete":        _make_cron_delete_handler,
    "cron_list":          _make_cron_list_handler,
    "manage_connection":  _make_manage_connection_handler,
    "search_toolkits":    _make_search_toolkits_handler,
    "tool_search":        _make_tool_search_handler,
}


# ── Tool assembly ─────────────────────────────────────────────────────────────

def _make_local_tool(tool: Tool, ctx: PlatformContext) -> BaseTool:
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
    session_factory: async_sessionmaker[AsyncSession],
    session_id: uuid.UUID = None,
    api_key: str = "",
    deferred_tools_ref: Optional[List[BaseTool]] = None,
) -> Tuple[List[BaseTool], List[BaseTool]]:
    """
    Returns (active_tools, deferred_tools).

    Tools whose name is in _DEFERRED_TOOL_NAMES are placed in deferred_tools
    and are not bound to the LLM until the user activates them via tool_search.
    """
    slugs = list(enabled_tool_slugs or [])
    tools = [t for t in integration.tools if t.name in slugs]

    ctx = PlatformContext(
        session_factory=session_factory,
        blueprint_agent_id=agent_id,
        user_id=uuid.UUID(user_id),
        session_id=session_id or uuid.uuid4(),
        api_key=api_key,
        official_user_id=get_settings().composio_official_user_id,
        deferred_tools_ref=deferred_tools_ref if deferred_tools_ref is not None else [],
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

    official_uid = get_settings().composio_official_user_id
    if composio_active_actions:
        active.extend(
            await load_tools_cached_for_session(
                api_key,
                user_id,
                composio_active_actions,
                composio_official_user_id=official_uid,
            )
        )

    if composio_deferred_actions:
        deferred.extend(
            await load_tools_cached_for_session(
                api_key,
                user_id,
                [a for a, _ in composio_deferred_actions],
                composio_official_user_id=official_uid,
            )
        )

    # Always inject meta tools regardless of enabled_tool_slugs.
    # tool_search, manage_connection, search_toolkits are unconditional platform
    # capabilities available in every session. tool_search may be pruned by
    # ToolAssembler afterward if no deferred tools exist.
    _META_TOOLS = ("tool_search", "manage_connection", "search_toolkits")
    already_active = {t.name for t in active}
    meta_defs = {t.name: t for t in _PLATFORM_TOOLS if t.name in _META_TOOLS}
    for name in _META_TOOLS:
        if name in meta_defs and name not in already_active:
            active.append(_make_local_tool(meta_defs[name], ctx))

    return active, deferred
