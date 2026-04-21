"""
Image generation tool — generate images via Gemini, upload to Supabase Storage.
Returns a public URL.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from google import genai
from google.genai import types as genai_types

from app.config import get_settings
from app.storage import upload_image

logger = logging.getLogger(__name__)

_RATIO_TO_SIZE = {
    "1:1":  "1024x1024",
    "9:16": "1024x1792",
    "16:9": "1792x1024",
    "4:5":  "896x1120",
}

DEFINITIONS = [
    {
        "type": "custom",
        "name": "image_generate",
        "description": (
            "Generate an image from a text prompt. "
            "Returns a public URL to the generated image. "
            "Aspect ratios: 1:1 (feed), 9:16 (Stories/Reels), 16:9 (YouTube/LinkedIn), 4:5 (Instagram portrait)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Description of the image to generate.",
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["1:1", "9:16", "16:9", "4:5"],
                    "description": "Aspect ratio of the generated image. Defaults to 1:1.",
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

    prompt = input.get("prompt", "")
    aspect_ratio = input.get("aspect_ratio", "1:1")
    size = _RATIO_TO_SIZE.get(aspect_ratio, "1024x1024")

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = await client.aio.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=f"{prompt}\n\nImage dimensions: {size}. High quality, suitable for social media.",
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                try:
                    url = await upload_image(part.inline_data.data, part.inline_data.mime_type, user_id)
                except Exception as upload_exc:
                    import traceback; logger.warning("Supabase upload failed — %s\n%s", upload_exc, traceback.format_exc())
                    ext = part.inline_data.mime_type.split("/")[-1]
                    out_dir = Path(__file__).parents[2] / "scripts" / "generated_images"
                    out_dir.mkdir(exist_ok=True)
                    img_path = out_dir / f"{uuid.uuid4()}.{ext}"
                    img_path.write_bytes(part.inline_data.data)
                    url = f"file://{img_path}"
                return {"status": True, "url": url, "aspect_ratio": aspect_ratio}

        return {"status": False, "message": "No image returned from Gemini"}

    except Exception as exc:
        logger.error("image_generate failed: %s", exc)
        return {"status": False, "message": str(exc)}
