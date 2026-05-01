# Pillow Compositing Rules

## Layer Order

```
Base color / background image → Product image → Overlay / mask → Decorations → Text layer
```

Text is always the topmost layer. Nothing may cover text.

## Font Selection

- Chinese: NotoSansCJK family (Bold → headline, Medium → subheadline, Regular → body, Light → small text, Black → large price)
- Luxury / cultural contexts: use NotoSerifCJK family instead
- English / numbers: select from `canvas-fonts/` directory by style
- Chinese font path: `/usr/share/fonts/opentype/noto/NotoSansCJK-{Weight}.ttc`

## Text Size Hierarchy

| Level | Usage | Size |
|-------|-------|------|
| L1 | Price / key number | 80–160px |
| L2 | Headline | 48–72px |
| L3 | Subheadline / features | 26–36px |
| L4 | Tag group | 24–32px |
| L5 | Contact / fine print | 20–26px |

## Mandatory Rules

1. **Prevent overflow**: before drawing any text, use `getbbox` to check width. If it exceeds `canvas_width - 80px`, reduce font size step by step
2. **Prevent overlap**: track each text element's bounding box (x0, y0, x1, y1). Subsequent text must not intersect
3. **Transparent compositing**: when pasting an image with alpha, always pass the third mask argument: `canvas.paste(img, pos, img)`
4. **Image fitting**: use proportional scale + center crop (cover mode). Never stretch with raw resize
5. **Color format**: use RGB tuples `(R, G, B)` for Pillow fill, not hex strings
6. **Tag group wrapping**: lay out tags horizontally, use `getbbox` for each tag width, wrap to next line when exceeding right boundary
7. **Gradient overlay**: draw line by line, transitioning alpha from 0 to target value, to avoid banding
8. **Canvas size**: hardcode `(1080, 1080)` at the top of the script. Never derive from image dimensions
9. **Symbol safety**: never use decorative Unicode symbols (✦ ✿ ★ ◆ ❤ ✔ etc.) as text characters — NotoSansCJK does not cover them and they render as □. Replace with Pillow-drawn geometry (circles, lines, rectangles, polygons) or load `/usr/share/fonts/truetype/noto/NotoSansSymbols2-Regular.ttf` as a dedicated symbol font
10. **Image mode normalization**: before any `paste()`, convert the source image with `img.convert("RGBA")`. After all compositing is done, convert the final canvas with `canvas.convert("RGB")` before saving
11. **Multi-line text wrapping**: never rely on font size reduction alone for long strings. Implement character-by-character wrapping: accumulate characters until `getbbox` width exceeds the allowed zone, then break to a new line. Apply this before any font size step-down
12. **Line spacing**: set line height = font size × 1.4 for Chinese text, × 1.25 for Latin/numeric text. Never stack lines using font size alone
13. **Chinese / Latin font split**: render Chinese characters with NotoSansCJK and Latin characters (A–Z, a–z, 0–9, punctuation) with the matching `canvas-fonts/` typeface. Split mixed strings by character range and draw each segment with its own font object

## Brightness Analysis

Before placing text, analyze the brightness of the target text zone using PIL pixel data:

```python
region = canvas.crop((x0, y0, x1, y1)).convert("L")
brightness = sum(region.getdata()) / (region.width * region.height)
```

| Brightness | Action |
|------------|--------|
| > 180 | Add heavy gradient overlay (alpha 180–220), use white text |
| 60–180 | Add semi-transparent overlay (alpha 120–160), use white text |
| < 60 | Light or no overlay (alpha 60–100), use white text |

Always compute brightness **after** the background image is composited, **before** drawing text.

## Dynamic Font Sizing

Never hardcode font sizes. For each text element:

1. Start at the template's maximum size (L2 headline: 72px, L3 subheadline: 34px)
2. Measure text width with `draw.textbbox((0, 0), text, font=font)[2]`
3. If width exceeds the zone width, reduce by 4px and repeat
4. Minimum floor: 36px for headline, 22px for body
5. Apply line wrapping (rule 11) at the final size before drawing

## Per-Image Compositing Order

Each image must be composited independently in this sequence — never batch multiple images in a single loop:

1. Load raw image asset
2. Read text zone coordinates from the selected template (poster-layout.md)
3. Composite base layer (solid color or background image)
4. Composite product image using cover-crop into its template zone
5. Analyze brightness of text zone (see Brightness Analysis above)
6. Add gradient overlay if required
7. Add decorative color blocks / lines
8. Draw text layers with dynamically computed font sizes
9. Composite logo (bottom-right, if path exists)
10. Save output file