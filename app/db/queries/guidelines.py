"""Guidelines queries — global singleton prompt guidelines."""

from typing import Any, Dict, List, Optional

from app.db.client import get_supabase

TABLE = "guidelines"


async def get(guideline_id: str) -> Optional[str]:
    resp = (
        get_supabase()
        .table(TABLE)
        .select("content")
        .eq("guideline_id", guideline_id)
        .maybe_single()
        .execute()
    )
    if not resp.data:
        return None
    return resp.data["content"]


async def get_all() -> Dict[str, str]:
    resp = get_supabase().table(TABLE).select("guideline_id, content").execute()
    return {row["guideline_id"]: row["content"] for row in (resp.data or [])}


async def upsert(guideline_id: str, content: str) -> None:
    row = {"guideline_id": guideline_id, "content": content}
    get_supabase().table(TABLE).upsert(row, on_conflict="guideline_id").execute()


async def list_all() -> List[Dict[str, Any]]:
    resp = get_supabase().table(TABLE).select("guideline_id, updated_at").execute()
    return resp.data or []
