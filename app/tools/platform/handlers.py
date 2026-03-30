"""
Platform native tool handlers: create_file, str_replace, view, tool_search.

Stub implementations — all return None.
"""

from typing import List, Optional


async def handle_create_file(
    description: str,
    path: str,
    file_text: str,
) -> None:
    pass


async def handle_str_replace(
    description: str,
    path: str,
    old_str: str,
    new_str: str = "",
) -> None:
    pass


async def handle_view(
    description: str,
    path: str,
    view_range: Optional[List[int]] = None,
) -> None:
    pass


async def handle_tool_search(
    query: str,
    limit: int = 5,
) -> None:
    pass
