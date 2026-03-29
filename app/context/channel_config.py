"""Channel configuration resolution.

Migrated from ai-core common/context/channel_config.py — logic unchanged,
only imports adjusted.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel


class ChannelConfig(BaseModel):
    channel_type: str = "web"
    enabled_skills: Optional[List[str]] = None
    disabled_skills: Optional[List[str]] = None
    system_prompt_override: Optional[str] = None


def resolve_channel_config(
    channel_type: str,
    channel_configs: Optional[List[Dict]] = None,
) -> ChannelConfig:
    """Pick the ChannelConfig matching channel_type, or return default."""
    if not channel_configs:
        return ChannelConfig(channel_type=channel_type)
    for cfg in channel_configs:
        if cfg.get("channel_type", "").strip().lower() == channel_type.strip().lower():
            return ChannelConfig(**cfg)
    return ChannelConfig(channel_type=channel_type)


def compute_enabled_skills(
    agent_skill_ids: List[str],
    channel_cfg: ChannelConfig,
) -> List[str]:
    """Apply channel-level allow/block lists to the agent's skill set."""
    skills = list(agent_skill_ids)
    if channel_cfg.enabled_skills is not None:
        skills = [s for s in skills if s in channel_cfg.enabled_skills]
    if channel_cfg.disabled_skills:
        skills = [s for s in skills if s not in channel_cfg.disabled_skills]
    return skills
