"""Execute a single scheduled job by running the agent with its trigger message."""

import logging
import uuid
from typing import Any, Dict, Optional, Tuple

from app.db.engine import session_scope
from app.db.models.schedules import UserAgentSchedule
from app.db.queries import agents as agents_q
from app.db.queries import notifications as notifications_q
from app.db.queries import schedules as schedules_q
from app.db.queries import sessions as sessions_q
from app.llm.engine.agent_engine import AgentEngine
from app.models.session import SessionEventType

logger = logging.getLogger(__name__)

# Maps cron trigger message → (notification_type, title, body)
_NOTIFICATION_TEMPLATES: Dict[str, Tuple[str, str, str]] = {
    "[cron] 内容创作": (
        "cron_content",
        "内容草稿已准备好",
        "新内容草稿已生成，点击查看并发布",
    ),
    "[cron] 评论巡查": (
        "cron_review",
        "有新评论待处理",
        "检测到新评论，请查看并回复",
    ),
    "[cron] 数据汇报": (
        "cron_analytics",
        "数据报告已就绪",
        "本期表现报告已生成，点击查看",
    ),
}

_DEFAULT_NOTIFICATION = ("cron_task", "自动化任务已完成", "后台任务已完成")


def _notification_payload(job: UserAgentSchedule, notification_id: uuid.UUID) -> Dict[str, Any]:
    ntype, title, body = _NOTIFICATION_TEMPLATES.get(job.message, _DEFAULT_NOTIFICATION)
    return {
        "type": "notification",
        "id": str(notification_id),
        "notification_type": ntype,
        "title": title,
        "body": body,
        "metadata": {
            "job_id": str(job.id),
            "session_id": str(job.session_id) if job.session_id else None,
        },
    }


async def run_job(job: UserAgentSchedule) -> None:
    """
    Execute one scheduled job.

    Each job has a fixed session_id — all firings share the same LangGraph
    thread, giving the agent continuity across runs.

    After completion (success or failure), a UserNotification is created
    and pushed to any active WebSocket connections for the user.
    """
    job_label = f"job={job.id} session={job.session_id} agent={job.agent_id} msg={job.message!r}"

    async with session_scope() as db:
        if schedules_q.is_stale(job):
            logger.warning("Skipping stale cron %s (overdue > 30 min)", job_label)
            await schedules_q.mark_job_done(db, job)
            return

        agent = await agents_q.get_agent(db, job.agent_id)
        if not agent:
            logger.error("Cron %s: agent not found — disabling job", job_label)
            await schedules_q.disable_schedule(db, job.id, job.agent_id, job.user_id)
            return

        await sessions_q.append_event(
            db,
            job.session_id,
            event_type=SessionEventType.user_message,
            event_body=job.message,
        )

        engine = AgentEngine(job.agent_id, job.user_id, job.session_id, db)
        await engine.setup(agent)

        logger.info("Cron firing: %s", job_label)
        ai_tokens: list[str] = []
        try:
            async for event in engine.astream(job.message):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if isinstance(content, str):
                        ai_tokens.append(content)
                    elif isinstance(content, list):
                        ai_tokens.extend(
                            b.get("text", "") for b in content
                            if isinstance(b, dict) and b.get("type") == "text"
                        )

                elif kind == "on_tool_start":
                    d = event.get("data") or {}
                    await sessions_q.append_event(
                        db,
                        job.session_id,
                        event_type=SessionEventType.tool_start,
                        event_title=event["name"],
                        event_body=str(d.get("input", "")),
                    )

                elif kind == "on_tool_end":
                    d = event.get("data") or {}
                    await sessions_q.append_event(
                        db,
                        job.session_id,
                        event_type=SessionEventType.tool_end,
                        event_title=event["name"],
                        event_body=str(d.get("output", "")),
                    )

            reply = "".join(ai_tokens)
            if reply:
                await sessions_q.append_event(
                    db,
                    job.session_id,
                    event_type=SessionEventType.ai_message,
                    event_body=reply,
                )
            logger.info("Cron done: %s", job_label)
        except Exception:
            logger.exception("Cron failed: %s", job_label)

        await schedules_q.mark_job_done(db, job)

        # Create persistent notification
        ntype, title, body = _NOTIFICATION_TEMPLATES.get(job.message, _DEFAULT_NOTIFICATION)
        notification = await notifications_q.create_notification(
            db,
            user_id=job.user_id,
            agent_id=job.agent_id,
            title=title,
            body=body,
            type=ntype,
            metadata={
                "job_id": str(job.id),
                "session_id": str(job.session_id) if job.session_id else None,
            },
        )

    # Push to any active WebSocket connections (outside DB session — fire and forget)
    from app.notifications.manager import notification_manager
    payload = _notification_payload(job, notification.id)
    await notification_manager.push(job.user_id, payload)
