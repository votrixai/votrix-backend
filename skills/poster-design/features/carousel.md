# Carousel Narrative Planning

## Specs

Canvas: 1080×1350px (4:5 portrait). Slides per set: 5–10.

## Narrative Rhythm

Every carousel follows the same pace: **Hook → Content → CTA**.

| Position | Role |
|----------|------|
| Slide 1 | Hook — stop the scroll with a bold headline or counterintuitive claim |
| Slides 2–N | Body — one single point per slide, no exceptions |
| Last slide | CTA — prompt save, follow, or click |

## Narrative Modes

### General Content (default)

| Mode | One-line summary | Flow |
|------|-----------------|------|
| Step-by-step Tutorial | One step per slide — finished scrolling = finished learning | Problem → Step 1 → Step 2 → Step 3 → Save CTA |
| Comparison Roundup | One option per slide, side-by-side showcase | Cover → A → B → C → Recommendation |
| Problem → Solution | Poke the pain first, then deliver the fix | Pain point → Root cause → Solution → Action CTA |
| Data + Testimonial | Numbers, screenshots, user feedback builds trust | Data cover → Evidence → Testimonial → Try CTA |

### Product Seeding (priority when promoting a product)

> Use humor to reduce ad fatigue — let users get hooked while laughing. Rotation order: Product Rescue → Reverse Warning → Wrong Way → Product Monologue → Exaggerated Review.

| Mode | One-line summary | Flow |
|------|-----------------|------|
| Product Rescue | Show the painful problem first, product swoops in to save the day | Relatable struggle → escalation → product enters → before/after → CTA |
| Reverse Warning | "Don't buy this" reverse psychology — the more you warn, the more they want it | Warning cover → list "flaws" (actually selling points) → twist recommendation → Buy CTA |
| Wrong Way | Show what happens when used wrong, then reveal the right experience | "Don't do this" → wrong outcome → correct usage → satisfying contrast → CTA |
| Product Monologue | Product speaks in first person, "complaining" about being underestimated | "Nobody knows I can..." → feature reveal per slide → user surprise reaction → CTA |
| Exaggerated Review | Dramatize the product's effect for comedic impact | Outrageous promise cover → test each claim → dramatic reaction → honest conclusion → CTA |

## Mode Selection Logic

```
Goal: promote a specific product
  └─ Use Product Seeding, start with "Product Rescue"
     └─ Check modes already used in this conversation — skip repeats,
        rotate to next in order

Goal: brand awareness / education / content
  └─ Use General Content, pick by desired outcome:
       Save rate     → Step-by-step Tutorial, Comparison Roundup
       Trust         → Data + Testimonial, Problem → Solution
       Direct action → Problem → Solution
```
