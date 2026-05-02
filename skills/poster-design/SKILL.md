---
name: poster-design
version: v6-dual-route
final_prompt_focus: true
description: >
  General-purpose poster design skill with two compositing routes.
  Route A (default): generates a clean background image then composites real canvas-fonts
  typography via Pillow — precise font control, pixel-accurate layout.
  Route B (fast draft): generates the complete poster as one image with embedded text.
  Covers brand campaigns, product ads, SaaS, local businesses, promotions, events,
  recruitment, content education, and carousel sets.
integrations: []
---

# Poster Design

## Core Principles

This skill supports two routes decided at Step 6:

- **Route A — Pillow composite (default):** Generate a clean background/subject image (no text),
  then composite typography using real canvas-fonts TTF files via Pillow.
  Use this when font precision matters — which is the default.
- **Route B — image-complete (fast draft):** Generate the full poster as one image with text
  embedded by the model. Use only when the user explicitly asks for a quick draft, or when
  the style is `illustration` / `anime` and precise fonts are not required.

Always use the **image-complete** approach for Route B:

- Typography instructions go into the prompt
- Do NOT add `text` / `typography` / `letters` to negative elements in Route B

For Route A:

- Typography instructions are removed from the image prompt
- `text, typography, letters, numbers` MUST be in negative elements

> Analysis up front, convergence at the end.
> Clean visuals, no empty advertising.
> Final prompt is a production command for the image model.

The final prompt retains only:

1. One core ad concept
2. One hero visual
3. One confirmed aspect ratio
4. One confirmed layout
5. One persuasive but lean copy hierarchy
6. One set of brand / style / negative constraints

---

## Step 1 — Context Read

Read context in priority order. Infer what you can; do not ask unless you must:

1. `mnt/memory/social-media-manager/marketing-context.md` — brand name, industry, target audience,
   brand colors, tone, composition preferences; use **Logo / brand asset URLs** from this file
2. User message — poster purpose, product, platform, size, required text, forbidden elements
3. Uploaded images — logo, product photos, reference style, color palette, composition constraints
4. Conversation history — confirmed preferences such as color exclusions, text color, logo usage

Determine directly:

- Poster mode: single / carousel
- Ad purpose: brand, pain point, conversion, feature, promotion, event, recruitment, education
- Target audience: who sees it, why they care, what action you want
- Must include: brand name, logo, product, people, scene, specified copy
- Must avoid: colors, styles, elements, compositions, copy the user has explicitly forbidden

Only ask if: the topic is completely missing and you cannot determine what the poster promotes.

---

## Step 2 — Aspect Ratio & Format Strategy

Do not default every poster to `vertical 4:5`.

Priority:

1. User specifies platform / size / orientation → follow strictly
2. Unspecified → apply **controlled variation** based on use case, copy volume, hero visual, placement
3. Do not generate an Instagram portrait just because a reference prompt mentioned Instagram

Common formats:

| Format | Best for |
|---|---|
| `4:5 vertical` | Social ads, product promos, mobile feed |
| `1:1 square` | Brand posts, product posts, general social |
| `16:9 horizontal` | Website banners, landing page heroes, decks |
| `9:16 vertical` | Stories, Reels, TikTok, full-screen mobile ads |
| `2:3 vertical` | Traditional posters, flyers, event promos |

Canvas sizes (used by Route A Pillow composite):

| Format | Canvas (px) |
|---|---|
| `4:5` | 1080 × 1350 |
| `1:1` | 1080 × 1080 |
| `16:9` | 1920 × 1080 |
| `9:16` | 1080 × 1920 |
| `2:3` | 1080 × 1620 |

Output:

```text
Format Strategy: [user-specified / controlled variation]
Final format: [orientation + aspect ratio + use-case]
Canvas size: [W × H px]
Reason: [one sentence]
```

---

## Step 3 — Core Ad Concept

Before writing copy or describing the scene, distill one core ad concept.

The concept must express one of: pain point, loss, desire, outcome, contrast, or reason to act.

Requirements:

- Speaks to the genuine psychology of the target audience, not a feature list
- Can be translated into a clear hero visual
- One direction only — pick the best fit, discard the rest
- This is an internal brief; it does not have to appear verbatim in the final prompt

Output:

```text
Core concept: [one sentence]
```

---

## Step 4 — Copy Strategy

Determine the poster type first, then decide the copy hierarchy.

| Poster purpose | Default copy structure |
|---|---|
| Brand awareness | Headline + brand name |
| Pain-point ad | Headline + subheadline + 2–3 short benefit tags |
| Conversion ad | Headline + subheadline + 2–3 short benefit tags + 1 CTA |
| Feature ad | Headline + feature description + 2–3 feature tags |
| Promotion / event | Headline + key info + 1 CTA |
| Recruitment / sign-up | Headline + role / opportunity description + 1 CTA |
| Content education | Hook headline + one-line value + save / follow CTA |

### Single Poster Copy Rules

Default limits:

- Headline: 1, the strongest, largest, most scroll-stopping
- Subheadline: 0–1, explains product value
- Benefit tags: 0–3, each must be short
- CTA: 0–1
- Brand name / logo: include as needed

Constraints:

- Headline: prefer 3–8 English words; for Chinese prefer 6–14 characters
- No multiple headlines, no multiple CTAs, no long paragraphs
- Do not cram every feature into one image
- If the user provides a lot of copy, filter it — do not keep it all

Copy priority: `Headline > Subheadline > CTA > Benefit tags > Other info`

### Carousel Copy Rules

Carousel follows a fixed Hook → Content → CTA structure.

- Slide 1: strong hook — one pain point / contrast / curiosity trigger only
- Middle slides: one point per slide
- Last slide: explicit CTA
- Keep all copy short; avoid repeating benefit tags across slides

Show the user each slide's role and draft copy before generating; wait for confirmation.

---

## Step 5 — Layout Strategy

Choose one definitive layout based on aspect ratio, hero visual, and copy volume.
**This decision is locked here and must be followed exactly by Step 7A (image prompt framing)
and Step 9A (Pillow composite). Do not drift from it.**

Never write multiple candidate positions in the final prompt. Pick one.

### Text area position options

| Position | Meaning | Good when |
|---|---|---|
| `bottom-third` | Lower ~35% reserved for text | Heavy copy, portrait formats, subject with natural headroom |
| `top-third` | Upper ~35% reserved for text | Subject anchors at bottom (food on table, product on surface) |
| `left-half` | Left ~45% reserved for text | Landscape format, subject naturally on right |
| `right-half` | Right ~45% reserved for text | Landscape format, subject naturally on left |
| `overlay-center` | Central band overlaid on full-bleed image | Minimal copy (1–2 lines), strong moody background |

### Selection rules by aspect ratio

- `4:5 vertical` → prefer `bottom-third` or `top-third`
- `1:1 square` → prefer `bottom-third` or `top-third`; `overlay-center` for brand-only
- `16:9 horizontal` → prefer `left-half` or `right-half`
- `9:16 vertical` → prefer `bottom-third` (hook at top, CTA at bottom); or `top-third`
- `2:3 vertical` → prefer `top-third` or `bottom-third`

### Carousel layout variety rule

Carousel slides must not all use the same text area position.
Assign positions before generating anything — plan across all slides first:

- Hook slide: prefer `top-third` or `overlay-center` (bold, unexpected)
- Content slides: alternate between `bottom-third` and `left-half` / `right-half`
- CTA slide: prefer `bottom-third` (natural place for action text)

Output (one block per slide for carousel, one block for single):

```text
Layout Strategy: [one sentence]
Text area: [one fixed position]
Hero visual: [one fixed position]
```

---

## Step 6 — Lock Visual Parameters + Route Decision

Lock all parameters before generating. Carousel slides must stay consistent.

### Route Decision

| Condition | Route |
|---|---|
| Default | **A — Pillow composite** |
| User says "fast" / "draft" / "quick" | B — image-complete |
| Style is `illustration` or `anime` | B — image-complete |
| User explicitly says they do not need precise fonts | B — image-complete |

Output:

```text
Route: [A — Pillow composite / B — image-complete]
Reason: [one phrase]
```

### Style

Default: `photorealistic`. **Strongly recommended — keep this style.** The image should feel real,
three-dimensional, and tactile, like a commercial studio shoot or a high-end ad campaign.  
Do not switch unless the user explicitly and strongly requests it.
Switchable options: `illustration`, `3d-render`, `anime`, `minimal`, `cinematic`, `digital-art`.

### Mood

Mood describes the image's **color temperature, lighting, contrast, and overall atmosphere**.
Must be inferred from brand, ad purpose, hero visual, and user preferences — do not copy examples.

Output as one compact English phrase:

```text
[color temperature], [lighting source / quality], [contrast level], [atmosphere]
```

### Font Selection (Route A only)

**Fonts must be chosen from the Canvas font library below.** These TTF files are loaded by Pillow
at composite time. Do not reference fonts outside this list.

| Font | Available weights | Best for |
|---|---|---|
| **Boldonse** | Regular | Heavy impact headlines, street style |
| **EricaOne** | Regular | Strong display headlines, event promos |
| **BigShoulders** | Regular, Bold | Condensed headlines, sports, industrial |
| **BricolageGrotesque** | Regular, Bold | Modern grotesque display, tech, SaaS |
| **NationalPark** | Regular, Bold | Outdoor, nature, travel |
| **Gloock** | Regular | Editorial serif display, fashion, luxury |
| **Italiana** | Regular | Elegant Italian serif, fine dining, luxury |
| **PoiretOne** | Regular | Geometric elegant display, beauty, soft luxury |
| **WorkSans** | Regular, Bold, Italic, BoldItalic | Versatile modern sans-serif, corporate, SaaS |
| **InstrumentSans** | Regular, Bold, Italic, BoldItalic | Clean modern sans-serif, brand, product |
| **Outfit** | Regular, Bold | Clean modern sans-serif, tech, apps |
| **SmoochSans** | Medium | Friendly sans-serif, consumer goods, food & beverage |
| **ArsenalSC** | Regular | Small-caps sans-serif, brand labels, tags |
| **Jura** | Light, Medium | Technical, sci-fi, minimal |
| **CrimsonPro** | Regular, Bold, Italic | Classic editorial serif, publishing, education |
| **IBMPlexSerif** | Regular, Bold, Italic, BoldItalic | Technical serif, tech brands, precision |
| **Lora** | Regular, Bold, Italic, BoldItalic | Elegant editorial serif, food, lifestyle |
| **InstrumentSerif** | Regular, Italic | Refined editorial serif, fashion, creative |
| **YoungSerif** | Regular | Friendly serif, consumer goods, brand |
| **LibreBaskerville** | Regular | Classic book serif, traditional brands |
| **NothingYouCouldDo** | Regular | Handwritten, weddings, handmade, warm scenes |
| **DMMono** | Regular | Clean monospace, code aesthetic, tech |
| **GeistMono** | Regular, Bold | Modern monospace, developer tools, tech |
| **IBMPlexMono** | Regular, Bold | Technical monospace, data, precision |
| **JetBrainsMono** | Regular, Bold | Developer monospace, technical products |
| **RedHatMono** | Regular, Bold | Clean monospace, brand labels |
| **PixelifySans** | Medium | Pixel art, gaming, retro tech |
| **Silkscreen** | Regular | Pixel retro, gaming, 8-bit |
| **Tektur** | Regular, Medium | Sci-fi technical, game UI, futuristic |

Font pairing rules:

- One font for the headline; subheadline/body may use a different weight from the same family,
  or one contrasting font
- Serif + sans-serif (e.g. Gloock + WorkSans) is a reliable pairing
- Display fonts (Boldonse, EricaOne) for headlines only
- Monospace fonts only for labels/subheadlines in tech/code contexts
- Maximum 2 fonts per poster

Output:

```text
Font: [headline font name + weight] / [subheadline/body font name + weight (if different)]
TTF files: [e.g. WorkSans-Bold.ttf / CrimsonPro-Regular.ttf]
```

### Negative Elements

**Route A base** (always include `text` / `typography`):

```text
text, typography, letters, numbers, watermark, random logos, cluttered layout,
unreadable background, multiple competing subjects, decorative noise
```

**Route B base** (never exclude `text` / `typography`):

```text
watermark, random logos, cluttered layout, unreadable background,
multiple competing subjects, decorative noise, distorted text blocks
```

Add when the poster includes people or animals (both routes):

```text
extra fingers, extra limbs, fused limbs, malformed hands, distorted face, extra eyes,
anatomical distortion
```

---

## Step 7 — Compile Final Prompt

### Route A — Clean Image Prompt

The image prompt describes **only the background and hero subject** — no copy, no typography.
The model must not render any text in the scene.

Required elements:

1. Poster type — format, brand, product category
2. Hero visual — one hero subject; do not spread equal weight across multiple subjects
3. Scene — environment, people, lighting, realism
4. **Composition framing** — use the text area position locked in Step 5 to pick the exact
   framing instruction from the table below and include it verbatim in the prompt
5. Style — photorealistic, brand tone, color palette
6. Explicit instruction: `no text, no letters, no typography anywhere in the image`

### Composition framing instructions (pick one, paste into prompt)

| Text area (Step 5) | Framing instruction to include in the image prompt |
|---|---|
| `bottom-third` | The subject fills the upper 60% of the frame. The bottom 35% is a clean, minimal-detail area — dark floor, soft shadow gradient, or blurred ground — naturally clear enough for text overlay. |
| `top-third` | The subject fills the lower 60% of the frame. The top 35% is open sky, plain wall, or minimal background — naturally clear enough for text overlay. |
| `left-half` | The subject is framed on the right half of the image. The left half has minimal visual detail — open space, soft bokeh, or a plain surface — naturally clear enough for text overlay. |
| `right-half` | The subject is framed on the left half of the image. The right half has minimal visual detail — open space, soft bokeh, or a plain surface — naturally clear enough for text overlay. |
| `overlay-center` | The subject fills the full frame with a naturally dark or low-contrast central horizontal band across the middle third of the image, suitable for text overlay. |

Prompt opening:

```text
Create a [orientation] [aspect ratio] clean background image for a [Brand] advertising poster.
```

Target **120–180 words**. No copy hierarchy, no font names, no CTA.

### Route B — Full Poster Prompt

The image prompt describes the complete poster including embedded typography.

Required elements:

1. Poster type — format, use case, brand, product category
2. Core idea — one visualizable ad theme
3. Hero visual — one hero subject
4. Scene — environment, people, lighting, realism
5. Layout — one confirmed composition and text area position
6. Typography — headline, subheadline, benefit tags, CTA, brand name hierarchy and positions
7. Style — brand tone, color palette
8. Constraints — no extra text, no random logos, no watermarks, no garbled text

Forbidden in both routes: strategy sentences, non-executable lines, multiple layout candidates,
multiple headlines, multiple CTAs, stacked feature lists, destabilizing emotion words.

Prompt opening:

```text
Create a [orientation] [aspect ratio] [use-case] advertising poster for [Brand], a [product/category].
```

Target **180–280 words** for Route B.

---

## Step 8 — Generate Image

Call `image_generate`.

### Single Poster / Carousel Slide 1

| Parameter | Route A value | Route B value |
|---|---|---|
| `prompt` | Clean image prompt (Step 7A) | Full poster prompt (Step 7B) |
| `style` | Locked value from Step 6 | Locked value from Step 6 |
| `mood` | Locked value from Step 6 | Locked value from Step 6 |
| `negative_elements` | Route A negatives (includes `text, typography, letters`) | Route B negatives |
| `aspect_ratio` | Final format from Step 2 | Final format from Step 2 |
| `reference_image_urls` | User logo / reference / product photo (if any) | User logo / reference / product photo (if any) |

After generation:

- Route B single poster → proceed to Step 10 QC
- Route A / Carousel → proceed to next section

### Carousel Slide N (N ≥ 2)

**Generate slide 1 first. Do not generate any subsequent slide until slide 1 has passed QC.**

Always pass the **slide 1 URL** in `reference_image_urls` for slides 2+. Never reference the
previous slide — always reference slide 1.

| Parameter | Value |
|---|---|
| `prompt` | Current slide prompt |
| `style` | Locked value from Step 6 |
| `mood` | Locked value from Step 6 |
| `negative_elements` | Same as slide 1 |
| `aspect_ratio` | Final format from Step 2 |
| `reference_image_urls` | **[Slide 1 URL]** + user logo / product photo (if any) |

Append to every slide N prompt:

```text
Keep the same visual language as the first image: [actual style anchor description].
```

---

## Step 9A — Pillow Composite (Route A only)

After the clean image passes QC, composite all text layers using Pillow.

**All positioning in this step is driven by the layout locked in Step 5.
Do not choose new positions here — read `Text area` and `Hero visual` from Step 5 output
and apply them directly.**

### Canvas Size

Use the canvas size locked in Step 2.

### Text Zone Lookup

Use the **text area position from Step 5** to look up pixel coordinates:

Format: `(x0, y0, x1, y1)` — top-left to bottom-right of the text zone.

| Text area position | 4:5 (1080×1350) | 1:1 (1080×1080) | 16:9 (1920×1080) | 9:16 (1080×1920) | 2:3 (1080×1620) |
|---|---|---|---|---|---|
| `top-third` | (40, 40, 1040, 430) | (40, 40, 1040, 340) | (60, 40, 860, 1040) | (40, 60, 1040, 600) | (40, 40, 1040, 500) |
| `bottom-third` | (40, 920, 1040, 1310) | (40, 740, 1040, 1040) | (1060, 40, 1860, 1040) | (40, 1320, 1040, 1860) | (40, 1140, 1040, 1580) |
| `left-half` | (40, 40, 490, 1310) | (40, 40, 490, 1040) | (60, 60, 900, 1020) | (40, 200, 490, 1720) | (40, 40, 490, 1580) |
| `right-half` | (590, 40, 1040, 1310) | (590, 40, 1040, 1040) | (1020, 60, 1860, 1020) | (590, 200, 1040, 1720) | (590, 40, 1040, 1580) |
| `overlay-center` | (60, 480, 1020, 870) | (60, 360, 1020, 720) | (480, 120, 1440, 960) | (60, 720, 1020, 1200) | (60, 560, 1020, 1060) |

### Within-Zone Text Stacking

Stack all text elements **inside the text zone** in copy priority order, top to bottom,
left-aligned with 40px left padding (or centered for `overlay-center`).

| Layer | Vertical position within zone | Alignment |
|---|---|---|
| Headline | Zone top + 40px | Left (or center for `overlay-center`) |
| Subheadline | Below headline + 20px gap | Same as headline |
| Benefit tags | Below subheadline + 28px gap | Left, arranged in a row; wrap to next row if total width exceeds zone width |
| CTA | Below tags + 32px gap (or zone bottom − 60px, whichever is lower) | Left |
| Brand name | Zone bottom − 40px | Right-aligned within zone |

**Spacing rules:**

- Minimum 16px between any two text layers
- If total stacked height exceeds zone height: reduce all gaps proportionally, then reduce font
  sizes in reverse priority order (brand name first, then tags, then CTA, then subheadline)
- Never let any text layer exceed zone boundaries

### Overlay Decision (3-step)

**Step 1 — Sample the text zone**

Convert the text zone crop to grayscale. Compute:
- `mean` — average pixel brightness (0–255)
- `std` — standard deviation of pixel brightness

```python
import numpy as np
from PIL import Image

zone_crop = img.crop(text_zone).convert("L")
pixels = np.array(zone_crop)
mean, std = pixels.mean(), pixels.std()
```

**Step 2 — Decide whether overlay is needed**

| Condition | Decision | Reason |
|---|---|---|
| `std < 30` and `mean < 80` | **No overlay** — white text directly | Zone is uniformly dark; natural contrast is sufficient |
| `std < 30` and `mean > 180` | **No overlay** — dark text (`#1a1a1a`) directly | Zone is uniformly light; natural contrast is sufficient |
| `std < 30` and `80 ≤ mean ≤ 180` | **Light overlay** `alpha 80–120` | Zone is uniform mid-tone; small boost needed |
| `std ≥ 30` | **Overlay required** | Zone is complex/textured; must suppress background for legibility |

When `std ≥ 30`, set overlay alpha based on complexity:

| `std` range | Overlay alpha |
|---|---|
| 30–60 | 140 |
| 61–90 | 180 |
| > 90 | 220 |

Text color is always white `#FFFFFF` when an overlay is applied.

**Step 3 — Gradient direction (when overlay is applied)**

Draw the overlay as a **linear gradient** that fades from opaque at the text zone edge
to transparent toward the hero visual — never a hard-edged rectangle.

| Text area position | Gradient direction |
|---|---|
| `bottom-third` | Opaque at bottom edge → transparent upward |
| `top-third` | Opaque at top edge → transparent downward |
| `left-half` | Opaque at left edge → transparent rightward |
| `right-half` | Opaque at right edge → transparent leftward |
| `overlay-center` | Semi-transparent solid rectangle with 20px feathered edges |

Overlay color: `rgba(0, 0, 0, alpha)`. Do not use brand color for the overlay — it
competes with the hero visual.

### Font Loading

Load TTF files from the `canvas-fonts/` directory using the font names locked in Step 6:

```python
# Example
from PIL import ImageFont
headline_font = ImageFont.truetype("canvas-fonts/WorkSans-Bold.ttf", size=headline_size)
sub_font = ImageFont.truetype("canvas-fonts/CrimsonPro-Regular.ttf", size=sub_size)
```

Font size calculation (start from max, shrink until text fits zone width):

| Copy layer | Starting size | Minimum size | Step |
|---|---|---|---|
| Headline | 96px | 48px | −4px |
| Subheadline | 56px | 32px | −4px |
| Benefit tags | 40px | 28px | −2px |
| CTA | 44px | 30px | −2px |
| Brand name | 32px | 24px | −2px |

Measure with `font.getbbox(text)`. Shrink until text width ≤ zone width. Wrap at word boundaries
if text still does not fit at minimum size.

### Layer Order

```
1. Background / hero image (full canvas)
2. Gradient overlay on text zone (if needed)
3. Solid color block behind tags (if using benefit tags)
4. Headline text
5. Subheadline text
6. Benefit tag texts
7. CTA text
8. Brand name text
9. Logo (bottom-right corner, width ≤ 12% of canvas width, 24px margin)
```

### Logo Handling

If `marketing-context.md` provides a logo path:

- No transparent background → use `rembg` or threshold masking to remove background
- Low resolution or blurry → extract alpha shape, fill with `text_color` (single-color treatment)
- Composite with `Image.alpha_composite`; preserve transparency channel

### Output Path

- Single: `/mnt/session/outputs/poster_{slug}.png`
- Carousel: `/mnt/session/outputs/poster_{slug}_slide{n}.png`

---

## Step 10 — Quality Check

**Run after every generated or composited image. For carousel, check each slide before
proceeding to the next. Fix and redo immediately on any failure. Maximum 3 retries per slide.**

### Route A Checklist (Pillow output)

| Check | Pass standard | Action on fail |
|---|---|---|
| **Text not clipped** | No text character cut off at canvas edge | Reduce font size or adjust text zone |
| **No text overlap** | No two text layers intersect | Recalculate vertical spacing |
| **Text contrast** | Every text layer is legible against its local background | Increase overlay alpha or switch to darker overlay zone |
| **Font loaded correctly** | Fonts render as the selected canvas-fonts typeface, not a system fallback | Verify TTF path; re-check font name mapping |
| **Copy complete** | Every line of copy confirmed in Step 4 appears in the output | Re-add missing copy layer |
| **No garbled characters** | No □□□ or replacement characters | Check font supports the character set; add NotoSansCJK fallback for CJK |
| **Logo present and clean** | Logo in bottom-right, not distorted, correct color treatment | Re-run logo preprocessing |
| **Layout matches preset** | Text zone position matches the `Text area` locked in Step 5 | Re-composite using the correct zone coordinates |
| **Clean background** | No text rendered by the image model in the background image | Verify `text, typography, letters` were in negative elements; regenerate if present |
| **Composition matches Step 5** | Hero visual and text area are where Step 5 specified | Adjust zone coordinates |
| **Not overcrowded** | Information does not feel overloaded; composition is clean | Remove weakest copy layer |

### Route B Checklist (image-complete output)

| Check | Pass standard | Action on fail |
|---|---|---|
| Copy complete | All key text present; no stray characters | Emphasize missing text / no extra text, retry |
| Text legibility | Headline readable; no garbled characters | Add `crisp, sharp, highly legible typography` |
| Copy hierarchy | Headline largest; correct size order | Rewrite typography instruction |
| Hero visual | Hero subject immediately recognizable | Strengthen hero object description |
| Layout | Matches Step 5; text area unambiguous | Fix text area position |
| Non-templated | Does not look like a generic template | Use natural negative space |
| Marketing completeness | Pain point / value / action present | Add subheadline, tag, or CTA |
| Not overcrowded | Clean composition | Remove weak copy |
| Brand constraints | Colors, logo, forbidden elements comply | Correct conflicting constraints |

**Both routes — when people or animals are present:** also check for anatomical distortion
(hands, face, limbs). On failure, add anatomical correction terms and retry.

After 3 failed retries: report exactly which check is failing; do not pretend it passed.

---

## Step 11 — Output

Call `show_post_preview`.

Single poster:

```text
slides: [{ path: "<output path>", label: "Poster" }]
caption: "One sentence explaining the core design decision"
hashtags: []
```

Carousel:

```text
slides: [
  { path: "<output path>", label: "Slide 1 · Hook" },
  { path: "<output path>", label: "Slide 2 · Content" },
  { path: "<output path>", label: "Slide N · CTA" }
]
caption: "One sentence explaining the carousel narrative"
hashtags: []
```

Do not generate hashtags unless the user explicitly asks.

---

## Extra Rules

### Logo / Reference Images

If the user provides a logo or product image:

- Always pass it in `reference_image_urls` for the image generation call
- Route A: describe how the scene should relate to the product; do not instruct the model to render text
- Route B: describe how to use it; do not redesign, distort, or enlarge to compete with the headline
- Logo placed in corner, small and clear (Pillow handles final logo placement in Route A)

### User Preferences Take Priority

Explicitly stated preferences persist for the entire session:
excluded colors, text color, full color scenes, no black-and-white, ad placement requirements,
premium / clean / realistic look. If a default rule conflicts with a user preference, the user wins.

### Text Color (Route B)

If the user says "white text", this means poster text white only — not a desaturated image:

```text
All poster text should be white only, while the scene and people remain realistic full color.
```

### Busy Scenes

A busy atmosphere is fine; a cluttered layout is not:

```text
busy but controlled atmosphere, clean composition, no cluttered layout
```

### Prompt Quality Floor

The final prompt must satisfy:

- One hero visual
- One composition
- One headline
- Minimal but complete persuasion structure
- No multiple candidate directions spliced together
- No lengthy ad strategy explanation
- No over-templated layout
