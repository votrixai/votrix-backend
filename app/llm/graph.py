"""LangGraph chat handler.

Builds the state graph and runs one LLM turn (with tool loop).
"""

import logging
from typing import Awaitable, Callable, List, Optional, Tuple

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph

from app.context.assistant_context import AssistantContext
from app.llm.chat_state import ChatState
from app.llm.compactor import ContextCompactor, is_context_too_long
from app.llm.conversation_node import ChatConversationNode
from app.llm.prompt_sections import build_system_messages

logger = logging.getLogger(__name__)


class ChatLangGraphHandler:
    """Chat LangGraph handler. Uses AssistantContext."""

    def __init__(self):
        self.conversation_node = ChatConversationNode(node_name="conversation")
        self.graph = self._build_graph()
        self._compactor = ContextCompactor()

    def _build_graph(self):
        workflow = StateGraph(ChatState)
        workflow.add_node("dispatcher", self.dispatcher)
        workflow.add_node("conversation", self.conversation_node.ainvoke)
        workflow.add_edge("__start__", "dispatcher")
        workflow.add_conditional_edges("dispatcher", self.next_node_selector)
        workflow.add_conditional_edges("conversation", self.next_node_selector)
        return workflow.compile()

    def dispatcher(self, state: ChatState) -> ChatState:
        state["next_node"] = "conversation"
        return state

    def next_node_selector(self, state: ChatState) -> str:
        next_node = state.get("next_node")
        if next_node is not None and next_node != END:
            return next_node
        return END

    async def _build_state(
        self,
        ctx: AssistantContext,
        user_text: str,
        request_id: int = 0,
        on_partial_reply: Optional[Callable[[str], Awaitable[None]]] = None,
        on_tool_event: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    ) -> ChatState:
        system_messages: list[BaseMessage] = await build_system_messages(
            ctx,
            channel_system_prompt_override=ctx.channel_system_prompt_override,
        )
        chat_history: list[BaseMessage] = ctx.chat_manager.build_chat_history()
        return ChatState(
            request_id=request_id,
            assistant_context=ctx,
            user_text=user_text,
            system_agent_state={
                "system_messages": system_messages,
                "user_message": [HumanMessage(content=user_text)],
                "chat_history": chat_history,
                "intermediate_steps": [],
            },
            next_node=None,
            reply_text=None,
            on_partial_reply=on_partial_reply,
            on_tool_event=on_tool_event,
        )

    async def ainvoke(
        self,
        ctx: AssistantContext,
        user_text: str,
        request_id: int = 0,
        on_partial_reply: Optional[Callable[[str], Awaitable[None]]] = None,
        on_tool_event: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    ) -> Tuple[str, List[BaseMessage]]:
        """Run one LLM turn. Returns (reply_text, intermediate_steps)."""
        await self._compactor.run_if_needed(ctx)

        state = await self._build_state(ctx, user_text, request_id, on_partial_reply, on_tool_event)

        try:
            result = await self.graph.ainvoke(state, config={"recursion_limit": 30})
        except Exception as e:
            if is_context_too_long(e):
                logger.warning("context_too_long detected, running emergency compact")
                await self._compactor.run_emergency(ctx)
                state = await self._build_state(ctx, user_text, request_id, on_partial_reply, on_tool_event)
                result = await self.graph.ainvoke(state, config={"recursion_limit": 30})
            else:
                raise

        reply_text = result.get("reply_text", "")
        intermediate_steps: List[BaseMessage] = (
            result.get("system_agent_state", {}).get("intermediate_steps") or []
        )
        return reply_text, intermediate_steps
