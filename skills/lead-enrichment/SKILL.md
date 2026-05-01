---
name: lead-enrichment
description: "Research the market, score leads, and generate outreach intel. Updates the Google Sheet with enrichment data. Triggered after lead-prospecting is complete, or when the user says 'enrich leads', 'score leads', 'research leads', 'add intel', 'analyze leads'. Do NOT use for finding new leads — use lead-prospecting for that."
integrations:
  - composio_search
  - firecrawl
  - googlesheets
  - apollo
---

# Lead Enrichment

## Startup Check

Read `/workspace/campaign-context.md`:

1. Confirm lead-prospecting is marked complete — if not, tell the user to run it first
2. Confirm `## Google Sheet` has a valid Sheet ID and the sheet is accessible
3. Read `## Business Profile` and `## ICP` for scoring context

Call `GOOGLESHEETS_BATCH_GET` to read the **Leads** tab from the Google Sheet. Refer to `/mnt/skills/lead-enrichment/reference/tools.md` for all tool slugs and parameters.

---

## Phase 1 — Market Research

Before scoring individual leads, build market context to inform scoring and outreach. Use query templates from `/mnt/skills/lead-enrichment/reference/query_templates.md`:

1. **Industry trends** — call `COMPOSIO_SEARCH_TAVILY` for 2–3 current trends in the target industries
2. **Competitor intelligence** — for each known competitor (from Business Profile), call `COMPOSIO_SEARCH_TAVILY` for:
   - Positioning and recent news (1–2 searches per competitor)
   - Weaknesses or gaps to leverage in outreach
3. **Buying triggers** — call `COMPOSIO_SEARCH_TAVILY` for 2–3 signals that indicate buying readiness in the target market
4. **Deep content** — for high-value search results, call `FIRECRAWL_SCRAPE` to extract full content from competitor pages, industry reports, or relevant articles

Synthesize findings into actionable intelligence:
- Top 3–5 industry trends
- Key competitor weaknesses to leverage
- Active buying triggers to reference in outreach

Save to `/workspace/campaign-context.md` under `## Market Intelligence`:

```
## Market Intelligence
- **Last Updated:** {YYYY-MM-DD}
- **Key Trends:**
  - {trend 1}
  - {trend 2}
  - ...
- **Competitor Insights:**
  - {competitor}: {positioning, weakness, recent moves}
  - ...
- **Buying Triggers:**
  - {trigger 1}
  - {trigger 2}
  - ...
- **Sources:** {list of URLs consulted}
```

---

## Phase 2 — Lead Scoring

Score each lead on three dimensions (0–100 each). Read the appropriate rubric before scoring: `/mnt/skills/lead-enrichment/reference/scoring_rubric_smb.md`, `scoring_rubric_mid.md`, or `scoring_rubric_enterprise.md` based on the campaign's target company size.

| Dimension | Weight | What to Evaluate |
|-----------|--------|-----------------|
| Fit | 40% | Title match to ICP persona, company size within range, industry match, technology overlap |
| Intent | 35% | Recent company activity, hiring patterns, tech changes, online presence signals |
| Timing | 25% | Funding events, leadership changes, expansion signals, seasonal factors |

**Overall Score** = (Fit x 0.4) + (Intent x 0.35) + (Timing x 0.25)

**Tier assignment:**

| Tier | Score Range | Action |
|------|------------|--------|
| A | 75–100 | Priority outreach — full deep dive and personalized intel |
| B | 50–74 | Standard outreach — deep dive and standard intel |
| C | 0–49 | Low priority — score recorded, no further enrichment |

---

## Phase 3 — Account Deep Dive (A & B Tier Only)

For each unique company in the A and B tier lead set, research:

| Research Area | Method | What to Extract |
|--------------|--------|-----------------|
| Company news | `APOLLO_SEARCH_NEWS_ARTICLES` + `COMPOSIO_SEARCH_TAVILY` | Recent headlines, funding events, expansion moves |
| Tech stack | `COMPOSIO_SEARCH_TAVILY` + `FIRECRAWL_SCRAPE` | Current technologies, recent changes |
| Hiring signals | `APOLLO_GET_ORGANIZATION_JOB_POSTINGS` + `COMPOSIO_SEARCH_TAVILY` | Open roles in relevant departments, team growth |
| Financial signals | `COMPOSIO_SEARCH_TAVILY` | Funding rounds, revenue milestones, financial health |

**Cost control:** cap at 3–5 `COMPOSIO_SEARCH_TAVILY` searches and 1–2 `FIRECRAWL_SCRAPE` calls per company. Use `APOLLO_GET_ORGANIZATION` to get base org data first. Research each company once — fan results to all leads from that company.

---

## Phase 4 — Outreach Intel Generation

For each A and B tier lead, generate personalized outreach content. Follow the quality guidelines and templates in `/mnt/skills/lead-enrichment/reference/intel_templates.md`:

| Field | Description | Quality Bar |
|-------|-------------|-------------|
| Pain Signal | Specific pain hypothesis tied to their role and industry | Must reference something concrete about their situation |
| Lead Intel | 2–3 sentence insight connecting their situation to the user's solution | Must use account research, not generic |
| Email Subject | Suggested subject line, under 60 characters | No clickbait, no ALL CAPS |
| Email Opening | First 1–2 sentences of a personalized cold email | Must feel hand-written, not templated |

Use the business profile, market intelligence, and account research to make the intel specific and relevant. Generic content is worse than no content — if you lack enough data for a lead, note what is missing rather than fabricating specifics.

---

## Phase 5 — Update Google Sheet

Call `GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND` to write enrichment data to the **Enrichment** tab in the Google Sheet:

| Column | Source |
|--------|--------|
| Email | Key to join with Leads tab |
| Fit Score | Phase 2 |
| Intent Score | Phase 2 |
| Timing Score | Phase 2 |
| Overall Score | Phase 2 |
| Tier | Phase 2 |
| Company News | Phase 3 |
| Tech Stack | Phase 3 |
| Hiring Signals | Phase 3 |
| Financial Signals | Phase 3 |
| Pain Signal | Phase 4 |
| Lead Intel | Phase 4 |
| Email Subject | Phase 4 |
| Email Opening | Phase 4 |

Update `/workspace/campaign-context.md`:
- `## Pipeline Status` → mark lead-enrichment complete
- Record Composio Search and Firecrawl credits used

Report to the user:

```
Enrichment complete:
- A-tier: {N} leads (full enrichment)
- B-tier: {N} leads (full enrichment)
- C-tier: {N} leads (scored only, no enrichment)
- Companies researched: {N}
- Composio Search queries: {N} | Firecrawl scrapes: {N}
```

Hand off to `lead-export`.

---

## Reference Files

- `/mnt/skills/lead-enrichment/reference/query_templates.md` — Search query templates for market research
- `/mnt/skills/lead-enrichment/reference/scoring_rubric_smb.md` — SMB pass/fail scoring rubric
- `/mnt/skills/lead-enrichment/reference/scoring_rubric_mid.md` — Mid-market 3D scoring rubric
- `/mnt/skills/lead-enrichment/reference/scoring_rubric_enterprise.md` — Enterprise 4D scoring rubric
- `/mnt/skills/lead-enrichment/reference/lead_score.schema.json` — Scoring output schema
- `/mnt/skills/lead-enrichment/reference/market_kb.schema.json` — Market knowledge base schema
- `/mnt/skills/lead-enrichment/reference/intel_templates.md` — Outreach intel quality guidelines and templates

---

## Error Handling

| Error | Action |
|-------|--------|
| Google Sheet not accessible | Call `COMPOSIO_MANAGE_CONNECTIONS(toolkits=["googlesheets"])` to reconnect |
| Composio Search / Firecrawl not connected | Call `COMPOSIO_MANAGE_CONNECTIONS` to guide user |
| No A or B tier leads after scoring | Inform user, suggest adjusting ICP or re-running prospecting |
| API rate limit | Inform user, suggest waiting and retrying |
