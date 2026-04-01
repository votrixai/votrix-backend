---
name: receptionist-setup
description: "Create and manage the receptionist. Admin only."
type: setup
audience: admin
produces_config: skills/receptionist/receptionist.json
---

# receptionist-setup

> **Admin only.** Never run during a customer conversation.
> The receptionist handles **inbound** calls only — no outbound.
>
> All `receptionist.*` commands in this document are executed via `votrix_run("receptionist.<subcommand> [flags]")`. `write(...)` and `COMPOSIO_*` tools are called directly.

---

## Data layers

| Layer | Fields | Source of truth | How to update |
|---|---|---|---|
| Voice / phone | `phone.*` | Backend | `receptionist.*` commands; synced to json on pre-flight via `get_agent` |
| AI behavior config | `behavior.*`, `policy` | `receptionist.json` | Confirm in conversation → write json → votrix_run to register |
| Setup status | `modules.receptionist` | `registry.json` | `votrix_run("module.setup_complete receptionist")` |

---

## Pre-flight

Call `receptionist.get_agent` and write the returned fields into `phone.*` in `receptionist.json`. Then route:

```
receptionist.get_agent

-> { agentId, agentName, mainLanguageCode, languageCodes,
     voice, fallbackTransferNumber, receptionistPhoneNumber }
```

| Condition | Action |
|---|---|
| `phone.agentId` is null | Go to「Create Agent」 |
| `phone.receptionistPhoneNumber` is null | Go to「Manage Phone Numbers → Bind」 |
| `phone.fallbackTransferNumber` is null | Ask admin for fallback number → `receptionist.update_agent --fallback-transfer-number <n>` → write to json |
| `behavior.greetingMessage` is null | Go to「Configure Behavior」 |
| `modules.receptionist` is `false` | Tell admin setup is incomplete; suggest re-running Configure Behavior |
| `modules.receptionist` is `true` | Show current config, ask what to do. If `booking` is not configured in Module Status, mention it: "Want callers to be able to book appointments over the phone?" |

---

## Create Agent

> Only when `agentId` is null. Read **BusinessName** from `USER.md`.

### Defaults (do not ask unless admin raises it)

| Setting | Default | If admin asks to change |
|---|---|---|
| Language | `en-US` only | Options: `zh-CN`, `es-ES`. Max 2 total. |
| Voice | `Zara` (en-US), `Xiaoxiao` (zh-CN) | en-US: Arabella, Lily, Ivanna, Zara, Jessa, Chris, Ryan; zh-CN: Xiaoxiao, Xiaochen, Yunxi, Yunfan |

Fallback transfer number: search `USER.md` for a phone number. Found → confirm with admin. Not found → ask. International format (`+<country><number>`).

```
receptionist.create_agent --agent-name <n>
                          --main-language-code <code>
                          --language-code <code> [--language-code <code>]
                          --voice <lang>:<voice> [--voice <lang>:<voice>]
                          --fallback-transfer-number <number>

-> { agentId }
```

- `--language-code` repeatable, max 2, must include `--main-language-code`
- `--voice` one per language, format `<langCode>:<voiceName>` e.g. `en-US:Zara`
- `--fallback-transfer-number` international format e.g. `+16501234567`

Write returned `agentId` to `phone.agentId`, then go to「Manage Phone Numbers → Bind」.

---

## Manage Phone Numbers

> Can be triggered independently or automatically after creating an agent.
>
> Number lifecycle (list, search, buy, release) is managed via **skills/phone/SKILL.md**. Only the bind/unbind operations below are receptionist-specific.

List all numbers in the account with binding status:

```
phone.list

-> { numbers: [{ number, status: "bound" | "unbound", boundTo: string | null }] }
```

Search for available numbers to purchase:

```
phone.search [--area-code <code>]

-> { numbers: [string] }
```

Purchase a number (**incurs a charge — require explicit admin confirmation before executing**):

```
phone.buy --number <number>
```

Bind a number to the agent:

```
receptionist.bind_phone --agent-id <agentId>
                        --number <number>
```

Write bound number to `phone.receptionistPhoneNumber`. If `behavior.greetingMessage` is null, go to「Configure Behavior」.

Unbind a number (number stays in account, requires confirmation):

```
receptionist.unbind_phone --agent-id <agentId>
                          --number <number>
```

Release a number (**permanently deleted, cannot be undone — warn + require explicit confirmation**):

```
phone.release --number <number>
```

Update voice layer config (language, voice, fallback number) — pass only the fields to change:

```
receptionist.update_agent --agent-id <agentId>
                          [--agent-name <n>]
                          [--main-language-code <code>]
                          [--language-code <code> [--language-code <code>]]
                          [--voice <lang>:<voice> [--voice <lang>:<voice>]]
                          [--fallback-transfer-number <number>]
```

- `--language-code` and `--voice` overwrite all values if passed; omitting them leaves backend unchanged
- On success, sync changed fields into `phone.*`

---

## Configure Behavior

> Used for both first-time setup and updates. Do not ask field by field — silently build the full config, present it all at once, and write only after admin confirms. If admin abandons, save nothing.

### Inference rules

**`greetingMessage`** — The first thing the receptionist says when picking up. Infer from BusinessName.
Default: `"Thank you for calling [BusinessName], how can I help you today?"`

**`policy`** — Rules the receptionist must always follow during every call. Merge built-in defaults (below) with any business-specific rules the admin mentions in conversation.
Default: built-in only.

**`transferRules`** — When and where to transfer the call. Each rule has a trigger condition, a label, and a destination number. Matched in order. The fallback number collected in Phase 1 is always the last rule. Check USER.md for any additional contacts to add.
Default: fallback number only.

**`forbiddenPhrases`** — Words or phrases the receptionist must never say under any circumstances.
Default: `[]`

**`summary.tagChoices`** — After every call ends, the system picks one tag from this list and writes it to the call record. Used for filtering and categorizing calls. Admin can add or remove options.
Default: `["appointment", "inquiry", "complaint", "marketing", "wrong_number", "other"]`

**`summary.additionalInstructions`** — Appended to the default summary prompt. Use when the admin wants to extract business-specific information from calls, e.g. "Also note whether the caller mentioned having insurance." Translate the admin's request into a clear instruction.
Default: `null`

### Built-in policy (always active, cannot be removed)

- Stay polite and professional; never argue with the caller.
- If unsure, say so honestly — don't guess.
- For pricing questions: "Exact pricing is available in store."
- No medical, legal, or financial advice.
- If caller is abusive, politely end the call.
- Always offer to transfer to a real person if the caller is unsatisfied.
- If the caller shows sales or marketing intent, politely decline and end the call.
- If the caller does not appear to be a genuine customer (e.g. survey, partnership pitch, robocall), politely decline and end the call.

### Save

After admin confirms, write the complete `receptionist.json` (all fields), then register:

**Required flags:** `--agent-name`, `--agent-id`, `--phone-number`, `--greeting-message`

**Optional:** `--main-language-code`, `--language-code` (repeatable, max 2), `--voice` (repeatable, `lang:name`), `--fallback-transfer-number`, `--capability` (repeatable, `id:skillPath`), `--transfer-rule` (repeatable, `condition|label|number`), `--policy` (repeatable), `--forbidden-phrase` (repeatable)

```
write("skills/receptionist/receptionist.json", { ... })
votrix_run("receptionist.setup --agent-name '<agentName>' --agent-id '<agentId>' --phone-number '<receptionistPhoneNumber>' --greeting-message '<greetingMessage>' [--fallback-transfer-number <n>] [--main-language-code <code>] [--language-code <code>] [--voice <lang>:<voice>] [--transfer-rule 'cond|label|number'] [--policy '<line>'] [--forbidden-phrase '<phrase>']")
votrix_run("module.setup_complete receptionist")
```

- **Success** → tell admin the receptionist is live, provide the phone number, and invite them to test it by calling that number. If `booking` is not configured in Module Status, ask: "Want callers to be able to book appointments over the phone?"
- **Failure** → report the error; fix flags or json and retry. Do not call `module.setup_complete` until the command succeeds.

---

## Destructive operations

All require a warning + explicit confirmation.

| Operation | Command | Notes |
|---|---|---|
| Reset behavior config | `votrix_run("module.setup_reset receptionist")` | Clears `behavior.*` and `policy` in receptionist.json. Does not delete agent or unbind phone. |
| Unbind number | `receptionist.unbind_phone` | Number stays in account; `phone.receptionistPhoneNumber` → null. |
| Release number | `phone.release --number <n>` | Permanently deleted, cannot be undone. |
| Delete agent | `receptionist.delete_agent --agent-id <agentId>` | Sets all `phone.*` to null. |

---

## receptionist.json Schema

```jsonc
{
  "_meta": {
    "produced_by": "receptionist-setup.md",
    "schema_version": "1.2",
    "last_updated": ""              // updated to current timestamp on every write
  },

  // ── Voice / phone (backend is source of truth, synced on pre-flight) ──
  "phone": {
    "agentId": null,                // string | null
    "agentName": null,              // string | null
    "mainLanguageCode": null,       // string | null — e.g. "en-US"
    "languageCodes": [],            // string[] — max 2
    "voice": {},                    // object — { "<langCode>": "<voiceName>" }
    "fallbackTransferNumber": null, // string | null — international format
    "receptionistPhoneNumber": null // string | null — international format
  },

  // ── AI behavior config (json is source of truth) ──────────
  "behavior": {
    "greetingMessage": null,        // string | null
    "transferRules": [],            // { condition: string, label: string, number: string }[]
    "forbiddenPhrases": []          // string[]
  },

  "policy": [],                     // string[] — built-in + custom, merged

  // ── Post-call summary config ──────────────────────────
  "summary": {
    "tagChoices": [                 // string[] — AI picks one tag per call, written to session labels
      "appointment", "inquiry", "complaint", "marketing", "wrong_number", "other"
    ],
    "additionalInstructions": null  // string | null — appended to default summary prompt
  }
}
```

### Field reference

| Field | Type | Source of truth | Default |
|---|---|---|---|
| `phone.agentId` | string\|null | backend | `null` |
| `phone.agentName` | string\|null | backend | `null` |
| `phone.mainLanguageCode` | string\|null | backend | `null` |
| `phone.languageCodes` | string[] | backend | `[]` |
| `phone.voice` | object | backend | `{}` |
| `phone.fallbackTransferNumber` | string\|null | backend | `null` |
| `phone.receptionistPhoneNumber` | string\|null | backend | `null` |
| `behavior.greetingMessage` | string\|null | json | `null` |
| `behavior.transferRules` | object[] | json | `[]` |
| `behavior.forbiddenPhrases` | string[] | json | `[]` |
| `policy` | string[] | json | built-in |
| `summary.tagChoices` | string[] | json | default choices |
| `summary.additionalInstructions` | string\|null | json | `null` |

---

## Example

```json
{
  "_meta": {
    "produced_by": "receptionist-setup.md",
    "schema_version": "1.2",
    "last_updated": "2025-01-15T10:30:00Z"
  },
  "phone": {
    "agentId": "agt_abc123",
    "agentName": "Sunny Dental",
    "mainLanguageCode": "en-US",
    "languageCodes": ["en-US", "zh-CN"],
    "voice": { "en-US": "Zara", "zh-CN": "Xiaoxiao" },
    "fallbackTransferNumber": "+16501234567",
    "receptionistPhoneNumber": "+14151234567"
  },
  "behavior": {
    "greetingMessage": "Thank you for calling Sunny Dental, how can I help you today?",
    "transferRules": [
      { "condition": "caller requests to speak with a person", "label": "Front Desk", "number": "+16501234567" }
    ],
    "forbiddenPhrases": []
  },
  "policy": [
    "Stay polite and professional; never argue with the caller.",
    "If unsure, say so honestly — don't guess.",
    "For pricing questions: exact pricing is available in store.",
    "No medical, legal, or financial advice.",
    "If caller is abusive, politely end the call.",
    "Always offer to transfer to a real person if the caller is unsatisfied.",
    "If the caller shows sales or marketing intent, politely decline and end the call.",
    "If the caller does not appear to be a genuine customer, politely decline and end the call."
  ],
  "summary": {
    "tagChoices": ["appointment", "inquiry", "complaint", "marketing", "wrong_number", "other"],
    "additionalInstructions": "Also note whether the caller mentioned having insurance."
  }
}
```

---

## Rules

- All phone numbers in international format (`+<country><number>`).
- `phone.*` fields are written only by commands — do not edit manually.
- On pre-flight, if `phone.*` differs from backend, overwrite with backend values.
- Language defaults to en-US; do not ask. Max 2 if admin requests.
- Voice defaults to Zara/Xiaoxiao; do not ask unless admin raises it.
- Require explicit admin confirmation before purchasing a number (incurs a charge).
- Warn that releasing a number is permanent before proceeding.
- Built-in policy entries cannot be removed; always write them into the `policy` array.
- Always write the complete `receptionist.json` after any change — no partial writes.
- `module.setup_complete receptionist` is only called after `receptionist.setup` succeeds — never before.