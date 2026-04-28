---
name: poster-design
description: >
  Complete poster design workflow. Design publish-ready promotional posters (single or Carousel multi-image) from scratch: context reading, narrative planning, copywriting, style decision, layout design, color system, asset generation, Pillow compositing, quality review.
  Suitable for scenarios where the business needs a dedicated poster design — new product launches, promotional campaigns, brand awareness, holiday promotions, etc.
integrations: []
---

# Poster Design

## Step 1 — Context Reading

Read all available context by priority; infer directly what can be inferred, do not ask:

1. `/workspace/marketing-context.md` — brand name, industry, tone, brand composition style, target audience, color system
2. User message — extract: poster theme, target audience signals, required text

Determine directly:
- **Mode**: single poster or Carousel multi-image (infer from user message or platform)
- **Promotional purpose**: persuade whom to do what
- **Target audience**: their aesthetic preferences and decision-making psychology
- **Publication size**: for single posters, infer from platform; if unable to infer, default to 1080x1080; Carousel fixed at 1080x1350px
- **Brand assets**: read the "Brand Assets" section of `marketing-context.md`, extract Logo and mascot path list (may be empty)

The only situation requiring follow-up: theme is completely missing, unable to determine what this poster is promoting.

---

## Step 1.5 — Carousel Narrative Planning (only execute for Carousel)

Read `/mnt/skills/poster-design/features/carousel.md`, select a narrative mode based on promotional purpose, and plan the narrative role for each slide:

- If the user has not specified a mode, default to **humorous interactive**.
- If the promotional purpose is product promotion, prefer **humorous product seeding**, with **product rescue** as the first choice; check modes already used in this conversation to avoid repetition, rotate in order (cautionary seeding -> wrong way to use -> product personification monologue -> exaggerated review).

Output planning table:

| Slide | Narrative Role | One-sentence Theme Direction |
|-------|---------------|------------------------------|
| 1 | Hook | ... |
| 2–N | Single-point content | Each slide covers only one topic |
| Last | CTA | Call to action |

**Inform the user of each slide's narrative role and theme direction, wait for confirmation before continuing.**

---

## Step 2 — Copywriting

Based on the promotional purpose and confirmed narrative structure, write all text content.

**Single poster**:
- Headline
- Subheadline (optional)
- Selling point tags (optional, 2–4)
- Price (if applicable)
- CTA text

**Carousel**: write complete copy for each slide according to the narrative planning table —
- Each slide: main headline + description text (1–2 lines) + optional small tags

After writing, **present to the user for confirmation**; only continue after confirmation.

---

## Step 3 — Style Decision

Read `/mnt/skills/poster-design/features/styles.md`, decide the style according to selection logic, default **Photography**.

Select the most effective style based on promotional purpose (emotional resonance / problem solving / impulse purchase / trust building / curiosity attraction) and audience psychology.

Lock in the **style token**, keep it consistent throughout; all Carousel slides maintain the same style.

**Images must be clean**: generated images should have a clean background, clear subject, no visual clutter. In step 6 image generation prompts, always include `clean background, clear subject, no visual clutter`.

---

## Step 4 — Layout Design

Read `/mnt/skills/poster-design/features/poster-layout.md`.

- **Single poster**: select one of T1–T8 according to template selection logic.
- **Carousel**: select templates by narrative role — Hook -> C1, Content -> C2, CTA -> C3.

Record the selected template; step 6 asset generation and step 7 compositing both follow this template's region definitions.

---

## Step 5 — Color System

Read `/mnt/skills/poster-design/features/colors.md`, reference the palette system, and select or combine colors based on brand tone and promotional purpose.

Color tone and style must be consistent with the brand composition style recorded in `marketing-context.md`, based not on specific color values but on overall visual atmosphere matching.

All Carousel slides use the same color tone description.

---

## Step 6 — Asset Generation

### 6a. Main Image Assets

**User has a clear Reference Image** -> use directly for compositing, skip generation.

**User has a Reference Image but it is blurry or low quality** -> regenerate using the reference as a guide, improving quality and style consistency.

**User has no Reference Image** -> generate asset images based on the following three sets of information:

**1. Style keywords**
- style token (step 3)
- Image Tone Keywords (step 5 palette)
- `clean background, clear subject, no visual clutter`

**2. Template region constraints** (from the template selected in step 4)

| Template | Image Generation Size and Composition Constraints |
|----------|--------------------------------------------------|
| T1 | Image fills top 60%, compose at 1080x648, subject fully presented within this area |
| T2 | Image fills left 50%, compose at 540x1080 |
| T3 | Full image 1080x1080, subject stays in top 65%, bottom 35% will be covered by gradient overlay |
| T4 | Transparent background, centered subject, approx 600x500 composition area |
| T5 | Full image, center-bottom area will be covered by semi-transparent card, subject biased top or side |
| T6 | Full image, diagonal split, subject on one side of image |
| T7 | Multiple small images, each with uniform background color and composition |
| T8 | Optional small image, not the visual hero |
| C1 | Full image 1080x1350, subject stays in top 60%, bottom 40% will be covered by gradient overlay |
| C2 | Image fills top 55%, compose at 1080x742 |
| C3 | Usually no main image needed, skip |

**3. Copy-theme alignment**
The image's scene, mood, and visual atmosphere must match the copy content confirmed in step 2; reflect what the copy expresses in the prompt.

**`negative_elements` must include**: `text, typography, letters, numbers, watermark, busy background, cluttered, decorative noise`

**Carousel consistency**: from slide 2 onward, pass slide 1's generated image as reference image to maintain scene/style coherence. C3 usually does not need a main image, skip.

### 6b. Background Image

| Template | Handling Method |
|----------|----------------|
| T3 (full bleed) / T5 (overlay card) / C1 (Bold Hero) | Generate texture or gradient background image |
| T1 / T2 / T4 / T6 / T7 / T8 / C2 / C3 | Draw directly in Pillow using step 5 base color, no generation needed |

---

## Step 7 — Pillow Compositing

Strictly follow all rules in `/mnt/skills/poster-design/features/pillow-rules.md`.

**Composite each slide independently**, execute each slide in the following order, complete and pass step 8 quality review before processing the next slide.

### Per-slide Compositing Flow

**1. Load image**
Load the current slide's original image asset.

**2. Determine text region coordinates**
Based on the template selected in step 4, read the current slide's text region bounds (x0, y0, x1, y1) from `poster-layout.md`.

**3. Analyze brightness -> decide overlay and text color**
Calculate the mean brightness of the text placement region:
- Mean > 180: region is bright -> darken overlay (alpha 180–220), white text
- Mean 60–180: midtone -> semi-transparent overlay (alpha 120–160), white text
- Mean < 60: region is dark -> light overlay or none (alpha 60–100), white text

**4. Dynamically calculate font size and line wrapping**
Start from the template-defined max font size (L2 level starts at 72px), use `getbbox` to measure copy width; if it exceeds the text region width, reduce step by step (-4px each time) until it fits. Minimum font size no less than 36px. Line wrapping logic follows `pillow-rules.md` rule 11.

**5. Composite in layer order**
```
Base color/background image -> main image asset -> mascot (when user explicitly requests) -> gradient overlay (if needed) -> color blocks -> decorative lines -> text layer -> Logo
```

**6. Save, proceed to step 8 quality review**

**Single poster output**: `/mnt/session/outputs/poster_{slug}.png`

**Carousel output**: `/mnt/session/outputs/poster_{slug}_slide{n}.png`

**Logo compositing** (execute when `marketing-context.md` "Brand Assets -> Logo" has a path):
- **Quality preprocessing**: if logo has no transparent background -> first use `rembg` or threshold masking to remove background; if low resolution or blurry edges -> directly apply monochrome processing (extract alpha channel shape, fill with poster `text_color`, naturally crisp)
- **Multi-path selection**: when multiple paths exist, analyze background brightness at the logo placement area: bright background (> 128) use the first one, dark background (<=128) use the second one; if only one path, apply monochrome processing
- **Position and size**: bottom-right corner, 24px from edge; width no more than 12% of canvas width, maintain original aspect ratio
- Composite using Pillow `Image.alpha_composite`, preserve transparency channel
- **When generating a new version**: save the processed file to `/workspace/assets/`, and append a line `path — note` to the corresponding field under "Brand Assets" in `marketing-context.md` to avoid reprocessing next time

**Mascot compositing** (execute only when user explicitly requests adding a mascot):
- Position defined by the template selected in step 4; size: height no more than 35% of canvas height, maintain original aspect ratio
- Paste directly, no blend mode needed

**Error handling**:

| Error | Handling |
|-------|----------|
| `FileNotFoundError` | Check path; download URL to local first using requests |
| `OSError: cannot open resource` | CJK font hardcoded to `/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc` |
| Output file is empty | Check whether `canvas.save()` was executed |

---

## Step 8 — Quality Review

**Execute immediately after each slide is composited**, do not wait for all Carousel slides to be complete. Read the output image, strictly check each item. Fix the script and redo the current slide immediately upon finding any issue; only continue to the next slide after confirmation of pass.

| Check Item | Pass Criteria | Fail Handling |
|------------|--------------|---------------|
| **Text contrast** | Each text element has clear contrast against its background area, small text is also legible | Adjust text color or darken overlay and redo |
| **Text overflow** | No text is clipped beyond the canvas edge | Reduce font size or adjust position and redo |
| **Text overlap** | No overlap between text layers, no tag stacking | Recalculate spacing and redo |
| Text completeness | All copy confirmed in step 2 appears on the image | Add missing content and redo |
| No garbled text | CJK text displays normally, no boxes | Check font path and redo |
| No box characters | All decorative symbols display normally, no boxes | Switch to Pillow geometric shapes or NotoSansSymbols2 and redo |
| Image not distorted | Background proportions are correct, subject is not cropped | Fix crop logic and redo |
| Style consistency | Step 3 style is visually reflected; all Carousel slides are visually unified | — |
| No redundant information | Same information does not appear in two places | — |

Maximum 3 redo rounds. If issues remain after 3 rounds -> state which item is blocked and request further guidance.

---

## Output

Call the `show_post_preview` tool to display the poster:
- **Single poster**: `slides: [{ path: "/mnt/session/outputs/poster_{slug}.png", label: "Poster" }]`
- **Carousel**: `slides` passes all paths in order, `label` indicates slide number and narrative role (e.g. "Slide 1 - Hook")
- `caption`: one sentence describing the core layout decision
- `hashtags`: `[]`
