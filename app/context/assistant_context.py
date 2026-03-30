"""AssistantContext — connection-level context for the chat assistant.

Built once when the client sends a chat request, reused across all LLM turns.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.utils.chat_manager import ChatManager


class UserInfo(BaseModel):
    user_id: Optional[str] = None
    user_phone: Optional[str] = None
    user_name: Optional[str] = None


class ChannelInfo(BaseModel):
    channel_type: str = "web"
    locale: Optional[str] = None


class SkillDefinition(BaseModel):
    id: str
    title: str
    description_md: str
    path_under_skills: Optional[str] = None
    audience: str = "both"


class AssistantContext(BaseModel):
    session_id: str
    agent_id: str
    org_id: str
    cust_id: str = ""

    user_info: UserInfo = UserInfo()
    channel_info: ChannelInfo = ChannelInfo()

    is_admin: bool = False
    enabled_skills: List[SkillDefinition] = []
    enabled_tools: Optional[List[str]] = None
    module_setup_status: Optional[Dict[str, Any]] = None
    prompt_sections: Dict[str, str] = {}
    channel_system_prompt_override: Optional[str] = None

    session_messages: List[Dict[str, Any]] = []
    session_summary: Optional[str] = None
    session_labels: List[str] = []

    chat_manager: ChatManager = Field(default_factory=ChatManager)

    db_session: Any = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
