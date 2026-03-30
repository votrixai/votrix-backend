"""Build AssistantContext for chat stream.

Loads agent prompts, skills, session history from the database.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.assistant_context import (
    AssistantContext,
    ChannelInfo,
    SkillDefinition,
    UserInfo,
)
from app.context.channel_config import (
    ChannelConfig,
    compute_enabled_skills,
    resolve_channel_config,
)
from app.db.queries import blueprint_files, agents, sessions
from app.utils.chat_manager import ChatManager

logger = logging.getLogger(__name__)


async def _fetch_enabled_skill_ids(session: AsyncSession, org_id: str, agent_id: str) -> List[str]:
    """Read enabled skill IDs from registry.modules keys or from skills/ directory."""
    reg = await agents.get_registry(session, org_id, agent_id)
    modules = reg.get("modules") or {}
    return list(modules.keys())


async def _fetch_channel_configs(session: AsyncSession, org_id: str, agent_id: str) -> List[Dict]:
    """Read channel configs from agent files (channel_configs.json)."""
    file = await blueprint_files.read_file(session, org_id, agent_id, "/channel_configs.json")
    if not file or not file.get("content"):
        return []
    try:
        return json.loads(file["content"])
    except (json.JSONDecodeError, TypeError):
        return []


async def _fetch_module_setup_status(session: AsyncSession, org_id: str, agent_id: str) -> Dict:
    """Read module setup status from registry."""
    reg = await agents.get_registry(session, org_id, agent_id)
    return reg.get("modules") or {}


async def _fetch_skills(
    session: AsyncSession, skill_ids: List[str], org_id: str, agent_id: str
) -> List[SkillDefinition]:
    """Load skill definitions from blueprint_files."""
    skills = []
    for skill_id in skill_ids:
        path = f"/skills/{skill_id}/SKILL.md"
        file = await blueprint_files.read_file(session, org_id, agent_id, path)
        if not file or not file.get("content"):
            continue

        content = file["content"]
        title = skill_id.replace("-", " ").title()
        description_md = content
        audience = "both"

        if content.strip().startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1])
                    if isinstance(fm, dict):
                        title = fm.get("name", title)
                        audience = fm.get("audience", "both")
                except yaml.YAMLError:
                    pass
                description_md = parts[2].strip()

        skills.append(SkillDefinition(
            id=skill_id,
            title=title,
            description_md=description_md,
            path_under_skills=f"skills/{skill_id}/SKILL.md",
            audience=audience,
        ))
    return skills


async def build_assistant_context_for_stream(
    session: AsyncSession,
    session_id: str,
    agent_id: str,
    org_id: str,
    channel_type: str = "web",
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    locale: Optional[str] = None,
) -> AssistantContext:
    """Build AssistantContext for a chat session."""

    if not user_name:
        user_name = "Dashboard User"
    if (channel_type or "").strip().lower() == "web":
        user_name = "admin"

    (
        prompt_sections,
        agent_skill_ids,
        channel_configs,
        session_data,
        module_setup_status,
    ) = await asyncio.gather(
        agents.get_prompt_sections(session, org_id, agent_id),
        _fetch_enabled_skill_ids(session, org_id, agent_id),
        _fetch_channel_configs(session, org_id, agent_id),
        sessions.get_session(session, session_id, events_limit=150),
        _fetch_module_setup_status(session, org_id, agent_id),
    )

    channel_cfg = resolve_channel_config(channel_type, channel_configs)

    if not agent_skill_ids:
        agent_skill_ids = ["web-scraper", "google-search"]
    enabled_skill_ids = compute_enabled_skills(agent_skill_ids, channel_cfg)
    is_admin = (channel_type or "").strip().lower() == "web"

    skills = []
    if enabled_skill_ids:
        try:
            skills = await _fetch_skills(session, enabled_skill_ids, org_id, agent_id)
        except Exception as e:
            logger.error("Failed to fetch skill definitions: %s", e)
    if not is_admin:
        skills = [s for s in skills if s.audience != "admin"]

    session_events = []
    session_summary = None
    session_labels = []
    cust_id = ""
    if session_data:
        session_events = session_data.get("events") or []
        session_summary = session_data.get("summary")
        session_labels = session_data.get("labels") or []
        cust_id = session_data.get("cust_id", "")

    compaction_idx = None
    for i, ev in enumerate(session_events):
        if ev.get("event_type") == "compaction":
            compaction_idx = i
    if compaction_idx is not None:
        session_summary = session_events[compaction_idx].get("event_body") or session_summary
        session_events = session_events[compaction_idx + 1:]

    ctx = AssistantContext(
        session_id=session_id,
        agent_id=agent_id,
        org_id=org_id,
        cust_id=cust_id,
        channel_system_prompt_override=channel_cfg.system_prompt_override,
        user_info=UserInfo(
            user_id=user_id,
            user_phone=None,
            user_name=user_name,
        ),
        channel_info=ChannelInfo(
            channel_type=channel_type,
            locale=locale,
        ),
        is_admin=is_admin,
        enabled_skills=skills,
        prompt_sections=prompt_sections,
        session_messages=[],
        session_summary=session_summary,
        session_labels=session_labels,
        module_setup_status=module_setup_status,
        db_session=session,
    )
    ctx.chat_manager = ChatManager()

    try:
        for ev in session_events:
            body = ev.get("event_body", "")
            event_type = ev.get("event_type", "")

            if event_type == "user_message":
                ctx.chat_manager.record_user_message(request_id=0, user_message=body)
                ctx.session_messages.append({"role": "user", "content": body})
            elif event_type == "ai_agent_message":
                try:
                    data = json.loads(body)
                    ai_content = data.get("content", "")
                    tool_calls = data.get("tool_calls") or []
                    additional_kwargs = data.get("additional_kwargs")
                except (json.JSONDecodeError, AttributeError):
                    ai_content = body
                    tool_calls = []
                    additional_kwargs = None
                ctx.chat_manager.record_agent_message(
                    request_id=0,
                    ai_message=ai_content,
                    tool_calls=tool_calls if tool_calls else None,
                    additional_kwargs=additional_kwargs,
                )
                ctx.session_messages.append({
                    "role": "assistant",
                    "content": ai_content,
                    **({"tool_calls": tool_calls} if tool_calls else {}),
                })
            elif event_type == "tool_result":
                try:
                    data = json.loads(body)
                    content = data.get("content", "")
                    tool_call_id = data.get("tool_call_id", "")
                    func_name = data.get("name", "")
                except (json.JSONDecodeError, AttributeError):
                    content = body
                    tool_call_id = ""
                    func_name = ""
                ctx.chat_manager.record_tool_message(
                    request_id=0,
                    tool_call_id=tool_call_id,
                    func_name=func_name,
                    content=content,
                )
                ctx.session_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": content,
                })
    except Exception as e:
        logger.error("Failed to reconstruct chat history: %s", e)

    return ctx
