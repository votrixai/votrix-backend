"""ChatConversationNode — LangGraph conversation node.

Handles LLM invocation, tool execution loop, and state management.
Merged from ai-core's ChatNodeBase + ChatConversationNode into one file.
"""

import asyncio
import base64
import inspect
import json
import logging
from abc import abstractmethod
from typing import Any, Awaitable, Callable, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import END

from app.db.queries import agents as agents_q
from app.llm.chat_state import ChatState
from app.llm.model_manager import model_manager
from app.llm.prompt_sections import build_system_messages
from app.llm.types import ToolCall, ToolResponse, ToolStructure

logger = logging.getLogger(__name__)

TOOL_CALL_TIMEOUT = 600

# Agent prompt file names — when write() targets one of these, refresh the system prompt.
AGENT_FILE_NAMES = {"IDENTITY.md", "SOUL.md", "USER.md", "AGENTS.md", "BOOTSTRAP.md", "TOOLS.md"}


def _extract_tool_calls(response: AIMessage) -> List[ToolCall]:
    """Extract ToolCall objects from an AIMessage."""
    raw = getattr(response, "tool_calls", None) or []
    calls = []
    for tc in raw:
        if isinstance(tc, dict):
            calls.append(ToolCall(
                name=tc.get("name", ""),
                args=tc.get("args", {}),
                id=tc.get("id", ""),
            ))
        else:
            calls.append(ToolCall(
                name=getattr(tc, "name", ""),
                args=getattr(tc, "args", {}),
                id=getattr(tc, "id", ""),
            ))
    return calls


class ChatConversationNode:
    """Conversation node: prompt + tools + LLM invoke + tool execution loop."""

    def __init__(self, node_name: str = "conversation"):
        self.node_name = node_name
        self.tools: List[ToolStructure] = []
        self.chain = None
        self.backup_chain = None
        self._chat_tools = None

    def _build_prompt(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([
            MessagesPlaceholder(variable_name="system_messages"),
            MessagesPlaceholder(variable_name="chat_history"),
            MessagesPlaceholder(variable_name="intermediate_steps"),
        ])

    async def _build_tools(self) -> List[ToolStructure]:
        # Import here to avoid circular deps
        from app.tools.chat_tools import ChatTools
        if self._chat_tools is None:
            self._chat_tools = ChatTools()
        return self._chat_tools.get_tools()

    async def init_node(self, state: ChatState) -> None:
        self.tools = await self._build_tools()
        prompt = self._build_prompt()
        tool_defs = [t.to_structured_tool() for t in self.tools]

        primary = model_manager.get_primary()
        self.chain = (prompt | primary.bind_tools(tool_defs)) if primary else None

        backup = model_manager.get_backup()
        self.backup_chain = (prompt | backup.bind_tools(tool_defs)) if backup else None

    def _extract_text(self, response) -> str:
        content = response.content if hasattr(response, "content") else str(response)
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif hasattr(block, "text"):
                    parts.append(getattr(block, "text", ""))
            return " ".join(parts).strip() if parts else str(content)
        return str(content).strip()

    def _tool_result_to_content(self, result) -> str:
        if hasattr(result, "message") and result.message is not None:
            return str(result.message)
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False, default=str)
        return str(result) if result is not None else ""

    def _filter_args(self, func: Any, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            sig = inspect.signature(func)
            accepted = [p for p in sig.parameters if p != "self"]
            return {k: v for k, v in args.items() if k in accepted}
        except Exception:
            return args

    async def _execute_single_tool(self, call: ToolCall, tool: ToolStructure, ctx: Any) -> ToolMessage:
        logger.info("tool_call name=%s", call.name)
        try:
            filtered = self._filter_args(tool.func, call.args)
            if asyncio.iscoroutinefunction(tool.func):
                result = await asyncio.wait_for(tool.func(**filtered), timeout=TOOL_CALL_TIMEOUT)
            else:
                from app.tools.tool_context import get_tool_context, set_tool_context, reset_tool_context
                saved_ctx = get_tool_context()
                def run_sync():
                    token = set_tool_context(ctx)
                    try:
                        return tool.func(**filtered)
                    finally:
                        reset_tool_context(token)
                result = await asyncio.get_event_loop().run_in_executor(None, run_sync)
            content = self._tool_result_to_content(result)
        except asyncio.TimeoutError:
            content = f"Error: tool timed out after {TOOL_CALL_TIMEOUT}s"
        except Exception as e:
            content = f"Error: {e}"
        return ToolMessage(content=content, tool_call_id=call.id)

    async def _execute_function_calls(
        self,
        response: AIMessage,
        function_calls: List[ToolCall],
        ctx: Any,
        on_tool_event: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    ) -> List[ToolMessage]:
        # Fire AI_AGENT_MESSAGE event
        if on_tool_event:
            tc_list = [{"id": c.id, "name": c.name, "args": c.args} for c in function_calls]
            ai_content = response.content if isinstance(response.content, str) else ""
            body = json.dumps({"content": ai_content, "tool_calls": tc_list}, ensure_ascii=False)
            await on_tool_event("ai_agent", "tool:call", body)

        tool_map = {t.name: t for t in self.tools}
        tool_messages = []
        for call in function_calls:
            tool = tool_map.get(call.name)
            if not tool:
                msg = ToolMessage(content=f"Unknown tool: {call.name}", tool_call_id=call.id)
            else:
                msg = await self._execute_single_tool(call, tool, ctx)
            tool_messages.append(msg)

            if on_tool_event:
                result_body = json.dumps({
                    "content": msg.content or "",
                    "tool_call_id": call.id,
                    "name": call.name,
                }, ensure_ascii=False)
                await on_tool_event("tool_result", f"tool:result:{call.name}", result_body)

        return tool_messages

    def _agent_prompt_modified(self, function_calls: List[ToolCall]) -> bool:
        for call in function_calls:
            if call.name != "write":
                continue
            path = (call.args or {}).get("path", "")
            if not path:
                continue
            basename = path.strip().replace("\\", "/").split("/")[-1]
            if basename and any(basename.lower() == n.lower() for n in AGENT_FILE_NAMES):
                return True
        return False

    def _onboard_complete_ran(self, function_calls: List[ToolCall]) -> bool:
        for call in function_calls:
            if call.name != "votrix_run":
                continue
            cmd = (call.args or {}).get("command", "").strip().lower()
            if "votrix onboard complete" in cmd:
                return True
        return False

    async def ainvoke(self, state: ChatState) -> ChatState:
        ctx = state["assistant_context"]

        # Refresh prompt sections before each turn
        try:
            sections = await agents_q.get_prompt_sections(ctx.db_session, ctx.org_id, ctx.agent_id)
            if sections:
                ctx.prompt_sections = sections
        except Exception as e:
            logger.warning("Failed to refresh prompt sections: %s", e)

        if self.chain is None:
            await self.init_node(state)

        sys_state = state["system_agent_state"]
        args = {
            "system_messages": sys_state.get("system_messages") or [],
            "chat_history": (sys_state.get("chat_history") or []) + (sys_state.get("user_message") or []),
            "intermediate_steps": sys_state.get("intermediate_steps") or [],
        }

        from app.tools.tool_context import set_tool_context, reset_tool_context
        token = set_tool_context(ctx)
        try:
            response = await self._invoke_with_fallback(args)

            if response is None:
                state["reply_text"] = "Sorry, something went wrong. Please try again."
                state["next_node"] = END
                return state

            function_calls = _extract_tool_calls(response)

            if function_calls:
                on_tool_event = state.get("on_tool_event")
                tool_messages = await self._execute_function_calls(response, function_calls, ctx, on_tool_event)

                # Add to intermediate steps
                ai_content = response.content if isinstance(response.content, str) else ""
                tc_dicts = [c.to_call() for c in function_calls]
                sys_state.setdefault("intermediate_steps", []).append(
                    AIMessage(content=ai_content, tool_calls=tc_dicts)
                )
                for tm in tool_messages:
                    sys_state["intermediate_steps"].append(tm)

                # Record to session messages
                ctx.session_messages.append({
                    "role": "assistant", "content": ai_content,
                    **({"tool_calls": tc_dicts} if tc_dicts else {}),
                })
                for tm in tool_messages:
                    ctx.session_messages.append({
                        "role": "tool",
                        "tool_call_id": getattr(tm, "tool_call_id", ""),
                        "content": getattr(tm, "content", ""),
                    })

                # Refresh system prompt if agent files were modified
                if self._agent_prompt_modified(function_calls) or self._onboard_complete_ran(function_calls):
                    new_sections = await agents_q.get_prompt_sections(ctx.db_session, ctx.org_id, ctx.agent_id)
                    ctx.prompt_sections = new_sections
                    sys_state["system_messages"] = await build_system_messages(
                        ctx, channel_system_prompt_override=ctx.channel_system_prompt_override
                    )

                state["next_node"] = "conversation"
                return state

            reply = self._extract_text(response)
            state["reply_text"] = reply or ""
            state["next_node"] = END
            return state
        finally:
            reset_tool_context(token)

    async def _invoke_with_fallback(self, args: Dict[str, Any]) -> Optional[AIMessage]:
        if self.chain is None:
            return None
        try:
            return await self.chain.ainvoke(args)
        except Exception as e:
            logger.warning("Primary model failed, trying backup: %s", e)
            if self.backup_chain is None:
                return None
            try:
                return await self.backup_chain.ainvoke(args)
            except Exception as backup_err:
                logger.error("Backup also failed: %s", backup_err)
                return None
