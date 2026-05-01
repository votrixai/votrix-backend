---
name: business-context
description: "Initial setup for a B2B lead generation campaign. Triggered when the user wants to start a new campaign, says 'setup', 'new campaign', 'get started', or when no campaign-context.md exists yet. Also triggered when the user wants to update business info or reconnect Google Sheets."
integrations:
  - composio_search
  - firecrawl
  - googlesheets
---

# Business Context Setup

## Startup Check

Read `/workspace/campaign-context.md`:

- **Does not exist** → run the full flow from Phase 1
- **Exists but has empty fields** → only fill in the missing parts
- **User specifies a section** (e.g. "reconnect Google Sheets") → jump directly to that phase

---

## Phase 1 — Business Information

Ask the user one question: "What is your business name?"

Once you have the business name, ask if they have a business website they can share.

Refer to `/mnt/skills/business-context/reference/tools.md` for tool slugs and parameters.

**If website URL is provided:**

1. Immediately call `FIRECRAWL_SCRAPE` with the website URL to extract core business information
2. From the scraped content, extract:
   - Industry and market segment
   - Products / services offered
   - Value proposition
   - Target audience (if detectable)
   - Key differentiators
3. Regardless of whether scraping succeeded, also call `COMPOSIO_SEARCH_TAVILY` with the business name to gather:
   - Additional product details
   - Recent news or announcements
   - Customer reviews or testimonials
   - Competitor landscape
4. Present all gathered information to the user for confirmation — only ask about fields you could not find

**If no website URL is provided:**

1. Call `COMPOSIO_SEARCH_TAVILY` to search for the business name
2. If useful results are found, extract relevant business info and present for confirmation
3. **Only if nothing useful is found online**, apologize and ask the user to provide:
   - Product / service description (2–3 sentences)
   - Value proposition
   - Target customer description
   - Pain points solved (3–5 items)
   - Main competitors (optional)

**Outreach goal** — ask which goal fits best:

| Goal | Description |
|------|-------------|
| Demo booking | Schedule a product demo |
| Free trial | Get prospects to try the product |
| Consultation | Book a discovery call |
| Partnership | Explore partnership opportunities |
| Other | Custom goal (user specifies) |

---

## Phase 2 — Campaign Naming

Ask the user for a campaign name (short slug, e.g. `q2-saas-push`).

If the user has no preference, generate one from the business name and current context (e.g. `acme-outbound-2024`).

---

## Phase 3 — Google Sheets Connection

Before proceeding, ask the user to connect their Google Sheets integration:

1. Call `COMPOSIO_MANAGE_CONNECTIONS(toolkits=["googlesheets"])` to check if Google Sheets is connected
2. If not connected, show the user the redirect URL to authenticate
3. **Do not continue until Google Sheets is successfully connected**

Once connected, ask the user if they have a preferred name for the campaign spreadsheet. If not, use: `{campaign-name}-{unix-epoch}` (e.g. `q2-saas-push-1706745600`).

Call `GOOGLESHEETS_CREATE_GOOGLE_SHEET1(title="{sheet-name}")` to create the spreadsheet, then call `GOOGLESHEETS_ADD_SHEET` for each tab:

| Tab | Purpose |
|-----|---------|
| Leads | Main lead data (filled by lead-prospecting) |
| Enrichment | Scoring and intel data (filled by lead-enrichment) |
| Summary | Campaign summary (filled by lead-export) |

Record the spreadsheet ID and URL.

---

## Phase 4 — Save & Handoff

Write all gathered information to `/workspace/campaign-context.md`:

```
## Business Profile
- **Company:** {name}
- **Industry:** {industry}
- **Products/Services:** {description}
- **Value Proposition:** {value prop}
- **Target Customer:** {target}
- **Pain Points:** {bullet list}
- **Competitors:** {list}
- **Outreach Goal:** {goal}
- **Source:** {website URL / online research / user-provided}

## Campaign
- **Name:** {campaign-name}
- **Started:** {YYYY-MM-DD}

## Google Sheet
- **Sheet Name:** {name}
- **Sheet ID:** {id}
- **Sheet URL:** {url}

## ICP
(to be filled by icp-builder)

## Market Intelligence
(to be filled by lead-enrichment)

## Pipeline Status
- **Current Step:** business-context complete
- **Credits Used:** Apollo: 0 | Composio Search: {n} | Firecrawl: {n}
```

Tell the user the setup is complete and hand off to the `icp-builder` skill.

---

## Subsequent Updates

When the user wants to update business info, read the current file, only modify the requested section. If Google Sheets needs reconnection, jump to Phase 3.
