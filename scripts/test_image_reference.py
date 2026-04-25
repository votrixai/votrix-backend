"""
Test: reference image vs no reference image for Cater AI product promotion.

Generates two images and saves to scripts/generated_images/:
  - caterai_no_ref.png     — pure prompt, no reference
  - caterai_with_ref.png   — same prompt + Unsplash restaurant-phone reference image
"""

import asyncio
import os
import uuid
from pathlib import Path

import httpx
from google import genai
from google.genai import types as genai_types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OUT_DIR = Path(__file__).parent / "generated_images"

# Reference image: smartphone + food ordering context (Unsplash, no auth needed)
REFERENCE_URL = "https://images.unsplash.com/photo-1760888549280-4aef010720bd?w=1080&q=80"

PROMPT = """\
A professional social media marketing image for Cater AI, an AI phone receptionist for restaurants.

Scene: A busy, warm modern restaurant interior. In the foreground, a sleek smartphone shows an
incoming call with a glowing AI waveform animation on the screen — symbolising the AI answering
the call automatically. The restaurant background shows happy diners at tables and staff at a counter.

Style: Commercial editorial photography, crisp and modern. Warm amber restaurant lighting mixed
with cool blue tech glow from the phone screen.

Composition: Phone is center-left, restaurant background fills the right two-thirds. Leave clean
open space in the upper 30% of the frame for text overlay.

Mood: Confident, modern, trustworthy. Conveys "never miss a call again."

Colors: Predominantly warm whites and ambers (restaurant) with one pop of deep navy blue from the
phone screen glow. Professional, inviting.

4:5 portrait aspect ratio, 896x1120, high quality, suitable for Instagram feed.
"""


async def fetch_image_bytes(url: str) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        mime = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        if not mime.startswith("image/"):
            mime = "image/jpeg"
        return resp.content, mime


async def generate(label: str, use_reference: bool) -> Path:
    client = genai.Client(api_key=GEMINI_API_KEY)
    contents: list = []

    if use_reference:
        print(f"[{label}] Fetching reference image...")
        img_bytes, mime = await fetch_image_bytes(REFERENCE_URL)
        contents.append(genai_types.Part.from_bytes(data=img_bytes, mime_type=mime))

    contents.append(genai_types.Part.from_text(text=PROMPT))

    print(f"[{label}] Calling Gemini...")
    response = await client.aio.models.generate_content(
        model="gemini-3.1-flash-image-preview",
        contents=contents,
        config=genai_types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            ext = part.inline_data.mime_type.split("/")[-1]
            fname = f"caterai_{'with_ref' if use_reference else 'no_ref'}.{ext}"
            out_path = OUT_DIR / fname
            out_path.write_bytes(part.inline_data.data)
            print(f"[{label}] Saved → {out_path}")
            return out_path

    raise RuntimeError(f"[{label}] No image in response")


async def main():
    OUT_DIR.mkdir(exist_ok=True)
    if not GEMINI_API_KEY:
        raise SystemExit("GEMINI_API_KEY not set")

    # Run both in parallel
    no_ref, with_ref = await asyncio.gather(
        generate("NO REF ", use_reference=False),
        generate("WITH REF", use_reference=True),
    )

    print("\n=== Done ===")
    print(f"No reference:   {no_ref}")
    print(f"With reference: {with_ref}")


if __name__ == "__main__":
    asyncio.run(main())
