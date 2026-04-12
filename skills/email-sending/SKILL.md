---
name: email-sending
description: "Best practices for composing and sending emails via Gmail, including confirmation flow and formatting."
type: skill
---

# Email Sending Skill

You can send emails on behalf of the user using the Gmail integration.
Always follow this workflow — never skip the confirmation step.

## Sending workflow

1. **Understand the request** — clarify recipient, subject, and intent if unclear
2. **Compose the draft** — write the full email (subject + body)
3. **Show the draft** — present it clearly to the user before sending
4. **Confirm** — ask "Shall I send this?" and wait for explicit approval
5. **Send** — only call `GMAIL_SEND_EMAIL` after confirmation

## GMAIL_SEND_EMAIL parameters

| Parameter | Description |
|---|---|
| `recipient_email` | Recipient email address |
| `subject` | Email subject line |
| `body` | Plain text or HTML body |

## Format rules

- Subject: ≤ 60 characters, specific and actionable
- Body: concise — one idea per paragraph, clear call-to-action at the end
- Sign off with the user's name when known

## Including images

When sharing a generated image via email:
- Include the image URL in the body as a clickable link or inline HTML `<img>` tag
- Add a short description of the image above the link
