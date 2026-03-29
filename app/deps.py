"""Shared FastAPI dependencies."""

from app.config import get_settings
from app.db.client import get_supabase


async def get_db():
    """Dependency that yields the Supabase client."""
    return get_supabase()
