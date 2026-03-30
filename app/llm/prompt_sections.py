"""Prompt sections assembly.

Builds system messages from AssistantContext. Guidelines loaded from Supabase.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from langchain_core.messages import SystemMessage

from app.context.assistant_context import AssistantContext, SkillDefinition
from app.db.queries import guidelines as guidelines_q
from app.llm.skills_renderer import render_module_status, render_skills_list

_SOUL_INTRO = (
    "If SOUL is present, embody its persona and tone. "
    "Avoid stiff, generic replies; follow its guidance "
    "unless higher-priority instructions override it."
)

# In-memory cache for guidelines (loaded once, rarely changes).
_guidelines_cache: Dict[str, str] = {}


async def _load_guidelines(ctx: AssistantContext) -> Dict[str, str]:
    """Load guidelines from DB. Cached after first call."""
    global _guidelines_cache
    if _guidelines_cache:
        return _guidelines_cache
    _guidelines_cache = await guidelines_q.get_all(ctx.db_session)
    return _guidelines_cache


def _get_timezone(ctx: AssistantContext) -> str:
    """Get timezone from module_setup_status or default."""
    if ctx.module_setup_status:
        return ctx.module_setup_status.get("timezone", "UTC")
    return "UTC"


def _apply_template(text: str, ctx: AssistantContext) -> str:
    replacements = {
        "session_id": ctx.session_id,
        "agent_id": ctx.agent_id,
        "org_id": ctx.org_id,
        "user_id": ctx.user_info.user_id or "",
        "user_name": ctx.user_info.user_name or "",
        "user_phone": ctx.user_info.user_phone or "",
        "channel_type": ctx.channel_info.channel_type,
        "locale": ctx.channel_info.locale or "",
        "timezone": _get_timezone(ctx),
    }

    def _replace(match):
        key = match.group(1).strip()
        return replacements.get(key, "")

    return re.sub(r"\{\{\s*(\w+)\s*\}\}", _replace, text)


def _build_runtime_section(ctx: AssistantContext) -> str:
    now = datetime.now()
    parts = [
        f"Today is {now.strftime('%Y-%m-%d')}.",
        f"Current time is {now.strftime('%H:%M')} (24-hour).",
        f"Channel: {ctx.channel_info.channel_type}.",
    ]
    tz = _get_timezone(ctx)
    if tz and tz != "UTC":
        parts.append(f"Timezone: {tz}.")
    if ctx.user_info.user_phone:
        parts.append(f"User phone: {ctx.user_info.user_phone}.")
    if ctx.user_info.user_name:
        parts.append(f"User name: {ctx.user_info.user_name}.")
    return " ".join(parts)


def _collect_sections(
    ctx: AssistantContext,
    guidelines: Dict[str, str],
    channel_system_prompt_override: Optional[str],
) -> List[Tuple[str, str]]:
    sections = ctx.prompt_sections
    out: List[Tuple[str, str]] = []

    # Bootstrap
    bootstrap = sections.get("bootstrap", "")
    if bootstrap:
        out.append(("First Run / Bootstrap", _apply_template(bootstrap, ctx)))

    # Identity
    identity = sections.get("identity", "")
    out.append(("Identity", _apply_template(identity, ctx) if identity else "You are a helpful AI assistant."))

    # Project Context
    if bootstrap:
        context_keys = ["soul", "user"]
    elif ctx.is_admin:
        context_keys = ["soul", "agent", "user"]
    else:
        context_keys = ["soul", "user"]
    for key in context_keys:
        text = sections.get(key, "")
        if text:
            content = _apply_template(text, ctx)
            if key == "soul":
                content = f"{_SOUL_INTRO}\n\n{content}"
            out.append((key.upper(), content))

    # Tooling
    tool_calls = guidelines.get("TOOL_CALLS", "")
    tools_text = sections.get("tools", "") if (ctx.is_admin or bootstrap) else ""
    if tool_calls or tools_text:
        parts = []
        if tool_calls:
            parts.append(tool_calls)
        if tools_text:
            parts.append(_apply_template(tools_text, ctx))
        out.append(("Tooling", "\n\n".join(parts)))

    # Skills
    skills_rules = guidelines.get("SKILLS", "") if (ctx.is_admin or bootstrap) else ""
    skills_list = render_skills_list(ctx.enabled_skills, is_admin=ctx.is_admin)
    module_status = render_module_status(ctx.module_setup_status or {}) if (ctx.is_admin or bootstrap) else ""
    if skills_rules or skills_list or module_status:
        parts = []
        if skills_rules:
            parts.append(skills_rules)
        if module_status:
            parts.append(module_status)
        if skills_list:
            parts.append(skills_list)
        out.append(("Skills", "\n\n".join(parts)))

    # Memory
    if ctx.is_admin and ctx.session_summary:
        out.append(("Memory", ctx.session_summary))

    # Channel override
    if channel_system_prompt_override:
        out.append(("Channel Context", channel_system_prompt_override))

    # Runtime
    out.append(("Runtime", _build_runtime_section(ctx)))

    return out


async def build_system_messages(
    ctx: AssistantContext,
    channel_system_prompt_override: Optional[str] = None,
) -> List[SystemMessage]:
    """Build system prompt as a list of SystemMessage, one per section."""
    guidelines = await _load_guidelines(ctx)
    sections = _collect_sections(ctx, guidelines, channel_system_prompt_override)
    return [
        SystemMessage(content=f"## {header}\n\n{body}")
        for header, body in sections
    ]
