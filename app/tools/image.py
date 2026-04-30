"""
Image generation tool — generate images via Gemini, upload to Supabase Storage.
Returns a public URL and a sandbox path.

Flow:
  1. Generate image bytes via Gemini
  2. Upload to Supabase → permanent public URL (recorded in asset-registry.md)
  3. Upload to Anthropic Files API → file_id
  4. Mount into session sandbox at /mnt/session/uploads/ → agent can read/view via built-in read tool

Supports optional reference images (up to 14) passed as public URLs.
Gemini does not accept URLs directly; we fetch each image and pass as inline bytes.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import List

import httpx
import structlog
from google import genai
from google.genai import types as genai_types

from app.client import get_async_client
from app.config import get_settings
from app.storage import upload_image

logger = structlog.get_logger()

_BETA = ["files-api-2025-04-14", "managed-agents-2026-04-01"]

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
            "Generate an image from a structured prompt, optionally guided by reference images. "
            "Returns a public URL to the generated image. "
            "Aspect ratios: 1:1 (feed), 9:16 (Stories/Reels), 16:9 (YouTube/LinkedIn), 4:5 (Instagram portrait). "
            "Provide up to 14 reference image URLs via reference_image_urls to steer style, composition, or content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Core scene description — who/what, where, key visual details.",
                },
                "style": {
                    "type": "string",
                    "description": (
                        "Visual style token. Always default to photographic (photorealistic) — this is the standard and produces the best results. "
                        "Supported values: "
                        "photographic, 3d-model, analog-film, anime, cinematic, comic-book, digital-art, "
                        "enhance, fantasy-art, isometric, line-art, low-poly, neon-punk, "
                        "origami, pixel-art, tile-texture."
                    ),
                },
                "mood": {
                    "type": "string",
                    "description": "Emotional atmosphere, e.g. 'serene, nostalgic', 'dramatic', 'warm and inviting'.",
                },
                "composition": {
                    "type": "string",
                    "description": "Framing / layout instructions, e.g. 'upper third open for title text', 'rule of thirds', 'centered'.",
                },
                "negative_elements": {
                    "type": "string",
                    "description": "Comma-separated list of things to exclude, e.g. 'text, watermark, people'.",
                },
                "context": {
                    "type": "string",
                    "enum": [
                        "poster-background", "banner", "icon", "social-media",
                        "product-shot", "editorial", "hero-image", "thumbnail", "illustration",
                    ],
                    "description": "Intended use case — drives composition and style adjustments.",
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["1:1", "9:16", "16:9", "4:5"],
                    "description": "Aspect ratio of the generated image. Defaults to 1:1.",
                },
                "reference_image_urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional list of public image URLs (max 14) to use as visual references. "
                        "The model will use them to guide style, composition, or subject."
                    ),
                },
            },
            "required": ["prompt"],
        },
    },
]


async def _fetch_image_bytes(url: str) -> tuple[bytes, str]:
    """Download an image from a public URL and return (bytes, mime_type)."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        mime_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        if not mime_type.startswith("image/"):
            mime_type = "image/jpeg"
        return resp.content, mime_type


async def _mount_into_sandbox(session_id: str, img_bytes: bytes, mime_type: str, filename: str) -> str | None:
    """Upload image to Anthropic Files API and mount into the session sandbox.

    Returns the sandbox path on success, None on failure (non-fatal).
    """
    try:
        client = get_async_client()
        file_tuple = (filename, img_bytes, mime_type)
        uploaded = await client.beta.files.upload(file=file_tuple, betas=_BETA)
        await client.beta.sessions.resources.add(
            session_id,
            type="file",
            file_id=uploaded.id,
            mount_path=f"/{filename}",
        )
        return f"/mnt/session/uploads/{filename}"
    except Exception as exc:
        logger.warning("sandbox mount failed — %s", exc)
        return None


_CONTEXT_HINTS = {
    "poster-background": "Leave a clean area suitable for text overlay.",
    "banner": "Wide horizontal composition, subject must read clearly at small sizes.",
    "icon": "Simple shapes, solid or white background, minimal detail.",
    "thumbnail": "Bold composition, readable at small sizes.",
    "social-media": "Eye-catching colors, strong focal point, punchy contrast.",
    "product-shot": "Clean studio lighting, sharp product focus, commercial quality.",
    "hero-image": "Dramatic composition, strong visual impact.",
}


def _build_enhanced_prompt(raw_input: dict) -> str:
    parts = [raw_input["prompt"].strip()]

    if style := raw_input.get("style"):
        parts.append(f"Style: {style}.")
    if mood := raw_input.get("mood"):
        parts.append(f"Mood: {mood}.")
    if composition := raw_input.get("composition"):
        parts.append(f"Composition: {composition}.")

    context = raw_input.get("context")
    if hint := _CONTEXT_HINTS.get(context or ""):
        parts.append(hint)

    negatives = []
    if context in ("poster-background", "banner"):
        negatives.extend(["text", "typography", "letters"])
    negatives.extend(["watermark", "signature"])

    neg_input = raw_input.get("negative_elements") or raw_input.get("negativeElements")
    if neg_input:
        for item in neg_input.split(","):
            item = item.strip()
            if item:
                negatives.append(item)

    parts.append("No " + ", no ".join(negatives) + ".")
    return " ".join(parts)


async def handle(name: str, input: dict, user_id: str, session_id: str | None = None) -> dict:
    settings = get_settings()
    if not settings.gemini_api_key:
        return {"status": False, "message": "Gemini API key not configured"}
    if not settings.supabase_url:
        return {"status": False, "message": "Supabase storage not configured"}

    prompt = _build_enhanced_prompt(input)
    aspect_ratio = input.get("aspect_ratio", "1:1")
    size = _RATIO_TO_SIZE.get(aspect_ratio, "1024x1024")
    reference_urls: List[str] = input.get("reference_image_urls") or []

    # Build the contents list: reference images first, then the text prompt.
    contents: list = []

    if reference_urls:
        for url in reference_urls[:14]:
            try:
                img_bytes, mime_type = await _fetch_image_bytes(url)
                contents.append(
                    genai_types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
                )
            except Exception as fetch_exc:
                logger.warning("Failed to fetch reference image %s — %s", url, fetch_exc)
                return {
                    "status": False,
                    "message": f"Reference image is not publicly accessible: {url}. Please provide a public URL.",
                }

    contents.append(
        genai_types.Part.from_text(
            text=f"{prompt}\n\nImage dimensions: {size}. High quality, suitable for social media."
        )
    )

    try:
        gemini = genai.Client(api_key=settings.gemini_api_key)
        response = await gemini.aio.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=contents,
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                img_data = part.inline_data.data
                img_mime = part.inline_data.mime_type
                ext = img_mime.split("/")[-1]
                filename = f"generated_{uuid.uuid4().hex[:8]}.{ext}"

                # Upload to Supabase for permanent URL
                try:
                    public_url = await upload_image(img_data, img_mime, user_id)
                except Exception as upload_exc:
                    import traceback
                    logger.warning("Supabase upload failed — %s\n%s", upload_exc, traceback.format_exc())
                    out_dir = Path(__file__).parents[2] / "scripts" / "generated_images"
                    out_dir.mkdir(exist_ok=True)
                    img_path = out_dir / filename
                    img_path.write_bytes(img_data)
                    public_url = f"file://{img_path}"

                # Mount into session sandbox so agent can view via built-in read tool
                sandbox_path = None
                if session_id:
                    sandbox_path = await _mount_into_sandbox(session_id, img_data, img_mime, filename)

                result = {"status": True, "url": public_url, "aspect_ratio": aspect_ratio}
                if sandbox_path:
                    result["path"] = sandbox_path
                return result

        return {"status": False, "message": "No image returned from Gemini"}

    except Exception as exc:
        logger.error("image_generate failed: %s", exc)
        return {"status": False, "message": str(exc)}
