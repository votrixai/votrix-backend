"""File system models."""

import posixpath
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class NodeType(str, Enum):
    file = "file"
    directory = "directory"


class FileEntry(BaseModel):
    """A single node in the virtual filesystem."""

    id: Optional[str] = None
    blueprint_agent_id: Optional[str] = None
    user_account_id: Optional[str] = None
    path: str
    name: str
    type: NodeType = NodeType.file
    content: Optional[str] = ""
    mime_type: str = "text/markdown"
    size_bytes: int = 0
    storage_path: Optional[str] = None
    file_class: str = "file"
    parent: str = "/"
    ext: str = ""
    depth: int = 0
    created_by: str = "system"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def derive_fields(cls, values):
        if isinstance(values, dict):
            path = values.get("path", "/")
            name = values.get("name", "")

            if "parent" not in values or not values["parent"]:
                values["parent"] = posixpath.dirname(path) or "/"
            if "ext" not in values or not values["ext"]:
                if "." in name:
                    values["ext"] = name.rsplit(".", 1)[-1]
            if "depth" not in values:
                values["depth"] = path.strip("/").count("/") + 1 if path.strip("/") else 0
            content = values.get("content") or ""
            if "size_bytes" not in values or not values["size_bytes"]:
                values["size_bytes"] = len(content.encode("utf-8")) if content else 0
            if "file_class" not in values or values["file_class"] == "file":
                values["file_class"] = classify_file(path, name)
        return values


def classify_file(path: str, name: str) -> str:
    if name == "SKILL.md":
        return "skill"
    parts = path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "skills":
        return "skill_asset"
    if name in {"IDENTITY.md", "SOUL.md", "USER.md", "AGENTS.md", "BOOTSTRAP.md", "TOOLS.md"}:
        return "prompt"
    return "file"


# ── Request models ────────────────────────────────────────────

class WriteFileRequest(BaseModel):
    path: str = Field(..., description="File path, e.g. /skills/booking/SKILL.md")
    content: Optional[str] = Field(None, description="File content (for text files)")
    mime_type: str = Field("text/markdown", description="MIME type")


class EditFileRequest(BaseModel):
    path: str = Field(..., description="File path")
    old_str: str = Field(..., description="String to find")
    new_str: str = Field(..., description="String to replace with")


class MkdirRequest(BaseModel):
    path: str = Field(..., description="Directory path")


class MoveRequest(BaseModel):
    old_path: str = Field(..., description="Current path")
    new_path: str = Field(..., description="New path")


class BulkDeleteRequest(BaseModel):
    paths: List[str] = Field(..., description="Paths to delete", min_length=1)
    recursive: bool = Field(False, description="If true, each path is treated as rm -rf")


class BulkMoveEntry(BaseModel):
    old_path: str = Field(..., description="Current path")
    new_path: str = Field(..., description="New path")


class BulkMoveRequest(BaseModel):
    moves: List[BulkMoveEntry] = Field(..., description="List of move operations", min_length=1)


class CopyRequest(BaseModel):
    source_path: str = Field(..., description="Path to copy from")
    dest_path: str = Field(..., description="Path to copy to")


# ── Response models ───────────────────────────────────────────

class FileListEntry(BaseModel):
    id: Optional[str] = None
    path: str
    name: str
    type: NodeType
    user_account_id: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: int = 0
    file_class: str = "file"
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class FileContent(BaseModel):
    path: str
    name: str
    type: NodeType
    user_account_id: Optional[str] = None
    content: Optional[str] = None
    mime_type: str = "text/markdown"
    size_bytes: int = 0
    file_class: str = "file"
    storage_path: Optional[str] = None
    download_url: Optional[str] = None


class GrepMatch(BaseModel):
    path: str
    name: str
    file_class: str
    matches: List[str]


class TreeEntry(BaseModel):
    path: str
    name: str
    type: NodeType
    file_class: str
