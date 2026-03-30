"""Versioning, publish, and conflict resolution models.

DISABLED — agent_conflicts and agent_version_log tables are commented out
in 001_initial.sql. Uncomment this module when re-enabling those tables.
"""

# from datetime import datetime
# from enum import Enum
# from typing import List, Optional
#
# from pydantic import BaseModel, Field
#
#
# class PublishResponse(BaseModel):
#     version: int = Field(..., description="New version number")
#     changes: int = Field(..., description="Number of files changed/deleted in this version")
#     conflicts_created: int = Field(..., description="New conflicts detected")
#     clean_end_users: int = Field(..., description="End users auto-synced without conflicts")
#
#
# class ConflictEntry(BaseModel):
#     id: str
#     end_user_id: str
#     path: str
#     version: int
#     conflict_type: str
#     base_content: Optional[str] = None
#     end_user_content: Optional[str] = None
#     new_content: Optional[str] = None
#     status: str = "unresolved"
#     created_at: Optional[datetime] = None
#
#
# class ConflictSummary(BaseModel):
#     total_unresolved: int
#     by_path: dict = Field(default_factory=dict)
#     by_end_user: dict = Field(default_factory=dict)
#
#
# class ResolveStrategy(str, Enum):
#     force_admin = "force_admin"
#     force_user = "force_user"
#     drop_overrides = "drop_overrides"
#
#
# class ResolveScope(BaseModel):
#     end_user_id: Optional[str] = Field(None)
#     path: Optional[str] = Field(None)
#
#
# class ResolveRequest(BaseModel):
#     strategy: ResolveStrategy
#     scope: Optional[ResolveScope] = Field(None)
#
#
# class ResolveResponse(BaseModel):
#     resolved: int = Field(..., description="Number of conflicts resolved")
#     overrides_deleted: int = Field(0, description="Number of end user overrides deleted")
#
#
# class VersionLogEntry(BaseModel):
#     version: int
#     action: str
#     path: str
#     created_at: Optional[datetime] = None
#
#
# class EndUserOverview(BaseModel):
#     end_user_id: str
#     override_count: int
#     conflict_count: int
