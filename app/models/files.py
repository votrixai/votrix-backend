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
    org_id: str
    agent_id: str = "default"
    end_user_id: Optional[str] = None
    path: str
    name: str
    type: NodeType = NodeType.file
    end_user_perm: str = "r"
    content: str = ""
    mime_type: str = "text/markdown"
    size_bytes: int = 0
    file_class: str = "file"
    base_version: int = 1
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
            content = values.get("content", "")
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


def default_end_user_perm(path: str, name: str) -> str:
    """Default end_user_perm based on file type."""
    if name in {"IDENTITY.md", "TOOLS.md", "BOOTSTRAP.md"}:
        return "r"
    if name == "SKILL.md":
        return "r"
    if name in {"SOUL.md", "USER.md"}:
        return "rw"
    if name == "registry.json":
        return "none"
    return "r"


# ── Request models ────────────────────────────────────────────

class WriteFileRequest(BaseModel):
    path: str = Field(..., description="File path, e.g. /skills/booking/SKILL.md")
    content: str = Field(..., description="File content")
    mime_type: str = Field("text/markdown", description="MIME type")
    end_user_perm: str = Field("r", description="End user permission: 'none' | 'r' | 'rw'")


class EditFileRequest(BaseModel):
    path: str = Field(..., description="File path")
    old_str: str = Field(..., description="String to find")
    new_str: str = Field(..., description="String to replace with")


class MkdirRequest(BaseModel):
    path: str = Field(..., description="Directory path")


class MoveRequest(BaseModel):
    old_path: str = Field(..., description="Current path")
    new_path: str = Field(..., description="New path")


# ── Response models ───────────────────────────────────────────

class FileListEntry(BaseModel):
    id: Optional[str] = None
    path: str
    name: str
    type: NodeType
    end_user_perm: Optional[str] = None
    end_user_id: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: int = 0
    file_class: str = "file"
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class FileContent(BaseModel):
    path: str
    name: str
    type: NodeType
    end_user_perm: Optional[str] = None
    end_user_id: Optional[str] = None
    content: str
    mime_type: str = "text/markdown"
    size_bytes: int = 0
    file_class: str = "file"


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
