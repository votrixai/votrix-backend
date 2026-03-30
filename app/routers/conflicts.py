"""Publish, versioning, and conflict resolution API.

DISABLED — agent_conflicts and agent_version_log tables are commented out
in 001_initial.sql. Uncomment this module when re-enabling those tables.

Routes (disabled):
  POST   /orgs/{oid}/agents/{aid}/publish
  GET    /orgs/{oid}/agents/{aid}/conflicts
  GET    /orgs/{oid}/agents/{aid}/conflicts/summary
  POST   /orgs/{oid}/agents/{aid}/conflicts/resolve
  GET    /orgs/{oid}/agents/{aid}/version-log
  GET    /orgs/{oid}/agents/{aid}/end-users
"""

# import logging
# from typing import List, Optional
#
# from fastapi import APIRouter, Query
#
# from app.db.queries import blueprint_files, user_files, conflicts as conflict_queries
# from app.models.conflicts import (
#     ConflictEntry,
#     ConflictSummary,
#     EndUserOverview,
#     PublishResponse,
#     ResolveRequest,
#     ResolveResponse,
#     VersionLogEntry,
# )
#
# logger = logging.getLogger(__name__)
#
# router = APIRouter()
#
#
# @router.post(
#     "/orgs/{org_id}/agents/{agent_id}/publish",
#     response_model=PublishResponse,
#     summary="Publish a new agent version",
# )
# async def publish(org_id: str, agent_id: str):
#     """Bump the agent's prompt_version, detect conflicts with end user overrides,
#     and auto-sync clean end users."""
#     old_version = await conflict_queries.get_prompt_version(org_id, agent_id)
#     new_version = await conflict_queries.bump_prompt_version(org_id, agent_id)
#
#     base_files = await blueprint_files.get_all_files(org_id, agent_id)
#     base_by_path = {f["path"]: f for f in base_files}
#     changed_paths = list(base_by_path.keys())
#
#     for path in changed_paths:
#         await conflict_queries.log_version_entry(
#             org_id, agent_id, new_version, "updated", path,
#         )
#
#     overrides = await user_files.get_overrides_for_paths(org_id, agent_id, changed_paths)
#
#     conflicts_created = 0
#     conflicted_end_users = set()
#     clean_end_users = set()
#
#     for override in overrides:
#         path = override["path"]
#         end_user_id = override["end_user_id"]
#         base_file = base_by_path.get(path)
#
#         if override.get("base_version", 1) < new_version and base_file:
#             await conflict_queries.create_conflict(
#                 org_id, agent_id, new_version,
#                 end_user_id, path,
#                 conflict_type="both_modified",
#                 base_content=base_file.get("content"),
#                 end_user_content=override.get("content"),
#                 new_content=base_file.get("content"),
#             )
#             conflicts_created += 1
#             conflicted_end_users.add(end_user_id)
#         else:
#             clean_end_users.add(end_user_id)
#
#     clean_only = clean_end_users - conflicted_end_users
#     for override in overrides:
#         if override["end_user_id"] in clean_only:
#             await user_files.update_base_version(
#                 org_id, agent_id, override["end_user_id"], override["path"], new_version,
#             )
#
#     return PublishResponse(
#         version=new_version,
#         changes=len(changed_paths),
#         conflicts_created=conflicts_created,
#         clean_end_users=len(clean_only),
#     )
#
#
# @router.get(
#     "/orgs/{org_id}/agents/{agent_id}/conflicts",
#     response_model=List[ConflictEntry],
#     summary="List unresolved conflicts",
# )
# async def list_conflicts(
#     org_id: str,
#     agent_id: str,
#     end_user_id: Optional[str] = Query(None, description="Filter by end user"),
#     path: Optional[str] = Query(None, description="Filter by file path"),
# ):
#     rows = await conflict_queries.get_unresolved_conflicts(
#         org_id, agent_id, end_user_id=end_user_id, path=path,
#     )
#     return [ConflictEntry(**r) for r in rows]
#
#
# @router.get(
#     "/orgs/{org_id}/agents/{agent_id}/conflicts/summary",
#     response_model=ConflictSummary,
#     summary="Conflict summary (counts by path and end user)",
# )
# async def conflict_summary(org_id: str, agent_id: str):
#     data = await conflict_queries.get_conflict_summary(org_id, agent_id)
#     return ConflictSummary(**data)
#
#
# @router.post(
#     "/orgs/{org_id}/agents/{agent_id}/conflicts/resolve",
#     response_model=ResolveResponse,
#     summary="Force-resolve conflicts",
# )
# async def resolve_conflicts(org_id: str, agent_id: str, body: ResolveRequest):
#     """Resolve conflicts using the chosen strategy."""
#     scope_end_user = body.scope.end_user_id if body.scope else None
#     scope_path = body.scope.path if body.scope else None
#
#     current_version = await conflict_queries.get_prompt_version(org_id, agent_id)
#
#     conflicts = await conflict_queries.get_unresolved_conflicts(
#         org_id, agent_id, end_user_id=scope_end_user, path=scope_path,
#     )
#
#     overrides_deleted = 0
#
#     if body.strategy.value == "force_admin":
#         for c in conflicts:
#             deleted = await user_files.delete_overrides(
#                 org_id, agent_id, c["end_user_id"], [c["path"]],
#             )
#             overrides_deleted += deleted
#         resolved = await conflict_queries.resolve_conflicts(
#             org_id, agent_id, scope_end_user, scope_path,
#             resolution_status="resolved_keep_admin",
#         )
#
#     elif body.strategy.value == "force_user":
#         for c in conflicts:
#             await user_files.update_base_version(
#                 org_id, agent_id, c["end_user_id"], c["path"], current_version,
#             )
#         resolved = await conflict_queries.resolve_conflicts(
#             org_id, agent_id, scope_end_user, scope_path,
#             resolution_status="resolved_keep_user",
#         )
#
#     elif body.strategy.value == "drop_overrides":
#         affected_users = set()
#         if scope_end_user:
#             affected_users.add(scope_end_user)
#         else:
#             for c in conflicts:
#                 affected_users.add(c["end_user_id"])
#
#         for uid in affected_users:
#             paths = [scope_path] if scope_path else None
#             deleted = await user_files.delete_overrides(
#                 org_id, agent_id, uid, paths,
#             )
#             overrides_deleted += deleted
#
#         resolved = await conflict_queries.resolve_conflicts(
#             org_id, agent_id, scope_end_user, scope_path,
#             resolution_status="resolved_keep_admin",
#         )
#     else:
#         resolved = 0
#
#     return ResolveResponse(resolved=resolved, overrides_deleted=overrides_deleted)
#
#
# @router.get(
#     "/orgs/{org_id}/agents/{agent_id}/version-log",
#     response_model=List[VersionLogEntry],
#     summary="Get version changelog",
# )
# async def version_log(
#     org_id: str,
#     agent_id: str,
#     version: Optional[int] = Query(None, description="Filter by version number"),
# ):
#     rows = await conflict_queries.get_version_log(org_id, agent_id, version=version)
#     return [VersionLogEntry(**r) for r in rows]
#
#
# @router.get(
#     "/orgs/{org_id}/agents/{agent_id}/end-users",
#     response_model=List[EndUserOverview],
#     summary="End user overview (overrides + conflicts per user)",
# )
# async def end_user_overview(org_id: str, agent_id: str):
#     rows = await conflict_queries.get_end_user_overview(org_id, agent_id)
#     return [EndUserOverview(**r) for r in rows]
