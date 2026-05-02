---
name: poster-design
description: >
  Design publishable posters and carousel/multi-poster sets: context, concept, copy,
  AI image generation with integrated brand assets, Pillow typography, and QC.
integrations: []
---

# Poster Design

Default route: **AI generates the visual image with logo/product/reference assets integrated into
the image; Pillow composites final marketing copy.**

Use for ads, promos, event posters, brand posts, SaaS/product posters, local business posters,
and carousel/multi-poster sets.

---

## Step 1 — Read Context

Read in order:

1. `mnt/memory/social-media-manager/marketing-context.md`
   - brand, audience, tone, colors, composition style
   - logo/product/mascot URLs and descriptions
2. User message
   - goal, platform, size, required text, forbidden elements
3. Uploaded files
   - logo, product photo, style reference, layout reference
4. Conversation history
   - persistent preferences

Determine:

- Mode: single / carousel / related multi-poster set
- Purpose: awareness / pain point / conversion / feature / promotion / event / education
- Audience and desired action
- Required assets and forbidden elements
- Size: follow user/platform; default single `1:1`, IG feed/carousel `4:5`

For every asset, record:

- What it is: logo/product/mascot/style/photo reference
- Key details: shape, colors, wordmark/icon, product features
- How AI should integrate it: corner brand mark, wall sign, sticker, counter card, packaging label,
  product in scene, mascot in scene, etc.
- Placement: outside the protected text zone; secondary to the hero subject

Only ask if the poster topic is missing.

---

## Step 2 — Plan Concept And Copy

Single poster:

```text
Core concept: [one sentence: pain/desire/contrast/outcome/reason to act]
```

Carousel:

- Slide 1: Hook
- Middle slides: one point per slide
- Last slide: CTA

Related multi-poster set:

- Each poster may use a different scene/concept.
- The set must share one visual language.
- Before generating, define a distinct scene structure for every image: setting, hero subject,
  subject action, key props, camera framing, text zone, and logo placement.
- Scene structures must be different from each other. Do not rely on later prompts to create
  variation.
- Generate image 1 first; later images must use image 1 URL as reference.
- Do not generate related images in parallel.

Copy limits:

- Headline: 1
- Subheadline: 0-1
- Tags: 0-3, short
- CTA: 0-1
- No long paragraphs, multiple headlines, or multiple CTAs
- If user gives too much copy, keep the strongest hierarchy

For carousel, show slide roles and draft copy before generating unless user already approved direct generation.

For carousel or multi-poster sets, write a storyboard/script before generation. Each image is a
different scene in the same campaign, not a variation of the same shot.

Storyboard format:

```text
Image 1 — [scene title]
Narrative beat: [what happens in this moment and why it matters]
Setting: [where this scene happens]
Hero subject: [who/what owns the frame]
Action: [specific visible action]
Key props: [objects that tell the story]
Camera/framing: [shot size, angle, subject placement]
Text zone: [where copy will go and what area must stay quiet]
Logo placement: [specific object/surface outside text zone]
Must differ from other images by: [setting / subject / action / props / framing]
Must avoid: [anything that would make it look like another image]
```

Write one block per image. Later prompts must follow their storyboard block exactly.

---

## Step 3 — Lock Style

Default style token: `photographic` — strongly prefer a photorealistic commercial photography
look. The image should feel real, tactile, and camera-shot, not illustrated or poster-rendered.

Use another style only if the user explicitly asks: `digital-art`, `anime`, `comic-book`,
`pixel-art`, `3d-model`, etc. Do not switch to another style based on mood alone.

For carousel/multi-poster sets:

- Lock one style token.
- Lock one mood phrase with explicit color direction: dominant palette, accent colors, color
  temperature, lighting, contrast, and atmosphere.
- Keep the same color grading across the set; do not let one image become warm amber while another
  becomes blue/purple unless the user explicitly requests that contrast.
- Image 1 becomes the visual anchor for all later images.

---

## Step 4 — Choose Layout

Common ratios:

- `1:1` → 1080x1080
- `4:5` → 1080x1350
- `16:9` → 1920x1080
- `9:16` → 1080x1920

Templates:

- **T1 Top-image Bottom-text:** subject top 60%; text bottom 35-40%
- **T2 Left-image Right-text:** subject left; text right 45-50%
- **T3 Full Bleed:** image full canvas; text bottom 35% overlay
- **T4 Centered Frame:** centered subject; top/bottom text clear
- **T5 Overlay Card:** subject top/side; text in center-bottom card
- **T6 Diagonal Split:** subject one side; text other side
- **T7 Grid:** multiple products, consistent framing
- **T8 Type-dominant:** mostly typography, image optional
- **C1 Bold Hero:** carousel hook, bottom 40% overlay
- **C2 Split Content:** image top 55%, text bottom 45% solid area
- **C3 CTA Focus:** minimal image, centered CTA

### Protected Text Zone

The text zone is protected space, not something to fix later with a dark overlay.

- Hero subject, face, hands, logo, product label, receipts, signs, menus, screens, and meaningful
  details must stay outside it.
- It should contain only low-detail negative space: wall, sky, floor, counter shadow, bokeh,
  blurred ground, smooth gradient.
- If meaningful objects land there, regenerate the AI image. Do not hide them with overlay.
- Do not write `subject fills the full frame` when text needs space.

---

## Step 5 — Generate AI Image

Call `image_generate`.

Supported params only:

- `prompt`
- `style`
- `aspect_ratio`
- `reference_image_urls`

Prompt must include:

1. format, brand, poster purpose, product/category
2. one hero visual
3. scene, lighting, camera feel, realism
4. selected template and protected text zone
5. brand asset integration instructions
6. clean constraints

### Brand Asset Integration

Always pass logo/product/reference URLs in `reference_image_urls` and describe each in the prompt.
Do not attach assets silently.

Pattern:

```text
Reference images: integrate the provided [logo/product/mascot] into the image as [exact placement].
Preserve [shape/colors/wordmark/icon/product details]. Do not redesign, distort, recolor, or
replace it. Keep it outside the protected text zone and secondary to the hero subject.
```

Logo placement examples:

- default: small crisp brand mark in the top-right corner, about 8-12% canvas width, with safe margin
- if top-right overlaps the hero subject or important detail, use top-left
- use bottom-right only when it is outside the protected text zone and not competing with CTA/copy
- use an in-scene carrier only when corners are unsuitable: wall sign, counter card, sticker,
  packaging label, door decal, uniform patch, menu stand with no readable menu text
- if the text zone is bottom 35-40%, do not say `lower-right corner`; place the logo above the
  protected text zone on a concrete object/surface: phone base, wall sign, counter card, packaging
  label, door decal, uniform patch, or menu stand with no readable menu text

AI should integrate logo/product/assets into the generated image itself. Pillow writes final
marketing copy.

One-logo policy:

- Pillow must not add a second logo by default. Logo placement should come from the AI image
  prompt and `reference_image_urls`.
- Add an exact Pillow logo overlay only when the user explicitly asks for logo correction.
- Do not create duplicate logos or large ghost/watermark logos.
- Default corner priority: top-right → top-left → bottom-right only if outside text zone.
- If the layout uses a bottom text zone, do not ask AI to put the logo in the bottom-right unless
  that corner is outside the text zone.

When writing the image prompt, specify both the carrier and the forbidden area:

```text
Integrate the provided logo as a small crisp brand mark in the [top-right/top-left] corner, outside
the protected text zone, about 8-12% canvas width with safe margin. If corners are unsuitable, use
a small [wall sign/counter card/sticker] on [specific object/surface] above the protected text zone.
Do not place any logo, watermark, or brand mark inside the protected text zone.
```

Allowed text-like visual in AI image: the provided brand logo only.

Forbidden in AI image:

```text
random text, random logos, watermark, invented menu text, garbled signs, cluttered layout,
important details inside the protected text zone
```

Template prompt constraints:

- T1/C2: subject top 55-60%; bottom text zone quiet
- T2: subject left; right text zone quiet
- T3/C1: bottom 35-40% has only shadow/gradient/blur
- T4: centered subject; top/bottom clear
- T5: card area has no important details
- T6: opposite text side clear
- T7: consistent product framing, no generated product-name text
- T8/C3: background/brand asset only if no main image needed

### Multi-image Consistency

For carousel or related multi-poster sets:

1. Generate image 1 first.
2. Inspect image 1 and write a style anchor that describes style only:
   `warm amber restaurant photography, high contrast, realistic motion blur, 35mm documentary feel`
   Do not include the same character, pose, object arrangement, or camera framing in the anchor.
3. For every later image:
   - include image 1 URL in `reference_image_urls`
   - include all logo/product references
   - use same `style` and `aspect_ratio`
   - use the prewritten scene structure for that image
   - append:

```text
Use the first image only as a style reference. Keep the same visual language: [style anchor].
Follow the prewritten scene structure for this image. Do not copy scene structure from image 1.
```

Never generate related images in parallel.

If two generated images look like near-duplicates, regenerate the later image with stronger scene
variation while keeping the same style anchor.

---

## Step 6 — Pillow Composite

Composite only after AI image passes QC.

Layer order:

```text
AI image → overlay/card/block → text → optional exact logo correction
```

Logo correction is not default. Do not add a Pillow logo unless the user explicitly asks for logo
correction after reviewing the AI-integrated logo.

Fonts:

- Latin: `canvas-fonts/`
- Chinese: `/usr/share/fonts/opentype/noto/NotoSansCJK-*.ttc`
- Max 2 font families
- Avoid emoji/decorative Unicode unless a supporting font is loaded

Text sizes:

- Headline: start 72-96px, min 40-48px
- Subheadline: start 36-56px, min 26-32px
- Tags: start 28-40px, min 22-28px
- CTA: start 34-44px, min 26-30px

Rules:

1. Measure text with `font.getbbox()` or `draw.textbbox()`.
2. Wrap before shrinking when text is long.
3. Track bounding boxes; no overlaps.
4. Keep all text inside the selected text zone.
5. Cover/crop images proportionally; never stretch.
6. Use `canvas.paste(img, pos, img)` for alpha images.
7. Convert final image to RGB before saving.

### Overlays

Use overlays for readability, not to hide failed composition.

- Uniform dark zone → white text, no/light overlay
- Uniform light zone → dark text, no/light overlay
- Mid-tone zone → subtle dark overlay
- Textured but abstract zone → stronger gradient overlay
- Meaningful object in text zone → regenerate AI image

Semi-transparent shapes must use a separate layer:

```python
shape_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
shape_draw = ImageDraw.Draw(shape_layer)
shape_draw.rounded_rectangle(box, radius=6, fill=(255, 255, 255, 60))
canvas = Image.alpha_composite(canvas.convert("RGBA"), shape_layer)
```

Then draw text. Never draw white text on white/near-white tag pills.

Output paths:

- Single: `/mnt/session/outputs/poster_{slug}.png`
- Set/carousel: `/mnt/session/outputs/poster_{slug}_slide{n}.png`

---

## Step 7 — Quality Review

Strictly review every image twice: once immediately after AI generation, and once after Pillow
composition. For sets/carousels, do not move to the next image until the current image passes both
checks. Retry up to 3 times.

### AI Image QC — before Pillow

Fail and regenerate the AI image if any item is true:

- The protected text zone contains the hero subject, logo, product label, receipt, screen, menu,
  sign, face, hands, or other meaningful detail.
- The logo is inside the protected text zone, too large, duplicated, distorted, or watermark-like.
- The AI image contains random text/logos/watermarks. Only the provided brand logo is allowed.
- A prop contains readable generated text unless the storyboard explicitly requires that exact text.
- The scene structure does not match the storyboard: setting, hero subject, action, key props,
  camera/framing, text zone, or logo placement are wrong.
- A set/carousel image does not match the shared style anchor, or it looks like a near-duplicate
  of another image.
- The image is cluttered where copy must go.

### Composite QC — after Pillow

Fail and re-composite if any item is true:

- Text is hard to read, clipped, overlapped, or outside the selected text zone.
- Text covers the hero subject, AI-integrated logo, product, face, hands, or meaningful prop.
- Tags/cards have white bars, white-on-white text, or broken alpha blending.
- Approved copy is missing, duplicated, misspelled, or lower priority copy overpowers the headline.
- Glyphs are missing or rendered as boxes.
- Pillow added a logo without explicit user-requested logo correction.
- Final image is stretched, cropped badly, or saved with wrong dimensions.

If AI image fails protected-zone or asset QC, regenerate AI image. If only text layout fails,
fix Pillow and re-composite.

---

## Output

Call `show_post_preview`.

Single:

```text
slides: [{ path: "/mnt/session/outputs/poster_{slug}.png", label: "Poster" }]
caption: "One sentence explaining the design decision"
hashtags: []
```

Carousel / set:

```text
slides: [
  { path: "/mnt/session/outputs/poster_{slug}_slide1.png", label: "Slide 1 · Hook" },
  { path: "/mnt/session/outputs/poster_{slug}_slide2.png", label: "Slide 2 · Content" }
]
caption: "One sentence explaining the set narrative"
hashtags: []
```
