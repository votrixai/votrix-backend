---
name: lead-prospecting
description: "Search Apollo for leads matching the ICP, sanitize and validate results, and write qualified leads to Google Sheets. Triggered after ICP is defined, or when the user says 'find leads', 'search Apollo', 'prospect', 'get leads', 'run Apollo'. Do NOT use for enrichment or scoring."
integrations:
  - apollo
  - composio_search
  - googlesheets
---

# Lead Prospecting

## Startup Check

Read `/workspace/campaign-context.md`:

1. Confirm `## ICP` is filled — if not, tell the user to run icp-builder first
2. Confirm `## Google Sheet` has a valid Sheet ID — if not, tell the user to run business-context setup first
3. Call `COMPOSIO_MANAGE_CONNECTIONS(toolkits=["apollo"])` — if not connected, show the redirect URL

---

## Phase 1 — Calibration Pull

Translate the ICP criteria into `APOLLO_PEOPLE_SEARCH` parameters. Refer to `/mnt/skills/lead-prospecting/reference/apollo_api_reference.md` for parameter formats and `/mnt/skills/lead-prospecting/reference/tools.md` for all tool slugs.

| ICP Field | Apollo Parameter |
|-----------|-----------------|
| Personas → title patterns | Person title search |
| Personas → seniority | Seniority filter |
| Industries | Industry filter |
| Company Size | Employee count range |
| Geography | Location filter |
| Technologies | Technology filter |
| Exclusions | Exclusion filters |

Call `APOLLO_PEOPLE_SEARCH` with a small calibration pull (10–15 leads) to validate targeting before spending more credits.

---

## Phase 2 — Sanitize Apollo Response

Apollo responses can be malformatted or have censored/missing data. For each lead returned:

**Name resolution:**
- If first_name or last_name is partially censored (e.g. "J***", "S.", or clearly truncated), attempt to find the full name:
  - Call `COMPOSIO_SEARCH_TAVILY` with the person's company name, title, and any available LinkedIn URL
  - If the full name is found, update the record
  - If the full name cannot be determined, **discard the lead**

**Required field check** — each lead must have all of these to pass:

| Field | Required |
|-------|----------|
| First name (full) | Yes |
| Last name (full) | Yes |
| Job title | Yes |
| Company name | Yes |
| Email address | Yes |

**Data quality check** — discard leads with:
- Clearly fake or placeholder data
- Company name that is garbled or unrecognizable
- Title that does not match any ICP persona

Keep a running count of discarded leads and reasons for the final report.

---

## Phase 3 — Calibration Review

Present 5 diverse leads from the sanitized calibration set. Select for diversity across companies, title levels, and industries. Use this card format:

```
Lead 1/5
─────────────────────────
Name:     Jane Smith
Title:    VP of Marketing
Company:  Acme Corp (SaaS, 150 employees)
Location: San Francisco, CA
Email:    jane@acme.com (verified)
LinkedIn: linkedin.com/in/janesmith
─────────────────────────
```

For each lead, ask the user:
- **Fit:** Great fit / Okay fit / Bad fit
- **Why:** (optional)

Then ask overall:
- Are these the right kinds of companies?
- Are the titles and seniority levels correct?
- Any adjustments to make?

**If the user is not satisfied:** adjust the search parameters based on feedback and re-run Phase 1. Loop until the user approves.

**Do not proceed to the bulk pull without explicit user approval.**

---

## Phase 4 — Bulk Prospecting Loop

Once calibration is approved, begin the main prospecting loop.

**Apollo free plan limit:** Apollo's free plan caps results per search (typically around 25). If the user's lead volume target is large, you will need multiple searches with varied parameters (rotating persona titles, geographies, or industry subsets). If the target is unreasonably large, proactively inform the user:

> "Apollo's free plan limits each search to about 25 results. For {N} leads, I'll need to run multiple search rounds. Would you like to proceed, or would you prefer to lower the target to something more manageable?"

**The prospecting loop:**

```
remaining = lead_volume_target
qualified_leads = []

while remaining > 0:
    1. Call `APOLLO_PEOPLE_SEARCH` for a batch (up to 25 per search)
    2. Sanitize the batch (Phase 2 rules)
    3. Validate the batch (Phase 5 rules)
    4. Add validated leads to qualified_leads
    5. remaining = lead_volume_target - len(qualified_leads)
    6. Deduplicate across batches by email and lead ID
    7. If no new valid leads were found in this batch,
       adjust search parameters or inform the user
```

If Apollo is exhausted (no more results with any parameter variation), inform the user of the shortfall and present what was found.

---

## Phase 5 — Online Validation

For each lead that passes sanitization, perform a quick online verification:

1. **Search for the person + company** using `COMPOSIO_SEARCH_TAVILY` to check:
   - The person currently works at the stated company
   - The company is real and active
   - The person's role matches what Apollo reported

2. **Discard a lead with reason** if you find:
   - The person has left the company
   - The company has shut down or been acquired
   - The person's actual role is significantly different from Apollo's data
   - Any other clear sign the lead is invalid or inappropriate for outreach

3. **Do not count discarded leads toward the target** — the loop in Phase 4 continues pulling until enough valid leads are gathered.

4. Log each discard with the reason for the final report.

---

## Phase 6 — Write to Google Sheet

Once the target number of qualified leads is reached (or Apollo is exhausted):

1. Read the Google Sheet ID from `/workspace/campaign-context.md`
2. Call `GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND` to write all qualified leads to the **Leads** tab (schema: `/mnt/skills/lead-prospecting/reference/lead_record.schema.json`):

| Column | Source |
|--------|--------|
| First Name | Apollo (sanitized) |
| Last Name | Apollo (sanitized) |
| Email | Apollo |
| Email Status | Apollo |
| Title | Apollo |
| Company | Apollo |
| Industry | Apollo |
| Company Size | Apollo |
| Location | Apollo |
| LinkedIn URL | Apollo |
| Source | "apollo" |
| Pulled At | Timestamp |
| Validation Status | "verified" or "unverified" |
| Validation Notes | Online check findings |

3. Update `/workspace/campaign-context.md`:
   - `## Pipeline Status` → mark lead-prospecting complete
   - Record totals: leads pulled, discarded (sanitization vs. validation), qualified

4. Report to the user:

```
Prospecting complete:
- Searched: {N} total leads from Apollo
- Discarded (sanitization): {N} — {breakdown of reasons}
- Discarded (validation): {N} — {breakdown of reasons}
- Qualified: {N} leads written to Google Sheet
- Apollo credits used: {N}
```

Hand off to `lead-enrichment`.

---

## Reference Files

- `/mnt/skills/lead-prospecting/reference/apollo_api_reference.md` — Apollo API endpoints, parameters, response structure, rate limits
- `/mnt/skills/lead-prospecting/reference/lead_record.schema.json` — Schema for lead records

---

## Error Handling

| Error | Action |
|-------|--------|
| Apollo not connected | Call `COMPOSIO_MANAGE_CONNECTIONS(toolkits=["apollo"])` to guide user |
| Apollo returns empty results | Suggest broadening ICP criteria, offer to adjust |
| Google Sheet not accessible | Call `COMPOSIO_MANAGE_CONNECTIONS(toolkits=["googlesheets"])` to reconnect |
| All leads in a batch fail validation | Warn user, suggest ICP adjustments |
| Apollo rate limit hit | Inform user of the delay, wait and retry |
