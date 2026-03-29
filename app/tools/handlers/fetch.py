"""fetch handler — HTTP fetch for URLs."""

import re
from typing import Optional, Dict

import httpx


def parse(cmd: str) -> Optional[Dict]:
    """Parse: fetch <url>"""
    m = re.match(r"^fetch\s+(https?://\S+)$", cmd, re.IGNORECASE)
    if not m:
        return None
    return {"url": m.group(1).strip()}


async def run(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, follow_redirects=True)
            content_type = resp.headers.get("content-type", "")
            if "text" in content_type or "json" in content_type:
                body = resp.text[:10_000]
                return f"HTTP {resp.status_code}\n{body}"
            return f"HTTP {resp.status_code} (binary: {content_type}, {len(resp.content)} bytes)"
    except Exception as e:
        return f"Error fetching {url}: {e}"
