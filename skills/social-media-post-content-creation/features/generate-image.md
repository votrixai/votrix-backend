# Generate Image

Use case: Generate image content for social media (no text overlay/typography). Single image or multi-image set (Carousel).

---

## Step 1 — Context Gathering

Read `/workspace/marketing-context.md` to extract brand name, industry, tone, brand composition style, and target audience. Combine with the user's message to determine:
- Post topic and promotional objective
- Single image or multi-image set

---

## Step 2 — Theme Design

**Single image**: Define one clear visual theme.

**Multi-image set (Carousel)**: First read `/mnt/skills/social-media-post-content-creation/features/carousel.md`, select a content pattern based on the promotional objective, and plan each slide's narrative role and visual direction.

- If the user has not specified a theme style, default to **Humor & Interaction**.
- If the promotional objective is product promotion, prefer **Humor & Product Seeding**, with **Product to the Rescue** as the first choice; but check which patterns have already been used in the current conversation to avoid repetition, cycling through other humor & product seeding patterns in order (Reverse Psychology Seeding → Wrong Way to Use It → Product First-Person Confession → Exaggerated Review).

Inform the user of each slide's theme and confirm before proceeding to style and color decisions.

---

## Step 3 — Style Decision

Read `/mnt/skills/social-media-post-content-creation/features/styles.md` and follow the selection logic to determine the style, defaulting to **Photography**.

Based on the promotional objective (emotional resonance / problem solving / impulse purchase / trust building / curiosity attraction) and audience psychology (everyday consumers are moved by authentic scenes, younger consumers are drawn to visual trends, business decision-makers are persuaded by professionalism, premium consumers are persuaded by restrained elegance), select the most effective style.

Lock in the **style token**; all slides in a multi-image set must use the same one.

---

## Step 4 — Color System

Read `/mnt/skills/social-media-post-content-creation/features/colors.md` and select or combine color tone keywords based on brand tone and promotional objective. The color tone must align with the overall visual atmosphere of the brand composition style recorded in `marketing-context.md`, not based on specific color values.

All slides in a multi-image set use the same color tone description.

---

## Step 5 — Generation

Pass in for each slide:
- Step 2's visual theme
- Step 3's style token
- Step 4's color tone keywords
- **Composition keywords**: Extract keywords from the brand composition style in `marketing-context.md` (e.g., layout approach, whitespace preference, element density, etc.); if not recorded, fall back to `single focal point, generous negative space, minimal elements, clean composition, focused subject, no clutter`
- If text overlay will be added later: specify `leave clean space in [position] for text overlay`
- `negative_prompt`: `text, watermark, logo, typography, busy background, cluttered, multiple competing subjects, decorative noise, visual complexity`

**Multi-image consistency**: From the 2nd slide onward, pass in the 1st slide as a reference image to maintain consistency in characters / scenes / style.

---

## Step 6 — Quality Check

| Check Item | Pass Criteria |
|-----------|--------------|
| No text | No text or watermarks in the image |
| Theme accuracy | Visual content matches the theme description |
| Sufficient whitespace | Areas designated for text overlay are clean |
| Multi-image consistency | All slides have unified style / color tone |

If any check fails, refine the description and regenerate.

---

## Output

Call `show_post_preview`, pass in slide paths in order, briefly describe the content direction in caption, and fill in hashtags based on the brand and content.
