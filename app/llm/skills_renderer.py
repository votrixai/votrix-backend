"""Render skills and module status into the system prompt."""

import json
from typing import Any, Dict, List

from app.context.assistant_context import SkillDefinition


def render_module_status(module_setup_status: Dict[str, Any]) -> str:
    if not module_setup_status:
        return ""
    return (
        "**Registry status (`registry.json`):**\n"
        "```json\n"
        f"{json.dumps(module_setup_status, ensure_ascii=False, indent=2)}\n"
        "```"
    )


def _skill_desc(skill: SkillDefinition) -> str:
    for line in (skill.description_md or "").split("\n"):
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:120]
    return skill.title


def render_skills_list(skills: List[SkillDefinition], is_admin: bool = False) -> str:
    if not skills:
        return ""
    entries: List[str] = []
    for skill in skills:
        if skill.id.endswith("-setup") or skill.id.endswith("-customer"):
            continue
        path = f"skills/{skill.id}/SKILL.md"
        entries.append(
            f"  <skill>\n"
            f"    <name>{skill.id}</name>\n"
            f"    <description>{_skill_desc(skill)}</description>\n"
            f"    <location>{path}</location>\n"
            f"  </skill>"
        )
    if not entries:
        return ""
    return "<available_skills>\n" + "\n".join(entries) + "\n</available_skills>"
