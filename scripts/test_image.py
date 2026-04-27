import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.tools.image import handle, _build_enhanced_prompt

async def main():
    raw_input = {
        "prompt": "A friendly AI voice assistant answering a restaurant phone call, glowing holographic phone interface floating above a warm restaurant dining room with tables and candles in the background",
        "style": "cinematic",
        "mood": "warm, modern, trustworthy",
        "composition": "centered holographic interface, restaurant atmosphere in background",
        "negative_elements": "text, watermark, people",
        "context": "hero-image",
        "aspect_ratio": "16:9",
    }
    enhanced = await _build_enhanced_prompt(raw_input)
    print("=== Enhanced Prompt ===")
    print(enhanced)
    print("=======================\n")

    result = await handle(
        name="image_generate",
        input=raw_input,
        user_id="test-user",
    )
    print(result)

asyncio.run(main())
