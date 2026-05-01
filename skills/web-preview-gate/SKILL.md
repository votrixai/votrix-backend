---
name: web-preview-gate
description: "User reviews the live preview site and approves before domain setup. Triggered after Vercel deployment is ready. Also triggered when the user says 'preview', 'review site', 'check deployment'."
integrations: []
---

# Web Preview Gate

This is a **blocking checkpoint** — the pipeline must never proceed to domain setup without explicit user approval.

---

## Startup Check

Read `/workspace/deployment.json`:

1. Confirm `vercel-deployer` phase is complete — if not, tell the user to wait for deployment to finish
2. Extract the `preview_url` from the deployment record

---

## Phase 1 — Present the Live Preview

Show the user the live preview URL clearly:

```
Your site preview is ready:
{preview_url}

Please open this link and review the following:
- Design and layout
- Content accuracy
- Feature functionality
- Overall look and feel

When you are done, let me know your verdict:
  1. Approved — ready for domain setup
  2. Needs changes — I will collect your feedback
  3. Start over — discard everything and begin fresh
```

---

## Phase 2 — Collect Verdict

Wait for the user to respond with one of three verdicts. Do not assume or suggest a verdict. The user must explicitly state their choice.

### Verdict: `approved`

1. Save `/workspace/preview_feedback.json` (schema: `/mnt/skills/web-preview-gate/reference/preview_feedback.schema.json`):
   - `verdict`: `"approved"`
   - `approved_for_domain_setup`: `true`
   - `revision_count`: increment from previous value (or `1` if first review)
   - `reviewed_at`: ISO 8601 timestamp
   - `preview_url`: the URL that was reviewed
2. Hand off to `web-domain-manager`

### Verdict: `needs_changes`

1. Collect specific feedback from the user across these categories:

   | Category | Ask |
   |----------|-----|
   | Design | Layout, colors, fonts, spacing |
   | Content | Text, images, copy changes |
   | Features | Functionality, interactions, missing elements |
   | Notes | Any other comments |

2. Save `/workspace/preview_feedback.json`:
   - `verdict`: `"needs_changes"`
   - `approved_for_domain_setup`: `false`
   - `revision_count`: increment from previous value
   - `feedback.design`: user's design feedback
   - `feedback.content`: user's content feedback
   - `feedback.features`: user's feature feedback
   - `feedback.notes`: user's additional notes
   - `reviewed_at`: ISO 8601 timestamp
   - `preview_url`: the URL that was reviewed

3. Hand back to `web-site-customizer` for revisions
4. After revisions and re-deployment, return here for another review cycle

### Verdict: `start_over`

1. Clear all workspace state files
2. Hand back to `web-project-intake` to begin fresh

---

## Critical Rules

- **NEVER** proceed to domain setup without an explicit `"approved"` verdict from the user
- **NEVER** interpret ambiguous responses as approval — ask for clarification
- If the user asks to see the preview again, re-display the URL
- Track revision count across review cycles

---

## Error Handling

| Error | Action |
|-------|--------|
| `deployment.json` missing | Tell the user deployment has not completed yet, hand back to `web-vercel-deployer` |
| `deployment.json` has no `preview_url` | Tell the user the deployment may have failed, hand back to `web-vercel-deployer` |
| User response is ambiguous | Ask the user to explicitly choose: approved, needs changes, or start over |
| Preview URL returns error | Suggest waiting a few minutes for deployment to propagate, offer to re-check |

---

## Handoff

On approval, hand off to **web-domain-manager** to connect the customer's domain.
