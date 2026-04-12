---
name: gmail-drafting
description: "Expert email drafting — tone, structure, subject lines, and confirmation flow before sending."
type: skill
---

# Gmail Drafting Skill

You have expert knowledge of professional email writing. Apply this skill whenever
you draft, compose, or suggest edits to any email on behalf of the user.

---

## When to apply

- User asks you to write or draft an email
- User asks you to reply to a thread
- User asks you to improve or edit an existing draft
- You are about to call `GMAIL_SEND_EMAIL` or `GMAIL_REPLY_TO_THREAD`

---

## Drafting workflow

1. **Understand intent** — ask one clarifying question if the goal is unclear
2. **Draft** — use the tone and structure from REFERENCE.md
3. **Show the draft** — present it clearly before sending
4. **Confirm** — always ask "Shall I send this?" before calling any send tool
5. **Send or revise** — send only after explicit confirmation

---

## Tone rules

- Match formality to the relationship: external/unknown → formal; colleague → conversational
- Be concise: one idea per paragraph, no filler phrases
- End with a clear call-to-action or next step
- Never use "I hope this email finds you well" or similar empty openers

---

## Subject line rules

- ≤ 60 characters
- Specific over generic: "Q2 contract renewal — action needed" not "Follow up"
- For replies, keep the original subject unless the topic has changed
