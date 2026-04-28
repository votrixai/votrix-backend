"""One-shot script to generate the Votrix hero image using Gemini."""
import asyncio
import uuid
from pathlib import Path

from google import genai
from google.genai import types as genai_types

GEMINI_API_KEY = "AIzaSyDMLZBWZvrv0AeDZgNDKsHLkRDfBgOelMI"

PROMPT = """A cinematic, hyper-polished promotional hero image for an AI-powered restaurant phone receptionist product. The scene depicts a warm, softly lit modern restaurant interior at evening time with amber candlelight and bokeh background. In the foreground, a sleek smartphone floats at a slight angle, its screen glowing with subtle sound wave visualizations in warm gold and coral tones, symbolizing an AI voice assistant actively handling a call. Around the phone, elegant concentric sound wave rings radiate outward in translucent amber light, representing the AI answering calls 24/7.
In the soft-focus background, a busy restaurant scene: a host stand with a relaxed staff member smiling and attending to in-person guests instead of being tied to the phone, kitchen activity visible through a warm pass-through window, and a receipt printer producing an order ticket. Small floating UI elements — a reservation confirmation badge, an order summary card, and a subtle upsell suggestion bubble — orbit around the phone like gentle holograms, all in a clean, minimal design language with rounded corners and warm transparency.
The overall color palette is deep navy-charcoal background with warm amber, soft gold, cream white, and living coral accents. The lighting is dramatic but inviting — cinematic restaurant warmth meets clean tech aesthetics. The mood conveys effortless efficiency: technology that feels like hospitality. No text, no logos, no words anywhere in the image. Photorealistic with subtle stylization, premium SaaS product marketing quality, 4K resolution.

Image dimensions: 1792x1024. High quality, suitable for social media."""


async def main():
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("Generating image...")
    response = await client.aio.models.generate_content(
        model="gemini-3.0-flash-preview-image-generation",
        contents=[genai_types.Part.from_text(PROMPT)],
        config=genai_types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )
    out_dir = Path(__file__).parent / "generated_images"
    out_dir.mkdir(exist_ok=True)
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            ext = part.inline_data.mime_type.split("/")[-1]
            img_path = out_dir / f"votrix_hero_{uuid.uuid4().hex[:8]}.{ext}"
            img_path.write_bytes(part.inline_data.data)
            print(f"Saved: {img_path}")
            return
    print("No image returned.")


asyncio.run(main())
