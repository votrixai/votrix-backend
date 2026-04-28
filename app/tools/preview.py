"""show_post_preview — surfaces generated images with caption for user review in the chat UI."""

from __future__ import annotations

import structlog

from app.tools.file import _find_file

logger = structlog.get_logger()

DEFINITIONS = [
    {
        "type": "custom",
        "name": "show_post_preview",
        "description": (
            "Show generated images and caption to the user for review inside the chat UI. "
            "Pass the output paths under /mnt/session/outputs/ — the backend resolves them automatically. "
            "Call AFTER writing all image files. No need to call download_file first."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "slides": {
                    "type": "array",
                    "description": "Ordered list of images. Empty array for text-only posts.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Sandbox path under /mnt/session/outputs/, e.g. '/mnt/session/outputs/slide_1.png'",
                            },
                            "label": {
                                "type": "string",
                                "description": "Slide label shown in the UI, e.g. 'Cover', 'Slide 2', 'CTA'",
                            },
                        },
                        "required": ["path", "label"],
                    },
                },
                "caption": {
                    "type": "string",
                    "description": "Full post caption / copy",
                },
                "hashtags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Hashtag list, with or without leading #",
                },
            },
            "required": ["slides", "caption", "hashtags"],
        },
    }
]


async def handle(name: str, input: dict, user_id: str, session_id: str | None = None) -> dict:
    if name != "show_post_preview":
        return {"error": f"Unknown preview tool: {name}"}
    if not session_id:
        return {"error": "session_id is required"}

    slides_in = input.get("slides") or []
    resolved_slides = []
    for slide in slides_in:
        path = (slide.get("path") or "").strip()
        label = slide.get("label", "")
        file_meta, err = await _find_file(path, session_id)
        if err:
            logger.warning("[show_post_preview] could not resolve %s: %s", path, err)
            resolved_slides.append({"file_id": None, "label": label, "error": err.get("error")})
        else:
            resolved_slides.append({"file_id": file_meta.id, "label": label})

    return {
        "ok": True,
        "slides": resolved_slides,
        "caption": input.get("caption", ""),
        "hashtags": input.get("hashtags") or [],
    }
