"""Quick test: generate a video with Veo 3.1 Lite and upload to Supabase Storage."""

import asyncio
import os
import uuid
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))

import httpx
from google import genai
from google.genai import types as genai_types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
BUCKET = "public-files"
MODEL = "veo-3.1-lite-generate-preview"
POLL_INTERVAL_S = 10
POLL_TIMEOUT_S = 360

IMAGE_URL = "https://pmskdncbcokccsdzrlox.supabase.co/storage/v1/object/public/public-files/787acb69-7920-49d3-a02a-31b6cede6792/images/9cc5c661-fbb1-41c6-8db4-226d712ec812.jpeg"

PROMPT = """\
Cinematic superhero style, 8 seconds.

Packed restaurant, phones ringing everywhere,
staff running around overwhelmed.

Suddenly — dramatic wind, golden light from above.

A glowing phone screen appears floating in mid-air,
it picks up automatically.

A smooth AI voice says:
"Thank you for calling. I'll take your order."

Staff all stop and stare in awe.

Epic orchestral music, slow motion, cinematic.\
"""


async def upload_to_supabase(video_bytes: bytes, user_id: str) -> str:
    path = f"{user_id}/videos/{uuid.uuid4()}.mp4"
    async with httpx.AsyncClient(timeout=300) as http:
        resp = await http.post(
            f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{path}",
            content=video_bytes,
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "video/mp4",
                "x-upsert": "true",
            },
        )
        resp.raise_for_status()
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"


async def main():
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not set"); return
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("SUPABASE_URL / SUPABASE_SERVICE_KEY not set"); return

    client = genai.Client(api_key=GEMINI_API_KEY)

    # Download reference image from Supabase
    print(f"Downloading reference image...")
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as http:
        img_resp = await http.get(IMAGE_URL)
        img_resp.raise_for_status()
        image_bytes = img_resp.content
        mime_type = img_resp.headers.get("content-type", "image/jpeg").split(";")[0]
    print(f"  Image: {len(image_bytes) / 1024:.1f} KB, {mime_type}")

    print(f"Submitting to {MODEL} with image as first frame...")
    operation = await client.aio.models.generate_videos(
        model=MODEL,
        prompt=PROMPT,
        image=genai_types.Image(image_bytes=image_bytes, mime_type=mime_type),
        config=genai_types.GenerateVideosConfig(
            aspect_ratio="16:9",
            duration_seconds=8,
            number_of_videos=1,
        ),
    )
    print(f"  operation: {operation.name}")

    elapsed = 0
    while not operation.done:
        if elapsed >= POLL_TIMEOUT_S:
            print("Timed out"); return
        print(f"  polling... ({elapsed}s)")
        await asyncio.sleep(POLL_INTERVAL_S)
        elapsed += POLL_INTERVAL_S
        operation = await client.aio.operations.get(operation)

    videos = operation.response.generated_videos
    if not videos:
        print("No videos returned"); return

    video_uri = videos[0].video.uri
    print(f"Done! Downloading from Google...")

    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as http:
        resp = await http.get(video_uri, params={"key": GEMINI_API_KEY})
        resp.raise_for_status()
        video_bytes = resp.content
    print(f"  Downloaded {len(video_bytes) / 1024 / 1024:.1f} MB")

    print("Uploading to Supabase...")
    public_url = await upload_to_supabase(video_bytes, user_id="test-user")
    print(f"\n Public URL:\n  {public_url}\n")


asyncio.run(main())
