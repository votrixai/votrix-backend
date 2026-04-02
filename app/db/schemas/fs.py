"""Typed return shapes shared by blueprint_files and user_files queries."""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict
from uuid import UUID

from app.db.models.blueprint_files import NodeType


class FileLsRow(TypedDict):
    """``ls()`` directory listing entry."""

    id: UUID
    path: str
    name: str
    type: NodeType
    mime_type: str
    size_bytes: int
    file_class: str
    created_by: str
    updated_at: datetime


class FileReadRow(TypedDict, total=False):
    """``read_file()`` row; ``total=False`` allows optional keys if queries differ."""

    content: str
    mime_type: str
    size_bytes: int
    file_class: str
    name: str
    type: NodeType
    path: str
    storage_path: str | None


class FileStatRow(TypedDict):
    """``stat()`` metadata."""

    id: UUID
    path: str
    name: str
    type: NodeType
    mime_type: str
    size_bytes: int
    file_class: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class FileTreeRow(TypedDict):
    """One node from ``tree()`` (flat list)."""

    path: str
    name: str
    type: NodeType
    file_class: str


class FileGlobRow(TypedDict):
    """One row from ``glob()``."""

    path: str
    name: str
    type: NodeType
    file_class: str
    size_bytes: int
    updated_at: datetime


class FileGrepRow(TypedDict):
    """One aggregate match group from ``grep()``."""

    path: str
    name: str
    file_class: str
    matches: list[str]
