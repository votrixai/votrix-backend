# Poster Color System

> These presets are references only. You are encouraged to freely compose colors based on brand context, campaign tone, and visual goals — do not treat these as a rigid selection list. Mix, adjust, or create entirely new palettes when the situation calls for it.

## 12 Preset Palettes

Each palette defines: base (background), main (blocks/decoration), text, accent (price/CTA), and image tone keywords.

| # | Name | Base | Main | Text | Accent | Image Tone Keywords |
|---|------|------|------|------|--------|-------------------|
| P1 | Warm Apricot | #FFF8F0 | #D4884A | #8B4513 | #E85D24 | `warm amber tones, soft golden light, cream background` |
| P2 | Chinese Red | #C62828 | #FF1744 | #FFFFFF | #FFD700 | `rich red tones, festive gold accents, warm dramatic lighting` |
| P3 | Honey Gold | #FFFBEB | #D4A017 | #3E2C1A | #E85D24 | `warm honey tones, golden hour light, caramel warmth` |
| P4 | Berry Pink | #FFF5F5 | #E8829A | #4B1528 | #D4537E | `soft pink tones, gentle blush light, pastel rose` |
| P5 | Business Blue | #F0F7FF | #2563EB | #1E293B | #0EA5E9 | `cool blue tones, clean studio light, professional` |
| P6 | Fresh Green | #ECFDF5 | #10B981 | #064E3B | #34D399 | `fresh green tones, natural daylight, vibrant nature` |
| P7 | Elegant Purple | #F5F3FF | #7C3AED | #2E1065 | #A78BFA | `soft violet tones, dreamy ambient light, elegant` |
| P8 | Mint Teal | #F0FDFA | #14B8A6 | #134E4A | #2DD4BF | `cool mint tones, clean bright light, refreshing` |
| P9 | Dark Gold | #1A1A1A | #C5A55A | #F5F5F5 | #E8C564 | `dark moody tones, golden accent light, luxury` |
| P10 | Cream White | #FAF9F6 | #A89F91 | #3D3D3A | #6B5B4A | `muted warm neutrals, soft diffused light, minimal` |
| P11 | Earth Brown | #F8F6F0 | #8B7355 | #3B2F1E | #C4956A | `earthy brown tones, warm natural light, rustic` |
| P12 | Space Gray | #2D3748 | #63B3ED | #E2E8F0 | #48BB78 | `dark tech tones, cool neon accent, futuristic` |

## Text Color Rules

- **Light base** (P1, P3–P8, P10–P11): headline uses text color, price/CTA uses accent color
- **Dark base** (P2, P9, P12): headline uses #FFFFFF, price/CTA uses accent color
- **Over image** (T3/T5): detect background brightness → dark region (<100) use white, light region (>180) use palette text color, mid-tone region add semi-transparent overlay then white text

## Brand Color Override

When brand color exists: replace the "main" role with brand color, keep others unchanged. If contrast ratio between brand color and base is below 4.5:1, switch palette.