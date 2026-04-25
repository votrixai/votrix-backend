"""
Generate Cater-AI carousel Slide 1 & 2 via Gemini.
Saves images to scripts/generated_images/.
"""
import asyncio
from pathlib import Path
from google import genai
from google.genai import types as genai_types

GEMINI_API_KEY = "AIzaSyC7X-_YBhxFZfAYARXhSn4HD23bLLgbY6I"
MODEL = "gemini-3.1-flash-image-preview"
SIZE = "1024x1024"
OUT = Path(__file__).parent / "generated_images"
OUT.mkdir(exist_ok=True)

CHARACTER_ANCHOR = (
    "a tired but sharp male restaurant owner in his early 40s, "
    "wearing a slightly wrinkled white chef apron over a dark grey t-shirt, "
    "short dark hair slightly disheveled, medium build, "
    "with an overwhelmed and panicked expression"
)

SLIDE_1_PROMPT = f"""
{CHARACTER_ANCHOR} — both hands full carrying two large plates of food,
body twisted sideways, eyes wide and darting toward a ringing telephone on the nearby counter,
mouth slightly open mid-yell toward someone off-frame.

Set inside a bright, lived-in, slightly cluttered American casual restaurant
kitchen pass-through area with warm stainless steel and worn wooden surfaces.
Spacious framing. Warm pendant lights hang above the counter.
A busy dining room packed with customers visible through a service window in the background.
Order tickets pinned to a rail above, stacked takeout bags on the counter.

Realistic documentary photography style with a playful, slightly exaggerated energy.
Candid mid-chaos moment. Authentic and humorous — not staged.

Warm overhead pendant lighting with soft ambient fill from the dining room.
High-key, energetic, no harsh shadows.

Low angle, 35mm lens, shallow depth of field.
Subject centered-right carrying plates.
A ringing corded telephone visible in the left foreground, slightly out of focus.
Upper 35% of the frame is relatively open and clean for text overlay.

Busy, chaotic, energetic, instantly relatable with a humorous edge.
Warm amber and cream tones dominate (65%), white and neutral accents (25%),
one pop of red from a small blinking light on the ringing phone (10%).

This is slide 1 of 6 in a visual story sequence.
Establish the character appearance and restaurant environment clearly
for visual consistency across the series.

{SIZE}. High quality, professional photography.
"""

SLIDE_2_PROMPT = f"""
{CHARACTER_ANCHOR} — now frozen in place, staring down at a smartphone
lying flat on the counter, face dropping in disbelief.
His hand hovers mid-reach toward the phone, halfway between picking it up and giving up entirely.
Expression: the specific look of a man who just realized something awful.

Same restaurant kitchen pass-through counter as the previous frame.
Same stainless steel surface, same order tickets on the rail above,
same warm pendant lighting. Counter slightly more cluttered now —
a cold coffee cup, crumpled order slips. Dining room blurred in background.

Realistic documentary photography, candid and authentic.
Slightly tighter and more intimate than slide 1 — the chaos is now personal.

Same warm overhead pendant lighting. Additional cool glow from the smartphone
screen casting faint light upward onto the owner's face and hands.

Medium close-up, 50mm lens.
Phone screen dominant in lower center of frame — clearly showing "Missed Calls: 6"
with timestamps stacked in a list.
Owner's face visible in the upper half, expression clearly readable.
Right side of frame has 30% clean space for text overlay.

Urgency and dread, still relatable and slightly darkly comic.
Same warm amber tones. Cool blue-white from phone screen is the one accent (10%).

Slide 2 of 6. Same character and restaurant environment as the reference image.
The story escalates: he has just seen the missed calls. Camera moves closer.
Mood shifts from frantic to sinking dread — still with a humorous edge.

{SIZE}. High quality, professional photography.
"""


async def generate(prompt: str, ref_bytes: bytes | None = None, ref_mime: str | None = None) -> tuple[bytes, str]:
    client = genai.Client(api_key=GEMINI_API_KEY)
    contents: list = []
    if ref_bytes and ref_mime:
        contents.append(genai_types.Part.from_bytes(data=ref_bytes, mime_type=ref_mime))
    contents.append(genai_types.Part.from_text(text=prompt))

    response = await client.aio.models.generate_content(
        model=MODEL,
        contents=contents,
        config=genai_types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            return part.inline_data.data, part.inline_data.mime_type
    raise ValueError("No image in Gemini response")


async def main():
    print("Generating Slide 1 (Hook)...")
    s1_bytes, s1_mime = await generate(SLIDE_1_PROMPT)
    ext = s1_mime.split("/")[-1]
    p1 = OUT / f"cater_ai_slide1.{ext}"
    p1.write_bytes(s1_bytes)
    print(f"  Saved → {p1}")

    print("Generating Slide 2 (Escalate) with Slide 1 as reference...")
    s2_bytes, s2_mime = await generate(SLIDE_2_PROMPT, s1_bytes, s1_mime)
    ext2 = s2_mime.split("/")[-1]
    p2 = OUT / f"cater_ai_slide2.{ext2}"
    p2.write_bytes(s2_bytes)
    print(f"  Saved → {p2}")

    print("\nDone. Open the images above to review.")


asyncio.run(main())
