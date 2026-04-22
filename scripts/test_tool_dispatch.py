"""
Test the video_generate custom tool through the full dispatch chain:
  app.tools.execute("video_generate", input, user_id)
This is what the Anthropic agent runtime calls when the agent uses the tool.
"""

import asyncio
import os
import sys
from pathlib import Path

# Load .env before importing app modules
from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[1] / ".env")

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.tools import TOOL_DEFINITIONS, execute


def test_definitions():
    """Check video_generate is registered and schema is valid."""
    assert "video_generate" in TOOL_DEFINITIONS, "video_generate not in TOOL_DEFINITIONS"
    defn = TOOL_DEFINITIONS["video_generate"]
    assert defn["type"] == "custom"
    assert "prompt" in defn["input_schema"]["properties"]
    assert "aspect_ratio" in defn["input_schema"]["properties"]
    assert "duration_seconds" in defn["input_schema"]["properties"]
    print(f"DEFINITIONS OK — tool registered with {len(TOOL_DEFINITIONS)} total tools:")
    for name in TOOL_DEFINITIONS:
        print(f"  - {name}")


async def test_execute():
    """Call execute() the same way the agent runtime would."""
    result = await execute(
        name="video_generate",
        input={
            "prompt": (
                "Comedy style, 5 seconds. "
                "A busy restaurant kitchen, chef looks at camera and says: "
                "'This is a test.' Quick zoom out. Upbeat music."
            ),
            "aspect_ratio": "16:9",
            "duration_seconds": 5,
        },
        user_id="test-user-tool-dispatch",
        session_id=None,
    )
    print(f"\nexecute() result: {result}")
    assert result.get("status") is True, f"Expected status=True, got: {result}"
    assert result.get("url"), "Expected a URL in result"
    print(f"\nTool dispatch OK — video URL: {result['url']}")


if __name__ == "__main__":
    print("=== Testing TOOL_DEFINITIONS ===")
    test_definitions()

    print("\n=== Testing execute() dispatch ===")
    asyncio.run(test_execute())
