---
name: generate-image
description: >
  Pure image generation (no text overlay or typographic composition).
  Accepts a subject description and focuses on producing visually consistent,
  well-composed images. Suitable for single images or multi-image sets that
  require a unified style.
---

# Generate Image

## Step 1 — Gather Inputs

Confirm the following parameters:
- **Subject description**: What each image should convey (one sentence or keywords per image)
- **Aspect ratio** (`aspect_ratio`): `1:1` / `4:5` / `9:16` / `16:9`
- **Use case** (`context`): Choose from `social-media`, `banner`, `icon`, `thumbnail`, `product-shot`, `editorial`, `hero-image`, `illustration`
- **Multi-image mode**: Are multiple images needed? If yes, how many?
- **User-uploaded images** (if any):
  - Style / content reference → pass as `reference_image_urls` to guide generation
  - Brand assets (logo, stickers to be composited) → do not pass to generation; handle separately after

---

## Step 2 — Lock Parameters (Once, Before Any Generation)

Decide the shared visual language for the entire set upfront. These parameters apply to **all images unchanged** — do not re-decide per image.

**Style** (`style`): Always default to `photographic` (photorealistic) — this is the standard and produces the best results. Only switch if the client explicitly requests a specific style name (e.g. `anime`, `cinematic`, `digital-art`, `fantasy-art`, `comic-book`, `pixel-art`). Vague terms like "illustration" or "cartoon" are not accepted.

**Mood** (`mood`): Describe the shared color temperature and visual atmosphere of the entire set — not the emotional tone of each individual scene. This is the visual bottom layer that makes all images feel like they belong together (e.g. `warm amber tones, soft natural light` or `cool blue tones, dramatic contrast`). Do not adjust mood per image even if each image has a different subject or scene.

**Composition base** (`composition`): Lock the shared framing principles:
- `single focal point, generous negative space, clean composition, focused subject, no clutter`

**Negative elements** (`negative_elements`): Lock once:
- `text, watermark, logo, typography, busy background, cluttered, multiple competing subjects, decorative noise, visual complexity`
- If the subject includes any person or animal, also add: `extra fingers, extra limbs, extra arms, extra legs, fused limbs, merged body parts, floating limbs, disfigured face, extra eyes, distorted face, anatomical distortion, malformed hands`

Write down the locked parameters before proceeding. They will be reused verbatim for every image.

---

## Step 3 — Generate Image 1 + Establish Style Anchor

1. Generate Image 1 using the locked parameters from Step 2. No `reference_image_urls` for this image.

2. **Quality check** — review the generated image immediately:

   | Check | Pass Criteria |
   |-------|--------------|
   | No text | No text or watermark visible |
   | Subject accuracy | Content matches the subject description |
   | Clean reserved area | Text overlay region is clean and usable (if applicable) |

   **Anatomy check** — only if the image contains a person or animal:

   | Check | Pass Criteria |
   |-------|--------------|
   | Limb count | Correct number of arms, legs, ears for the species |
   | Finger count | Each human hand has exactly five fingers |
   | Face structure | Eyes, nose, mouth are distinct and not duplicated or overlapping |
   | Limb boundaries | No fused, merged, or floating limbs |

   If any anatomy check fails, add a positive correction to `prompt` and a matching negative term to `negative_elements` that directly targets the defect, then regenerate. For example: extra fingers → add `anatomically correct hands, five fingers` to `prompt` and `extra fingers` to `negative_elements`. Max **3 retries** per image — if still failing after 3 attempts, note the remaining issue and proceed.

3. Once Image 1 passes all checks, report to the user: confirm the image number, state that composition and realism have been reviewed and look good, and note any minor observations if relevant.

4. **Extract style anchor** — once Image 1 passes, describe what it actually rendered (not what you intended). Write a short visual description covering:
   - Color temperature and palette (e.g. `warm amber highlights, muted shadows`)
   - Lighting style (e.g. `soft diffused natural light`, `dramatic side lighting`)
   - Depth and texture (e.g. `shallow depth of field, slight film grain`)

   Record: **Image 1 URL** + **style anchor text**. Both will be used for all subsequent images.

---

## Step 4 — Generate Each Subsequent Image (Multi-Image Mode)

For each Image N (N ≥ 2), follow this loop strictly — do not move to the next image until the current one passes.

**Build the tool call:**
- `prompt`: Subject description for this image (from Step 1)
- `style`: From Step 2 locked parameters (unchanged)
- `mood`: From Step 2 locked parameters (unchanged — do not adapt to this image's scene)
- `composition`: Step 2 base + append the style anchor text from Step 3
- `negative_elements`: From Step 2 locked parameters (unchanged)
- `context` and `aspect_ratio`: From Step 1 (unchanged)
- `reference_image_urls`: **Always Image 1's URL** — not the previous image, always the first

**Quality check** — review immediately after generation:

| Check | Pass Criteria |
|-------|--------------|
| No text | No text or watermark visible |
| Subject accuracy | Content matches this image's subject description |
| Clean reserved area | Text overlay region clean and usable (if applicable) |
| Style consistency | Color temperature, lighting, and overall visual language match Image 1 |

**Anatomy check** — only if the image contains a person or animal:

| Check | Pass Criteria |
|-------|--------------|
| Limb count | Correct number of arms, legs, ears for the species |
| Finger count | Each human hand has exactly five fingers |
| Face structure | Eyes, nose, mouth are distinct and not duplicated or overlapping |
| Limb boundaries | No fused, merged, or floating limbs |

If any check fails: add corrective instructions to `prompt` or `composition` and regenerate the **current image**. Do not proceed to the next image. For anatomy failures, add a positive correction to `prompt` and a matching negative term to `negative_elements` that directly targets the defect. Max **3 retries** per image — if still failing after 3 attempts, note the remaining issue and proceed.

Once the current image passes all checks, report to the user: confirm the image number, state that composition and realism have been reviewed and look good, and note any minor observations if relevant. Then proceed to Image N+1.

---

## Step 5 — Output

Once all images pass quality checks, return the file paths or URLs for all generated images.
