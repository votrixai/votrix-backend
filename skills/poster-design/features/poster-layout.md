# Poster Layout Templates

> All coordinates based on 1080×1080 canvas. Scale proportionally for other sizes. Safe margin: 40px.

## Template Selection

```
Single product + info-heavy (price/tags/features) → T1 Top-image Bottom-text
Single product + brand focus                      → T4 Centered Frame
Multi-product / combo                             → T7 Grid
Brand campaign / mood-driven                      → T3 Full Bleed
Premium + complex info                            → T5 Overlay Card
Product feature introduction                      → T2 Left-image Right-text
Event announcement / grand opening                → T8 Type-dominant
Young / trendy audience                           → T6 Diagonal Split
Cannot determine                                  → T1 Top-image Bottom-text
```

## Template Definitions

### T1 — Top-image Bottom-text
Image fills top 60% (y:0–648). Text area fills bottom 40% (y:648–1080, solid color fill). Text stacks top-down: headline → subheadline → price → tag group → CTA. Image does not need whitespace for text.

### T2 — Left-image Right-text
Left 50% for product image (x:0–540). Right 50% for text area (x:540–1080, solid color). Text left-aligned, top-down: headline → subheadline → feature list → price → CTA.

### T3 — Full Bleed
Image fills 100% of canvas. Bottom 35% gets a gradient overlay (transparent → black or brand color). Text sits on the overlay in white/light color. When generating the image, note that bottom 35% will be covered by overlay.

### T4 — Centered Frame
Solid color or gradient background. Product image centered (approx 600×500, requires transparent background). Headline above, price and CTA below.

### T5 — Overlay Card
Background image fills canvas (can be blurred). Semi-transparent rounded rectangle (60–80% opacity) placed center-lower. All text arranged inside the card.

### T6 — Diagonal Split
Canvas split along a diagonal line. One half image, other half solid color with text. Angle 15–30°. Suits dynamic/trendy feel.

### T7 — Grid
Title banner at top (160px). 2×2 grid below, each cell contains product image + name + price. Store info at bottom. Each product image generated separately with uniform background and composition.

### T8 — Type-dominant
Solid color or gradient background. Large headline (80–120px) is the visual hero. Image is optional small accent. Suits event announcements, grand openings.

---

## Carousel Layout Templates

> Canvas: 1080×1350px (4:5). Safe margin: 40px. All coordinates based on this size.

### Slide Role → Template

```
Hook（第 1 张）     → C1 Bold Hero
Content（中间张）   → C2 Split Content
CTA（末张）        → C3 CTA Focus
```

### C1 — Bold Hero
Image fills full canvas. Bottom 40% (y:810–1350) gets gradient overlay (transparent → brand dark color). Headline sits on overlay: large font 80–100px, white or light color. Optional subline below headline, 32–40px. Image generation note: bottom 40% will be covered — keep top 60% compositionally strong.

### C2 — Split Content
Top 55% (y:0–742): image fills this area, no text. Bottom 45% (y:742–1350): solid brand color or near-white fill. Text top-down inside bottom area: single-point headline (56–72px) → 1–2 lines of body copy (32–36px) → optional small tag. Each slide only carries one key point — do not stack multiple messages.

### C3 — CTA Focus
Solid brand color background (no image, or small accent image in top-right corner, max 30% of canvas). Center-aligned text stack: brand name / logo placeholder (top) → CTA headline 60–72px → action instruction 34–40px (e.g. 点击关注 / 收藏备用 / 点击跳转) → optional QR code or handle. High contrast, minimal visual noise.

### Carousel Image Requirements

| Template | Image Role | Background Requirement |
|----------|-----------|----------------------|
| C1 | Full-bleed scene or product hero | Atmospheric, strong top composition |
| C2 | Top-area supporting visual | Any, content-relevant per slide |
| C3 | Optional small accent only | None required |

### Carousel Consistency Rules

- All slides share the same **style token**, **color palette**, and **font family** from the main workflow.
- Generate C1 image first; pass it as reference image for C2+ slides.
- Pillow script uses shared variables (`font_path`, `primary_color`, `accent_color`, `bg_color`) and a `slides = [...]` list to loop over all slides, varying only the main image path and text content per slide.
- Output each slide as `/mnt/session/outputs/poster_{slug}_slide{n}.png`.

---

## Image Requirements per Template

| Template | Image Role | Background Requirement |
|----------|-----------|----------------------|
| T1 | Main visual, fills image area | Any |
| T2 | Main visual, left half | Transparent or solid preferred |
| T3 | Full-screen background | Atmospheric scene |
| T4 | Centered showcase | **Must be transparent** |
| T5 | Background layer | Atmospheric, can be blurred |
| T6 | Cropped material | Any |
| T7 | Multiple small images | Uniform background color |
| T8 | Optional accent | Any |