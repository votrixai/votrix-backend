"""Session + session event queries."""

from typing import Any, Dict, List, Optional

from app.db.client import get_supabase


async def get_session(session_id: str, events_limit: int = 150) -> Optional[Dict[str, Any]]:
    """Fetch session with its most recent events."""
    resp = (
        get_supabase()
        .table("sessions")
        .select("*")
        .eq("session_id", session_id)
        .maybe_single()
        .execute()
    )
    if not resp.data:
        return None
    session = resp.data

    events_resp = (
        get_supabase()
        .table("session_events")
        .select("*")
        .eq("session_id", session_id)
        .order("seq")
        .limit(events_limit)
        .execute()
    )
    session["events"] = events_resp.data or []
    return session


async def create_session(
    session_id: str, org_id: str, agent_id: str = "default", channel_type: str = "web"
) -> Dict[str, Any]:
    row = {
        "session_id": session_id,
        "org_id": org_id,
        "agent_id": agent_id,
        "channel_type": channel_type,
    }
    resp = get_supabase().table("sessions").upsert(row, on_conflict="session_id").execute()
    return resp.data[0]


async def log_event(
    session_id: str,
    seq: int,
    event_type: str,
    event_body: str,
    event_title: Optional[str] = None,
) -> Dict[str, Any]:
    row = {
        "session_id": session_id,
        "seq": seq,
        "event_type": event_type,
        "event_body": event_body,
    }
    if event_title:
        row["event_title"] = event_title
    resp = get_supabase().table("session_events").insert(row).execute()
    return resp.data[0]


async def update_summary(session_id: str, summary: str) -> None:
    (
        get_supabase()
        .table("sessions")
        .update({"summary": summary, "updated_at": "now()"})
        .eq("session_id", session_id)
        .execute()
    )


async def update_labels(session_id: str, labels: List[str]) -> None:
    (
        get_supabase()
        .table("sessions")
        .update({"labels": labels, "updated_at": "now()"})
        .eq("session_id", session_id)
        .execute()
    )
