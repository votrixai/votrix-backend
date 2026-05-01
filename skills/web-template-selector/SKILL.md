---
name: web-template-selector
description: "Select the best Next.js template from the catalog based on project requirements. Triggered after project-intake is complete, or when the user says 'pick template', 'choose template', 'select template', 'change template'."
integrations: []
---

# Web Template Selector

## Startup Check

Read `/workspace/project_brief.json`:

1. Confirm the file exists and contains valid business info, pages, and features -- if not, tell the user to run web-project-intake first
2. Check `/workspace/pipeline_state.json` to verify web-project-intake is in `completed_stages`

Read `/workspace/template_selection.json` if it exists:
- Already has a confirmed selection -- ask the user if they want to re-select or keep the current template
- Has an unconfirmed selection -- resume from Phase 3 (presentation)

---

## Phase 1 -- Load Template Catalog

Load the template catalog from `/mnt/skills/web-template-selector/reference/templates_catalog.json`.

Each template entry contains:
- `template_id` -- unique identifier
- `name` -- display name
- `repo` -- repository name in the `votrix-site-templates` org
- `business_types` -- list of business types this template is designed for
- `pages` -- list of pages included in the template
- `features` -- list of features supported out of the box
- `style` -- visual style keywords (modern, minimal, classic, playful, bold, elegant)
- `framework` -- always "nextjs"
- `description` -- short description of the template

---

## Phase 2 -- Score Templates

Score each template on a 0-100 scale using four weighted criteria:

| Criterion | Weight | How to Score |
|-----------|--------|-------------|
| Business Type Match | 40 pts | 40 if the project's business_type is in the template's business_types list. 20 if the template supports a related type. 0 if no match. |
| Page Coverage | 30 pts | (number of project pages found in template pages / total project pages) x 30 |
| Feature Coverage | 20 pts | (number of project features found in template features / total project features) x 20 |
| Style Match | 10 pts | Compare project font_preference to template style keywords. Exact match = 10. Related match = 5. No match = 0. |

**Style matching rules:**

| Font Preference | Matching Styles |
|----------------|-----------------|
| modern | modern, bold |
| classic | classic, elegant |
| playful | playful, bold |
| minimal | minimal, modern |
| custom | any (5 pts default) |

Sort templates by total score descending.

---

## Phase 3 -- Present Top Templates

Present the top 3 templates to the user in this format:

```
Template 1/3: {name}
Score: {total}/100
------------------------------------
Business Type Match:  {score}/40
Page Coverage:        {score}/30
Feature Coverage:     {score}/20
Style Match:          {score}/10
------------------------------------
Supported Pages:      {list of matching pages}
Missing Pages:        {list of project pages not in template}
Supported Features:   {list of matching features}
Missing Features:     {list of project features not in template}
------------------------------------
Note: {any important caveats -- e.g. "Missing pages can be created during customization"}
```

For missing pages, reassure the user that the web-site-customizer skill can create new pages from scratch. For missing features, note which ones require custom implementation versus simple configuration.

Ask the user to pick a template (1, 2, or 3) or request to see more options.

---

## Phase 4 -- Confirm Selection

Once the user picks a template, present a final confirmation:

- Template name and repo
- What will be customized (brand, content, pages)
- What will need to be built from scratch (missing pages, unsupported features)
- Estimated complexity (simple / moderate / complex based on gap analysis)

Wait for explicit user confirmation before saving.

---

## Phase 5 -- Save and Handoff

Write `/workspace/template_selection.json` (schema: `/mnt/skills/web-template-selector/reference/template_selection.schema.json`):

```json
{
  "template_id": "",
  "template_name": "",
  "template_repo": "",
  "scores": {
    "business_type_match": 0,
    "page_coverage": 0,
    "feature_coverage": 0,
    "style_match": 0,
    "total": 0
  },
  "supported_pages": [],
  "missing_pages": [],
  "supported_features": [],
  "missing_features": [],
  "complexity": "",
  "confirmed": true,
  "confirmed_at": ""
}
```

Update `/workspace/pipeline_state.json`:
- Add `"web-template-selector"` to `completed_stages`
- Set `current_stage` to `"web-template-selector"`
- Update `updated_at` timestamp

Tell the user the template is selected and hand off to `web-site-customizer`.

---

## Error Handling

| Error | Action |
|-------|--------|
| project_brief.json not found | Tell the user to run web-project-intake first |
| Template catalog is empty or unreadable | Report the error and ask the user to contact support |
| No templates score above 20 | Warn the user that no templates are a strong match; present the best available and suggest adjusting project requirements |
| User rejects all 3 templates | Show the next 3 templates if available; if the catalog is exhausted, suggest adjusting project requirements |
| User wants to change project requirements | Tell the user to re-run web-project-intake, then return to template selection |
