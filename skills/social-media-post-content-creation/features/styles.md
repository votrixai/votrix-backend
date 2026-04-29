# Poster Image Styles

> Defines the visual style for generated poster images. Default: Photorealistic.

## Composition Principles (all styles)

> **Clean · Minimal · Focused** — Apply to every generated image regardless of style choice:
>
> | Principle | Requirement |
> |-----------|-------------|
> | **Single focal point** | One dominant visual subject per image — no competing elements |
> | **Generous negative space** | At least 40% of the frame is breathing room around the subject |
> | **Element restraint** | No more than 3 visible elements; strip all purely decorative clutter |
> | **Emotion or message first** | Composition serves the core emotion or information — never adds complexity for richness |
>
> These four rules override style preferences and apply to every generated image.

---

## Style Selection

**Default: A Photography. Always start here. Only deviate when there is an explicit, clear reason to do otherwise.**

```
Ambiguous or unspecified            → A Photography (default — do not guess alternatives)
User's brand style is illustration  → B1 Flat/Geometric or B2 Painterly (realistic first if possible)
User's brand style is 3D           → C 3D Render
User's brand style is vintage       → D Retro
Needs mixed-media / conceptual      → E Hybrid
```

> **Realism preference**: When in doubt, lean toward the most photorealistic option available within the chosen style. Illustration and 3D styles should still aim for realistic lighting and proportions over stylised abstraction.
>
> **Cartoon styles (B3) are opt-in only**: Only select Modern Cartoon, Anime, or Chibi when either (a) the user explicitly requests a cartoon or animated look, or (b) the brand's visual identity is already cartoon-based — e.g., the logo is illustrated/cartoon, there is a cartoon mascot, or `marketing-context.md` describes a playful/animated brand style. Do not infer this style from audience age or tone alone.

---

## A. Photography (default)

| Style | Use Case | Prompt Keywords |
|-------|----------|-----------------|
| Product shot | E-commerce, single product | `product photography, white background, soft studio lighting` |
| Lifestyle | Product in real-use setting | `lifestyle product photography, natural setting, in-context` |
| Food | F&B, food brands | `food photography, overhead shot, warm lighting, shallow depth of field` |
| Portrait | Beauty, fashion | `studio portrait, softbox lighting, clean background` |
| Cinematic | Brand campaigns, mood | `cinematic photography, anamorphic, film color grading, dramatic lighting` |
| Film grain | Artistic, vintage brands | `film photography, Kodak Portra 400, grain, analog` |
| Aerial | Real estate, travel, outdoor | `aerial photography, drone shot, bird's eye view` |

---

## B. Illustration

### B1. Flat / Geometric
| Style | Use Case | Prompt Keywords |
|-------|----------|-----------------|
| Flat | Tech, education, app promo | `flat illustration, bold shapes, limited palette, no gradients` |
| Geometric | Modern, abstract expression | `geometric illustration, abstract shapes, clean composition` |
| Minimalist line | Premium, minimal brands | `minimalist vector art, simple lines, negative space, 2-3 colors only` |
| Line art | Artsy, handcraft feel | `line art illustration, continuous line, monochrome, elegant` |

### B2. Painterly
| Style | Use Case | Prompt Keywords |
|-------|----------|-----------------|
| Watercolor | Floral, maternal, soft brands | `watercolor illustration, soft washes, visible brushstrokes, paper texture` |
| Ink wash | Chinese tea, cultural brands | `ink wash painting, sumi-e style, black ink on white, zen minimalism` |
| Oil painting | Premium food, wine | `oil painting style, thick brushstrokes, rich colors, canvas texture` |

### B3. Cartoon ⚠ Explicit request only
> Only use if the user explicitly requests cartoon/anime/chibi, **or** the brand's visual identity is already cartoon-based (cartoon logo, mascot, or animated brand style in `marketing-context.md`). Do not infer from tone or audience age alone.

| Style | Use Case | Prompt Keywords |
|-------|----------|-----------------|
| Modern cartoon | Kids, fun promos | `modern cartoon style, bold outlines, geometric shapes, vibrant colors` |
| Anime | Young audience, ACG | `anime style, cel shading, large expressive eyes, dynamic pose` |
| Chibi / kawaii | Cute merch, IP mascots | `chibi style, super deformed, large head tiny body, kawaii` |

---

## C. 3D Render

| Style | Use Case | Prompt Keywords |
|-------|----------|-----------------|
| Product render | Electronics, industrial | `product render, industrial design, studio lighting, reflective surface` |
| Cartoon 3D | Fun promos, IP mascots | `3D cartoon render, Pixar style, soft lighting, subsurface scattering` |
| Isometric | Infographics, process flow | `isometric 3D illustration, 30-degree angle, flat colors, clean render` |
| Claymation | Cute, handcraft brands | `claymation style, plasticine texture, fingerprint marks, stop-motion feel` |
| Diorama | Creative showcase, real estate | `miniature diorama, tilt-shift effect, real material textures` |

---

## D. Retro

| Style | Era | Use Case | Prompt Keywords |
|-------|-----|----------|-----------------|
| Art Nouveau | 1890s | Floral, beauty, organic | `Art Nouveau style, organic curves, floral patterns` |
| Art Deco | 1920s | Luxury, hotel, jewelry | `Art Deco style, geometric symmetry, gold accents, elegant linework` |
| Mid-century | 1950s | Home, cafe | `mid-century modern illustration, retro poster, halftone dots, limited palette` |
| Pixel art | 8-bit | Gaming, tech, young | `pixel art, 16-bit retro game style, limited color palette, crisp pixels` |
| Synthwave | 80s | Esports, tech, nightlife | `synthwave, neon grid, retro sunset, chrome text, 80s sci-fi` |

---

## E. Hybrid

| Style | Use Case | Prompt Keywords |
|-------|----------|-----------------|
| Photo + line overlay | Creative marketing, social | `photo with hand-drawn line overlay, annotation style, mixed media` |
| Collage | Fashion, trendy, art | `mixed media collage, photo cutouts, hand-drawn elements, textured layers` |
| Gradient abstract | Background, mood base | `gradient mesh, fluid colors, soft blending, aurora-like, abstract background` |
