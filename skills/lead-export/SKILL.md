---
name: lead-export
description: "Final validation, quality check, and campaign summary. Triggered after lead-enrichment, or when the user says 'export', 'finalize', 'summary', 'wrap up', 'campaign report'. Also usable mid-campaign to check current progress."
integrations:
  - googlesheets
---

# Lead Export

## Startup Check

Read `/workspace/campaign-context.md`:

1. Confirm lead-enrichment is complete — if not, tell the user which steps remain
2. Read the Google Sheet ID and confirm access

Call `GOOGLESHEETS_BATCH_GET` to read both the **Leads** and **Enrichment** tabs from the Google Sheet. Refer to `/mnt/skills/lead-export/reference/tools.md` for all tool slugs and parameters.

---

## Phase 1 — Final Validation

Run validation checks across all leads. Refer to `/mnt/skills/lead-export/reference/validation_rules.md` for detailed rules and severity levels:

| Check | Rule | On Failure |
|-------|------|------------|
| Required fields | Every lead must have: first name, last name, email, title, company name | Remove lead |
| Email format | Must contain @ with a valid domain | Remove lead |
| Duplicate emails | Flag duplicates, keep the higher-scored lead | Remove lower-scored duplicate |
| Enrichment completeness | A and B tier leads should have enrichment data | Flag for review |

Build a validation summary table:

```
Validation Results:
- Passed:              {N} leads
- Removed (incomplete): {N}
- Removed (bad email):  {N}
- Removed (duplicate):  {N}
- Flagged (no enrichment): {N}
```

Call `GOOGLESHEETS_VALUES_UPDATE` to remove invalid leads from the Leads tab. Call `GOOGLESHEETS_ADD_SHEET` to create a **Removed** tab, then call `GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND` to log removed leads with rejection reasons.

---

## Phase 2 — Campaign Summary

Call `GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND` to write a summary to the **Summary** tab in the Google Sheet:

```
CAMPAIGN: {campaign-name}
Date: {YYYY-MM-DD}
Business: {company-name}
Outreach Goal: {goal}

LEAD VOLUME
- Total pulled from Apollo: {N}
- Discarded (sanitization): {N}
- Discarded (online validation): {N}
- Removed (final validation): {N}
- Final qualified leads: {N}

QUALITY DISTRIBUTION
- A-tier: {N} leads ({%})
- B-tier: {N} leads ({%})
- C-tier: {N} leads ({%})

TOP COMPANIES
- {company 1} ({N} leads)
- {company 2} ({N} leads)
- {company 3} ({N} leads)

TOP TITLES
- {title 1} ({N} leads)
- {title 2} ({N} leads)
- {title 3} ({N} leads)

API USAGE
- Apollo: {N} credits
- Composio Search: {N} searches
- Firecrawl: {N} scrapes
```

Update `/workspace/campaign-context.md` → mark campaign as complete.

---

## Phase 3 — Present Results

Show the user:

1. The validation summary (how many leads passed/failed each check)
2. The campaign summary (volumes, tier distribution, top companies and titles)
3. A direct link to the Google Sheet
4. The top 3 highest-scored leads as a preview

Then ask if the user wants to:
- Review any specific leads or companies
- Remove any leads before considering the campaign final
- Re-run enrichment for specific leads
- Start planning outreach

---

## Reference Files

- `/mnt/skills/lead-export/reference/validation_rules.md` — Validation rules for final quality checks
- `/mnt/skills/lead-export/reference/campaign_intel.schema.json` — Campaign intelligence output schema

---

## Error Handling

| Error | Action |
|-------|--------|
| Google Sheet not accessible | Call `COMPOSIO_MANAGE_CONNECTIONS(toolkits=["googlesheets"])` to reconnect |
| No leads found in the sheet | Tell user to run lead-prospecting first |
| All leads fail validation | Warn user, suggest re-running prospecting with adjusted ICP |
