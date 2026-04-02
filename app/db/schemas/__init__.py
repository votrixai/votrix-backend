"""Read-model types for DAO return values (not HTTP ``app.models`` responses).

**Filesystem** — :class:`TypedDict` definitions for ``blueprint_files`` / ``user_files``
queries (Pyright/Pylance shows keys on the caller).

**Agents / orgs / end users** — queries return ORM instances from ``app.db.models``;
the mapped class is the schema.
"""

from app.db.schemas.fs import (
    FileGlobRow,
    FileGrepRow,
    FileLsRow,
    FileReadRow,
    FileStatRow,
    FileTreeRow,
)

__all__ = [
    "FileGlobRow",
    "FileGrepRow",
    "FileLsRow",
    "FileReadRow",
    "FileStatRow",
    "FileTreeRow",
]
