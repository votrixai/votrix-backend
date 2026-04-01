---
name: phone
description: "Manage phone numbers and send SMS messages. Admin only."
type: skill
audience: admin
---

# phone

> **Admin only.** Manage phone numbers in the account and send SMS messages.
> Phone numbers are account-level resources — they can be assigned to modules (e.g. receptionist) or used standalone for SMS.

---

## Commands

> All commands below are executed via `votrix_run("command [flags]")`.

### List numbers

**Triggers:** "what numbers do I have", "show me my phone numbers", "which number is the receptionist using"

```
phone.list

-> { numbers: [string] }
```

Display as a numbered list of phone numbers.

---

### Search available numbers

**Triggers:** "I want a new number", "find me a number", "get a number with area code 415"

```
phone.search [--area-code <code>]

-> { numbers: [string] }
```

Show the list and ask which one the admin wants to buy. Do not purchase without explicit confirmation.

---

### Buy a number

**Triggers:** admin selects a number from search results, "buy this one", "get that number"

> **Incurs a charge — require explicit admin confirmation before executing.**

```
phone.buy --number <number>

-> { status: "purchased", number }
```

After purchase, ask if the admin wants to use it with the receptionist. If yes, read **skills/receptionist/reference/receptionist-setup.md** and go to「Manage Phone Numbers → Bind」.

---

### Release a number

**Triggers:** "I don't need this number anymore", "get rid of that number", "remove my number"

> **Permanently deleted and cannot be recovered — warn and require explicit confirmation before executing.**

```
phone.release --number <number>

-> { status: "released", number }
```

---

### Send SMS

**Triggers:** "send a text to", "SMS this customer", "text them that"

```
sms.send --to <phone> --body '<message>'

-> { status: "sent" }
```

- `--body` is composed by you based on context — never include internal IDs
- Always confirm the recipient and message content with the admin before sending
- All phone numbers in international format (`+<country><number>`)

---

## Rules

- Require explicit admin confirmation before **buying** a number (incurs a charge).
- Warn that **releasing** a number is permanent and cannot be undone — require explicit confirmation.
- All phone numbers in international format (`+<country><number>`).
- `sms.send --body` is always composed by you — never expose internal IDs or raw system values.
- Binding/unbinding numbers to specific modules (e.g. receptionist) is handled in those modules' setup flows, not here.
