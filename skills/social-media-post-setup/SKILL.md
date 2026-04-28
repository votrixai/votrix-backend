---
name: social-media-post-setup
description: "Social media marketing assistant initialization and configuration. Triggered when admin mentions setup, configuration, connecting platforms, or updating business information. Also proactively triggered on admin's first use when configuration has not been completed."
---

# Setup — Initialization & Configuration

## Startup Check

Read `/workspace/marketing-context.md`:

- **Does not exist** → Read the template `/workspace/skills/social-media-post-setup/templates/marketing-context.md` and run through the complete flow from scratch
- **Exists but has empty fields** → Only fill in the missing parts
- **Admin specifies a particular item** (e.g., "help me connect Instagram") → Jump directly to the corresponding phase

---

## Phase 1 — Brand Information

Ask admin one thing: "What is your store name or website?"

Once received, use `web_search` / `web_fetch` to compile the following:
- Industry, region, description, main products / services, target audience
- Brand tone (inferred from the website copy)
- Content mood / Mood (inferred from the website's overall visual style, e.g., premium quality, warm and friendly, professional and serious, lively and fun, etc.; leave blank if unable to infer — **do not default to "fresh and bright"**)
- Brand composition style (inferred from the website's visual design: layout, element composition, whitespace ratio, image-text relationship, overall visual atmosphere, etc.)
- Logo URL (the highest resolution version found in the website's header / footer / favicon)
- Timezone (inferred from the website's address, contact page, or About page, format `Asia/Shanghai`; list as pending confirmation if unable to infer)

Present everything to admin for confirmation at once; only ask individually about fields that could not be found (timezone must be asked if it cannot be inferred).

---

## Phase 2 — Brand Assets

Directly use the URL written in Phase 1 under `Brand Profile.Logo URL` to download the Logo — no need to search again. Also scrape the following from the website:
- Promotional images / reference images (website product pages, gallery pages)

Download and save anything that can be scraped; for anything that cannot be found, ask admin if they have materials to provide (URL or upload). Mascot / IP character should be asked about as needed; do not ask for industries where it is clearly not applicable.

**After downloading the Logo**: Observe the Logo's composition characteristics (shape, arrangement, style) and supplement or correct `Brand Profile.Brand Composition Style`.

Save assets to `/workspace/assets/` and create the index file `/workspace/assets/asset-registry.md` (if it does not exist). Each record format:
```
path — note — source: <source URL>
```

---

## Phase 3 — Platform Connections

Ask admin which platforms they want to connect (Facebook / Instagram / Twitter / LinkedIn, multiple selections allowed).

Handle each platform independently, referencing `/workspace/skills/social-media-post-setup/references/platform-connections.md`.

After a successful connection, pull recent posts from that account and supplement or correct the brand visual information in `marketing-context.md`: image style, composition approach, content tone, content mood / Mood. **The actual style from historical posts takes precedence**, overriding the Mood inferred from the website in Phase 1 (website inference serves only as an initial reference).

Write connection status to `## Connected Platforms` in real time — mark successful connections as `Enabled: true`, and skipped or failed ones as `Enabled: false`.

---

## Phase 4 — Operations Plan

Based on industry + connected platforms, generate content direction and publishing cadence:

**Content Direction Allocation**: Read the 15 content types from `/workspace/skills/social-media-post-setup/references/content-strategy.md`, combine with the business's industry, brand style, target audience, and connected platforms, then independently select 3–5 most suitable types and assign publishing ratios (totaling 100%). Consider both industry fit and each platform's content characteristics (e.g., Instagram is suited for visual and humorous content to grow followers, LinkedIn is suited for educational and opinion-based content).

**Publishing Cadence**:
- Food & beverage / retail / lifestyle: 3–4 posts per platform per week
- Local services: 2–3 posts per platform per week
- B2B / professional services: 2–3 posts per week on LinkedIn / Twitter
- When both Facebook and Instagram are connected: Facebook mirrors IG in sync, no separate content creation

**Workflows (fixed)**:

| Task | Default Time |
|------|---------|
| Content Co-creation | Every Monday 09:00 |
| Content Publishing | Every day 09:00 |
| Comment Patrol | Every 6 hours |
| Data Report | Every Friday 18:00 |

Present the plan to admin in a conversational tone, asking only one question: "What day and time would you like to schedule content co-creation? (Default: Monday morning at 9 AM)"

After admin confirms, write the content direction allocation, publishing cadence, and workflow configuration to the corresponding fields in `marketing-context.md` all at once, then call `cron_create` in sequence to register the workflow tasks. All times are based on the timezone recorded in `Brand Profile.Timezone`. When admin explicitly does not need a particular item, skip the corresponding cron and write `Enabled: false`.

---

## Subsequent Updates

When admin wants to modify the configuration, read the current file and only handle the parts that need changing. For workflow time changes, first `cron_delete` the old task then `cron_create` the new task.
