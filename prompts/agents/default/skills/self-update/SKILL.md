---
name: self-update
description: "Keep system files current as the business evolves. Update USER.md and registry when info changes."
type: skill
audience: admin
---

# self-update

Maintain AI system files so that `USER.md` and `registry.json` always reflect the current state of the business.

---

## Triggers

Recognize these situations **proactively** — no explicit request needed:

- Admin mentions a business change (address, hours, services, pricing, staff, etc.)
- Admin corrects something the AI said about the business
- Admin explicitly asks to update the profile

---

## Updating USER.md

Use the `write` tool directly.

**Rules:**
- Change only the fields mentioned — do not rewrite the whole file
- Preserve the existing format and section structure
- Confirm with the admin before writing: state which field and what the new value will be
- After writing, confirm it's done

**Example:**

> Admin: "We moved to 789 Oak Ave"
>
> AI: "Got it — I'll update Address to '789 Oak Ave'. Sound right?"
>
> Admin: "Yes"
>
> AI: [write USER.md, changing only the Address line] → "Done."

---

## Updating registry

Use `votrix_run`. For structured operational state only.

### Set timezone

When the business timezone changes, or after confirming timezone during bootstrap:

```
registry.set_timezone <IANA_timezone>

-> "Timezone set to '<tz>'."
```

Example: `registry.set_timezone America/New_York`

Must be a valid IANA name (e.g. `America/Los_Angeles`, `Asia/Shanghai`).

**When timezone changes, update both** — USER.md `Timezone` field and registry.

### Set a custom field

For operational state that doesn't belong in USER.md — e.g. last review date, config version:

```
registry.set_field <key> <value>

-> "Registry field '<key>' set to '<value>'."
```

Example: `registry.set_field last_profile_review 2026-03-25`

Reserved keys (`bootstrap_complete`, `timezone`, `modules`, `connections`, `_meta`) are rejected — use their dedicated commands instead.

---

## Periodic review

When the admin mentions the profile hasn't been updated in a while, or it's been more than ~3 months since bootstrap:

1. Read `USER.md` and go through each section
2. Ask: "Does this still look accurate? Anything that needs updating?"
3. Apply changes as the admin confirms them
4. Run `registry.set_field last_profile_review <today>` to record the review date

---

## Rules

- Confirm before writing — never silently edit files
- Only change what the admin explicitly mentioned; don't infer beyond that
- When timezone changes, update both USER.md and registry
