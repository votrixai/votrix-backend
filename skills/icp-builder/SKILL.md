---
name: icp-builder
description: "Build the Ideal Customer Profile (ICP) that drives lead targeting. Triggered after business-context is complete, or when the user says 'define ICP', 'targeting criteria', 'ideal customer', 'who should we target'. Do NOT use for prospecting or searching leads."
integrations: []
---

# ICP Builder

## Startup Check

Read `/workspace/campaign-context.md`:

1. Confirm `## Business Profile` is filled — if not, tell the user to run business-context setup first
2. Check `## ICP` section:
   - Empty or placeholder → run the full flow
   - Already filled → ask user if they want to revise or start fresh

---

## Phase 1 — Target Definition

Based on the business profile, suggest initial targeting criteria and ask the user to confirm or adjust each:

**Industries** — which industries to target:
- Suggest 3–5 industries based on the business profile with brief reasoning
- User can add or remove

**Company Size** — employee count range:

| Segment | Range | Description |
|---------|-------|-------------|
| Startup | 1–50 | Early-stage companies |
| SMB | 50–200 | Small-to-medium businesses |
| Mid-Market | 200–2,000 | Growing organizations |
| Enterprise | 2,000+ | Large corporations |

Suggest a range based on the business profile. User can adjust.

**Personas** — who to reach within target companies. For each persona:
- Job title patterns (e.g. "VP of Marketing", "Head of Growth")
- Seniority level (C-suite, VP, Director, Manager)
- Department (Marketing, Sales, Engineering, etc.)

Suggest 1–2 personas based on the product and target customer description.

**Geography** — countries and regions to target.

**Technologies** — tech stack filters (optional, only if relevant to the product).

**Exclusions** — companies, domains, or industries to exclude.

---

## Phase 2 — Lead Volume

Ask the user how many qualified leads they want from this campaign.

Provide guidance on typical volumes:

| Volume | Use Case |
|--------|----------|
| 10–25 | Focused, high-touch outreach |
| 25–50 | Standard campaign |
| 50–100 | Broad outreach |
| 100+ | Large-scale prospecting |

**Important:** If the user requests a number that would exceed what Apollo's free plan can realistically deliver, let them know upfront. Apollo's free plan typically returns up to 25 results per search, so large volumes require multiple search rounds. Suggest starting with a manageable target and scaling up.

---

## Phase 3 — Confirm & Save

Present the complete ICP summary to the user in a clear format. Wait for explicit confirmation before saving.

Write the ICP to `/workspace/campaign-context.md` under `## ICP`:

```
## ICP
- **Industries:** {list}
- **Company Size:** {min}–{max} employees
- **Personas:**
  - {title patterns} | {seniority} | {department}
  - ...
- **Geography:** {countries/regions}
- **Technologies:** {list or "any"}
- **Exclusions:** {list or "none"}
- **Lead Volume Target:** {number}
- **Last Updated:** {YYYY-MM-DD}
```

Update `## Pipeline Status` to mark icp-builder complete.

Tell the user the ICP is set and hand off to `lead-prospecting`.
