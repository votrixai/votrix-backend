"""
Test calling Composio Twitter tools directly via REST API.
Flow: TWITTER_UPLOAD_LARGE_MEDIA → poll status → CREATE_TWEET
"""

import asyncio
import httpx
import json

COMPOSIO_API_KEY = "ak_8vG7x_RyPvOyIXeHUSDR"
ENTITY_ID = "787acb69-7920-49d3-a02a-31b6cede6792"
API_BASE = "https://backend.composio.dev/api/v3"

# Video we already generated and stored in Supabase
VIDEO_URL = "https://pmskdncbcokccsdzrlox.supabase.co/storage/v1/object/public/public-files/test-user/videos/2b390a24-7d55-4f3d-ae20-fcd37fae5322.mp4"

HEADERS = {
    "x-api-key": COMPOSIO_API_KEY,
    "Content-Type": "application/json",
}


async def execute_action(slug: str, input: dict) -> dict:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{API_BASE}/actions/{slug}/execute",
            headers=HEADERS,
            json={"input": input, "entity_id": ENTITY_ID},
        )
        print(f"  HTTP {r.status_code}")
        return r.json()


async def main():
    # Step 1: Upload video
    print("=== Step 1: TWITTER_UPLOAD_LARGE_MEDIA ===")
    result = await execute_action("TWITTER_UPLOAD_LARGE_MEDIA", {
        "media": {"url": VIDEO_URL, "name": "cater-ai-demo.mp4"},
        "media_category": "tweet_video",
    })
    print(json.dumps(result, indent=2)[:800])

    if not result.get("successful"):
        print(f"\nFailed: {result.get('error')}")
        return

    data = result.get("data", {})
    media_id = (data.get("media_id_string") or data.get("media_id") or
                (data.get("data") or {}).get("media_id_string"))
    print(f"\nmedia_id: {media_id}")

    if not media_id:
        print("Could not extract media_id from response")
        return

    # Step 2: Poll until processing done
    print("\n=== Step 2: Poll TWITTER_GET_MEDIA_UPLOAD_STATUS ===")
    for attempt in range(15):
        await asyncio.sleep(10)
        status_result = await execute_action("TWITTER_GET_MEDIA_UPLOAD_STATUS", {
            "media_id": str(media_id),
        })
        status_data = status_result.get("data", {})
        state = (
            (status_data.get("processing_info") or {}).get("state") or
            ((status_data.get("data") or {}).get("processing_info") or {}).get("state")
        )
        print(f"  attempt {attempt+1}: state={state}")
        if state in ("succeeded", "failed", None):
            break

    if state == "failed":
        print("Media processing failed")
        return

    # Step 3: Post tweet
    print("\n=== Step 3: CREATE_TWEET ===")
    tweet_result = await execute_action("CREATE_TWEET", {
        "text": "AI-generated video test 🎬 — Cater AI superhero scene (Veo 3.1 Lite)",
        "media_media_ids": [str(media_id)],
    })
    print(json.dumps(tweet_result, indent=2)[:600])


asyncio.run(main())
