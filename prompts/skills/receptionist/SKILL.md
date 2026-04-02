---
name: receptionist
description: "View receptionist config and query call history. Admin only."
type: skill
audience: admin
requires_config: skills/receptionist/receptionist.json
---

# receptionist

> **Admin only.** View receptionist config, call records, transcripts, recordings, and summaries.
> To modify any config, read `skills/receptionist/reference/receptionist-setup.md`.

---

## Pre-flight

Read **registry.json**:

- `modules.receptionist` is not `true` → tell the admin the receptionist isn't configured yet and suggest running **skills/receptionist/reference/receptionist-setup.md**. Stop.

Once confirmed, read `skills/receptionist/receptionist.json` and get `agentId` from it. All commands below require it.

---

## Commands

> All commands below are executed via `votrix_run("command [flags]")`.

### View current config

**Triggers:** "what's my current setup", "show me the receptionist config", "what greeting am I using"

Behavior config (greeting, policy, transfer rules, etc.) is already in context — display it directly. No command needed.

To sync the latest voice and phone config from the backend (e.g. admin suspects something changed):

```
receptionist.get_agent

-> { agentId, agentName, mainLanguageCode, languageCodes,
     voice, fallbackTransferNumber, receptionistPhoneNumber }
```

To modify any config, read **skills/receptionist/reference/receptionist-setup.md**.

---

### List call records

**Triggers:** "show me recent calls", "any calls today", "did this number call", "show me all marketing calls"

```
receptionist.list_sessions [--agent-id <agentId>] [--phone <number>] [--label <tag>] [--page-offset <n>] [--page-size <n>]

-> { sessions: [{ sessionId, createdAt, endedAt, custId, labels: [string], summary: { content, labels } | null }] }
```

| Flag | Default | Notes |
|---|---|---|
| `--agent-id` | from config | read automatically from loaded config |
| `--phone` | — | filter by caller number |
| `--label` | — | filter by tag |
| `--page-offset` | 0 | newest-first |
| `--page-size` | 10 | |

Display as a list: index, time, caller (`custId`), duration, labels, summary.

---

### View a single call

**Triggers:** "show me the full transcript", "I want to see the complete conversation", "give me the full dialogue"

```
receptionist.get_session <sessionId>

-> { session: { sessionId, events: [{ eventType, eventTitle, eventBody, occurredAt }] } }
```

Extract `USER_MESSAGE` and `AI_AGENT_MESSAGE` from events and display as a conversation in chronological order. Do not show other event types.

---

### Get recording

**Triggers:** "play the recording", "let me hear that call", "do you have the audio"

```
receptionist.get_session_audio <sessionId>

-> { audioUrl }
```

Return `audioUrl` to admin. If empty, tell admin no recording is available for this call.

---

### Call summary

**Triggers:** "what happened on that call", "what was that call about", "anything interesting today" — default when admin wants to know about a call. Always try summary first; only pull the full transcript if admin explicitly asks.

```
receptionist.get_session_summary <sessionId>

-> { summary: { content, labels: [string] } }
```

`content` is the summary text; `labels` contains the tag picked from `summary.tagChoices`. If not yet available, tell admin it's still processing and to check back shortly.

---

### Test the receptionist

**Triggers:** "I want to test it", "how do I try it", "can I preview", "show me what it sounds like"

Tell the admin to call `phone.receptionistPhoneNumber` directly — that is the live number. No separate preview step is needed.

---

## Rules

- `agentId` is always taken from the loaded config — never ask the admin for it.
- All commands are read-only — nothing modifies config.
- Only show fields meaningful to the admin; do not expose raw proto fields.
- If a sessionId doesn't exist, tell the admin and suggest using List call records to find it.
- If the admin asks to change any config, read **skills/receptionist/reference/receptionist-setup.md**.