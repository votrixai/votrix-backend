"""
Video generation tool — generate videos via Gemini Veo 3 Fast, upload to Supabase Storage.
Returns a public URL. Generation is async (polling) and takes 1-5 minutes.
"""

from __future__ import annotations

import asyncio

import httpx
import structlog

from google import genai
from google.genai import types as genai_types

from app.config import get_settings
from app.storage import upload_video

logger = structlog.get_logger()

_MODEL = "veo-3.1-lite-generate-preview"
_POLL_INTERVAL_S = 10
_POLL_TIMEOUT_S = 360  # 6 minutes max

DEFINITIONS = [
    {
        "type": "custom",
        "name": "video_generate",
        "description": (
            "Generate a short video from a text prompt using Veo 3. "
            "Videos are 720p with natively generated audio (dialogue, SFX, music). "
            "Generation takes 1-5 minutes. Returns a public URL to the MP4 file. "
            "Aspect ratios: 16:9 (landscape/YouTube), 9:16 (portrait/Reels/TikTok). "
            "Duration: 4s / 6s / 8s (Veo only supports these three values)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Detailed description of the video to generate, including scene, action, mood, and audio cues.",
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["16:9", "9:16"],
                    "description": "Aspect ratio. 16:9 for landscape (YouTube/LinkedIn), 9:16 for portrait (Reels/TikTok). Defaults to 16:9.",
                },
                "duration_seconds": {
                    "type": "integer",
                    "enum": [4, 6, 8],
                    "description": "Video duration in seconds. 4s for quick clips, 6s for standard, 8s for full scenes. Defaults to 8.",
                },
                "negative_prompt": {
                    "type": "string",
                    "description": "Optional. Elements to avoid in the generated video.",
                },
            },
            "required": ["prompt"],
        },
    },
]


async def handle(name: str, input: dict, user_id: str) -> dict:
    settings = get_settings()
    if not settings.gemini_api_key:
        return {"status": False, "message": "Gemini API key not configured"}
    if not settings.supabase_url:
        return {"status": False, "message": "Supabase storage not configured"}

    prompt: str = input.get("prompt", "")
    aspect_ratio: str = input.get("aspect_ratio", "16:9")
    duration_seconds: int = input.get("duration_seconds", 8)
    negative_prompt: str | None = input.get("negative_prompt")

    try:
        client = genai.Client(api_key=settings.gemini_api_key)

        # Submit generation request
        operation = await client.aio.models.generate_videos(
            model=_MODEL,
            prompt=prompt,
            config=genai_types.GenerateVideosConfig(
                aspect_ratio=aspect_ratio,
                duration_seconds=duration_seconds,
                number_of_videos=1,
                **({"negative_prompt": negative_prompt} if negative_prompt else {}),
            ),
        )

        # Poll until done
        elapsed = 0
        while not operation.done:
            if elapsed >= _POLL_TIMEOUT_S:
                return {"status": False, "message": "Video generation timed out after 6 minutes"}
            await asyncio.sleep(_POLL_INTERVAL_S)
            elapsed += _POLL_INTERVAL_S
            operation = await client.aio.operations.get(operation)

        # Extract video URI from completed operation
        generated_videos = operation.response.generated_videos
        if not generated_videos:
            return {"status": False, "message": "No video returned from Veo"}

        video_uri: str = generated_videos[0].video.uri

        # Download video bytes from Google
        video_bytes = await _download_video(video_uri, settings.gemini_api_key)

        # Upload to Supabase Storage
        url = await upload_video(video_bytes, "video/mp4", user_id)
        return {"status": True, "url": url, "aspect_ratio": aspect_ratio, "duration_seconds": duration_seconds}

    except Exception as exc:
        logger.error("video_generate failed: %s", exc)
        return {"status": False, "message": str(exc)}


async def _download_video(uri: str, api_key: str) -> bytes:
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as http:
        resp = await http.get(uri, params={"key": api_key})
        resp.raise_for_status()
        return resp.content
