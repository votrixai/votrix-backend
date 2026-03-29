"""File system models."""

import posixpath
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, model_validator


class NodeType(str, Enum):
    file = "file"
    directory = "directory"


class AccessLevel(str, Enum):
    owner = "owner"
    org_read = "org_read"
    org_write = "org_write"


class FileEntry(BaseModel):
    """A single node in the virtual filesystem."""

    id: Optional[str] = None
    org_id: str
    agent_id: str = "default"
    path: str
    name: str
    type: NodeType = NodeType.file
    access_level: AccessLevel = AccessLevel.org_read
    content: str = ""
    mime_type: str = "text/markdown"
    size_bytes: int = 0
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
        """Auto-derive parent, ext, depth, size_bytes, file_class from path/name/content."""
        if isinstance(values, dict):
            path = values.get("path", "/")
            name = values.get("name", "")

            # parent
            if "parent" not in values or not values["parent"]:
                values["parent"] = posixpath.dirname(path) or "/"

            # ext
            if "ext" not in values or not values["ext"]:
                if "." in name:
                    values["ext"] = name.rsplit(".", 1)[-1]

            # depth
            if "depth" not in values:
                values["depth"] = path.strip("/").count("/") + 1 if path.strip("/") else 0

            # size_bytes
            content = values.get("content", "")
            if "size_bytes" not in values or not values["size_bytes"]:
                values["size_bytes"] = len(content.encode("utf-8")) if content else 0

            # file_class
            if "file_class" not in values or values["file_class"] == "file":
                values["file_class"] = classify_file(path, name)

        return values


class GrepMatch(BaseModel):
    path: str
    name: str
    file_class: str
    matches: List[str]


class FileTree(BaseModel):
    path: str
    name: str
    type: NodeType
    children: List["FileTree"] = []


def classify_file(path: str, name: str) -> str:
    if name == "SKILL.md":
        return "skill"
    parts = path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "skills":
        return "skill_asset"
    if name in {"IDENTITY.md", "SOUL.md", "USER.md", "AGENTS.md", "BOOTSTRAP.md", "TOOLS.md"}:
        return "prompt"
    return "file"
