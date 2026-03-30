"""Shared FastAPI dependencies."""

from app.db.engine import get_session

__all__ = ["get_session"]
