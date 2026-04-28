---
name: social-media-post-content-creation
description: >
  Social media content creation. Plan upcoming posts, confirm asset requirements, generate images/videos/copy, present to user for review, and save as drafts for scheduled publishing.
  Trigger scenarios: (1) [cron] Weekly scheduled content plan drafting; (2) User ad-hoc content generation requests.
integrations: []
---

# Social Media Content Creation

## Trigger Logic

- `[cron] Content Co-creation` → **Phase 1**: Draft this week's content plan
- User sends assets (images / videos) or says "here are the assets" → **Phase 3**: Create directly
- User ad-hoc request ("make me a poster", "create some images for me") → **Phase 3**: Create directly

---

## Phase 1 — Content Plan

Read `/workspace/marketing-context.md` to understand brand name, industry, tone, connected platforms, posting cadence, and content direction.

Based on connected platforms, read the corresponding reference files to understand dimension specs, caption limits, hashtag counts, and weekly content ratios:
`/mnt/skills/social-media-post-content-creation/references/{platform}.md`

Draft entries for each post scheduled this week based on the current week's dates:

| Field | Description |
|-------|-------------|
| Date | Planned publish date |
| Platform | Instagram / LinkedIn / Twitter, etc. |
| Content Type | Single Image Poster / Carousel / Reels / Story (Instagram only) |
| Topic | What this post is about, in one sentence |
| Asset Requirement | AI-generated / User-provided image / User-provided video |

**Content Type Selection:**

| Scenario | Type |
|----------|------|
| Multiple products / multiple selling points / step-by-step tutorial / before-and-after comparison | Carousel |
| Single strong visual / simple announcement / holiday poster | Single Image Poster |
| Behind-the-scenes story / making-of process / video assets available | Reels |
| Quick interaction / limited-time offer (Instagram only) | Story |

When unsure which type to choose, refer to the weekly ratio in the corresponding platform reference file and fill in whichever type is underrepresented that week.

**Cross-Platform Asset Reuse:**
If multiple platforms cover the same topic in the same week, consolidate into one asset task and note the reuse relationship in the plan's "Asset Requirement" column:
- 1:1 image → Shared across Instagram Single Image / Facebook Feed Post / LinkedIn Image Post
- 9:16 video → Cross-post directly to Instagram Reels + Facebook Reels without regenerating

---

## Phase 2 — Asset Checklist

Split all entries' asset requirements into two categories:

- **AI Auto-generated**: Proceed directly to Phase 3
- **User-provided**: List out what is needed for each entry (how many seconds of video / product photo / scene photo), then proceed to Phase 3 once assets are received

Present the plan and checklist in a conversational tone, **and wait for explicit admin confirmation before proceeding**. Unless the admin has previously stated "just generate directly each time, no confirmation needed," do not skip this step and jump to Phase 3.

---

## Phase 3 — Asset Creation

Create all generatable content in parallel, routing by content type. Entries marked "reuse [platform] asset" skip generation and directly reference the already-generated file path:

| Content Type | Route |
|-------------|-------|
| Single Image Poster | `poster-design` skill |
| Carousel Poster | First read `/mnt/skills/social-media-post-content-creation/features/carousel.md` to plan the narrative structure, then use `poster-design` skill to design each slide |
| Pure Image / Carousel Images (no text overlay) | `/mnt/skills/social-media-post-content-creation/features/generate-image.md` |
| Video | `/mnt/skills/social-media-post-content-creation/features/generate-video.md` |

---

## Phase 4 — Post Assembly

After each asset is generated, write the accompanying:

- **Caption**: Supplement information not conveyed by the asset (backstory / usage experience / why this choice), ending with a call to action
- **Hashtags**: Per platform requirements (Instagram 10-15 / Facebook & LinkedIn 3-5 / Twitter 1-2), covering broad tags + niche tags + geo / brand tags

---

## Phase 5 — User Review

Once all content is generated, call `show_post_preview` to present all posts at once:

```
show_post_preview({
  slides: [{ path: "/mnt/session/outputs/{filename}", label: "Cover" }],
  caption: "Full copy text",
  hashtags: ["tag1", "tag2"]
})
```

- Single image: one item in slides
- Carousel: slides passed in sequential order
- Text-only post: slides is an empty array

After the user confirms everything, proceed to Phase 6. If there are revision notes on a specific post, redo that post individually and re-present.

---

## Phase 6 — Archiving

After each post is confirmed, write to `/workspace/drafts/`:

Filename: `{YYYY-MM-DD}-{platform}-{type}-{slug}.md`

Each draft includes:

| Field | Description |
|-------|-------------|
| Platform | `instagram` / `facebook` / `linkedin` / `twitter` |
| Content Type | Carousel / Single Image Poster / Reels / Story (Instagram only) |
| Status | `pending publish` |
| Planned Publish Date | YYYY-MM-DD |
| Media File Path | Generated image / video path (can be empty for text-only posts) |
| Caption | Full copy text |
| Hashtags | Tag list |

Once drafts are saved, the daily 09:00 `[cron] Content Publish` job automatically scans and publishes by date.
