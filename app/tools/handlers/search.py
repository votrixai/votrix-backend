"""search handler — web search via SerpAPI or similar."""

import re
from typing import Optional, Dict


def parse(cmd: str) -> Optional[Dict]:
    """Parse: search <query>"""
    m = re.match(r"^search\s+(.+)$", cmd, re.IGNORECASE)
    if not m:
        return None
    return {"query": m.group(1).strip()}


async def run(query: str) -> str:
    # TODO: implement with SerpAPI or Google Custom Search
    return f"Search not yet implemented in votrix-backend. Query: {query}"
