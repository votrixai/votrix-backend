"""Versioning, publish, and conflict resolution models."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ── Publish ───────────────────────────────────────────────────

class PublishResponse(BaseModel):
    version: int = Field(..., description="New version number")
    changes: int = Field(..., description="Number of files changed/deleted in this version")
    conflicts_created: int = Field(..., description="New conflicts detected")
    clean_end_users: int = Field(..., description="End users auto-synced without conflicts")


# ── Conflicts ─────────────────────────────────────────────────

class ConflictEntry(BaseModel):
    id: str
    end_user_id: str
    path: str
    version: int
    conflict_type: str         # 'both_modified' | 'base_deleted'
    base_content: Optional[str] = None
    end_user_content: Optional[str] = None
    new_content: Optional[str] = None
    status: str = "unresolved"
    created_at: Optional[datetime] = None


class ConflictSummary(BaseModel):
    total_unresolved: int
    by_path: dict = Field(default_factory=dict, description="path → count of conflicted end users")
    by_end_user: dict = Field(default_factory=dict, description="end_user_id → count of conflicted files")


class ResolveStrategy(str, Enum):
    force_admin = "force_admin"
    force_user = "force_user"
    drop_overrides = "drop_overrides"


class ResolveScope(BaseModel):
    end_user_id: Optional[str] = Field(None, description="Scope to one end user")
    path: Optional[str] = Field(None, description="Scope to one file path")


class ResolveRequest(BaseModel):
    strategy: ResolveStrategy
    scope: Optional[ResolveScope] = Field(None, description="Omit to resolve all")


class ResolveResponse(BaseModel):
    resolved: int = Field(..., description="Number of conflicts resolved")
    overrides_deleted: int = Field(0, description="Number of end user overrides deleted")


# ── Version log ───────────────────────────────────────────────

class VersionLogEntry(BaseModel):
    version: int
    action: str
    path: str
    created_at: Optional[datetime] = None


# ── End user files (admin view) ───────────────────────────────

class EndUserOverview(BaseModel):
    end_user_id: str
    override_count: int
    conflict_count: int
