---
name: canvas-design
description: Used only for initializing brand visual style. Based on brand name, industry, and style keywords, outputs a design philosophy document (.md) that defines the color system, typography character, composition direction, and aesthetic naming, serving as the visual style baseline for F1/F3/F4. Does not generate images or posters, does not respond to user content creation requests. Create original visual designs, never copying existing artists' work to avoid copyright violations.
license: Complete terms in LICENSE.txt
---

## Scope of Responsibility

**This skill outputs only one file: a design philosophy document (.md), saved to `/workspace/brand-style/philosophy.md`.**

- Does not generate any images (.png / .pdf)
- Does not include product information, prices, contact details, promotional copy, or CTA
- Downstream F1 (posters), F3 (AI images), F4 (AI videos) read this file as their visual style baseline

---

## Design Philosophy Creation

Based on brand name, industry, and style keywords, create a visual philosophy system.

### Step 1: Name the Aesthetic Movement (1–2 words)

Name an aesthetic movement for this brand's visual style. The name should be concise, evocative, and instantly conjure a visual feeling:

Examples: "Brutalist Joy" / "Chromatic Silence" / "Analog Meditation" / "Warm Craftsman" / "Aurora Geometry"

### Step 2: Write the Philosophy Manifesto (4–6 paragraphs)

Develop around the following five dimensions, one paragraph each, no repetition:

- **Space and Form**: proportion of whitespace, the language of shapes, rhythm of density and openness
- **Color and Texture**: the mood of primary colors, how color conveys brand character, expression of material quality
- **Scale and Rhythm**: size contrast, repeating elements, how visual rhythm is established
- **Composition and Balance**: position of visual focal point, tension and harmony between elements
- **Typography and Hierarchy**: personality of typefaces, how text is used as a visual element, information hierarchy

**Writing requirements:**
- Use poetic language to describe visual feelings, not technical specifications
- Emphasize craftsmanship repeatedly: "meticulously crafted," "painstaking attention," "master-level execution"
- Keep it universal, do not mention specific products or marketing intent
- Leave room for interpretation by downstream creation, do not over-constrain

### Step 3: Output Structured Style Specifications

After the philosophy manifesto, output the following structured fields for F1/F3/F4 to read directly:

```
## Style Specifications

### Aesthetic Name
[1–2 words]

### Color System
- Primary color: [color description + hex]
- Secondary color: [color description + hex]
- Accent color: [color description + hex]
- Overall color mood: [one sentence]

### Typography Character
- Style type: [Bold / Refined / Modern / Gentle]
- Recommended headline font: [font name, choose from canvas-fonts/]
- Recommended subheadline font: [font name]
- Recommended accent font: [font name, optional]

### Spatial Composition
- Composition type: [Immersive / Zoned / Layered / Framed]
- Whitespace tendency: [Spacious / Moderate / Compact]
- Visual focal point: [Center / Upper / Lower / Side]
```

### Philosophy Example (for reference, do not copy)

**"Concrete Poetry"**
Space and Form: Large color blocks dominate the canvas, geometric shapes carry a sculptural sense of weight...
Color and Texture: Colors are bold yet restrained, each color carries meaning rather than decoration...
(And so on, 4–6 paragraphs)

Style Specifications:
- Aesthetic Name: Concrete Poetry
- Primary color: Charcoal Black #1A1A1A
- Secondary color: Warm White #F5F0E8
- Accent color: Brick Red #C0392B
- Style type: Bold
- Composition type: Zoned

---

## Output

Save the complete content (philosophy manifesto + style specifications) as `/workspace/brand-style/philosophy.md`, do not output other files.
