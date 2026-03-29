---
name: booking-setup
description: "Configure the booking system (mode, staff, services, scheduling rules). Admin only."
type: setup
audience: admin
produces_config: skills/booking/booking.json
---

# booking-setup

> **Admin only.** Run during merchant configuration — never during a customer conversation.

Help the merchant configure their booking system. Goal: **done in 2–3 exchanges.** Infer what you can, only ask what you must.

---

## Phase 0 — Read context, build a draft

Silently read **USER.md** and the module status in the system prompt. Infer as much as possible: industry type, bookable services, staff, working hours, timezone. Use what you can confirm, only ask about what you can't.

**Inference principle:** Based on industry and merchant context, infer all reasonable defaults — staff titles, service durations, scheduling rules, staff assignment patterns. A dental cleaning is typically 30–60 minutes, a hair colour 90–120 minutes, a personal training session 60 minutes. You should already know this. Only ask when you can't infer.

---

## Phase 1 — Talk to the merchant, fill in the gaps

Based on Phase 0, only ask about what's still unknown. Don't re-ask things you already know.

### Booking mode

**managed** — The merchant uses Google Calendar to manage bookings. I can query availability, book on behalf of callers, and create or modify calendar events. All booking commands are available. A booking link can also be configured so customers can self-book.

**notify** — The merchant uses an external booking system (not Google Calendar), or handles bookings manually. I cannot view or manage booking information. If a third-party link is available, I send it to the customer. If not, I collect their details for the merchant to follow up.

Default to `managed`. Only switch to `notify` if the merchant explicitly says they use an external system or don't want me managing bookings.

### Transfer number

The number to transfer to when a customer requests a human. Defaults to the business phone number in USER.md — only ask if there isn't one.

Transfer triggers:
- Customer explicitly asks to speak to a person
- No available slots: ask the customer if they'd like to be transferred (don't auto-transfer)

Write into `special_instructions` — no dedicated field needed.

### Guiding custom workflows

Don't ask "do you have a custom workflow" — the merchant won't know how to answer. Lead with concrete examples:
> "When a customer calls to book, do you normally ask anything besides service and time? Some clinics ask about insurance first, some beauty salons ask about allergies. If there's nothing special, we can skip this."

Write any custom steps the merchant mentions directly into `special_instructions`.

### Conversation principles

- Use what you can infer — don't ask about everything
- When the merchant says something that covers multiple fields, infer them all — don't break it into separate questions
- Point out contradictions immediately (e.g. says Saturday is open but no staff scheduled for Saturday)
- If the merchant wants to adjust, keep talking. Once they say "looks good," move to Phase 2
- Confident but not pushy

---

## Phase 2 — Generate config and write file

Once the merchant confirms, write the full config to **skills/booking/booking.json**. Always write the complete config — write replaces the entire file each time.

```
write("skills/booking/booking.json", { ... })
```

### After writing

**notify mode:**
```
votrix_run("module.setup_complete booking")
```
Tell the merchant the setup is complete and briefly recap.

**managed mode + `connections.google-calendar` is already `true` (previously connected):**
Check whether all staff in booking.json have a non-null `calendar_id`.
- All bound → `votrix_run("module.setup_complete booking")`, confirm done
- Some unbound → read **skills/booking/reference/google-calendar-setup.md** to complete binding, then return here

**managed mode + `connections.google-calendar` is `false`:**
Tell the merchant the config is saved and Google Calendar still needs to be connected.
Read **skills/booking/reference/google-calendar-setup.md** to continue.

### After returning from google-calendar-setup

Read current **skills/booking/booking.json** and confirm all staff `calendar_id` fields are not null:
- All confirmed → `votrix_run("module.setup_complete booking")`, tell the merchant the booking system is fully ready
- Still unbound → guide the merchant to resolve remaining bindings, do not call setup_complete

---

## Subsequent changes

1. Read the current **skills/booking/booking.json**
2. Only discuss what needs changing — don't re-run the full setup
3. After confirming changes, write the full updated config

---

## booking.json Schema

```jsonc
{
  // "managed": I manage bookings directly via Google Calendar / booking link
  // "notify":  I don't manage bookings — send link or notify merchant
  "mode": "managed | notify",

  // managed mode: booking_link = self-booking link, null to disable
  // notify mode:   booking_link = third-party link to send customer, null to collect details manually
  "mode_config": {
    "booking_link": "https://..."
  },

  // timezone lives in registry.json — do NOT write it here

  "services": [
    {
      "name": "Haircut",           // use the merchant's own terminology
      "duration_mins": 30,         // inferred from industry
      "notes": null                // things to know or ask the customer
    }
  ],

  "staff": [
    {
      "name": "Sarah",
      "services": ["Haircut", "Colour"], // ["*"] means all services
      "hours": {                          // missing keys = day off
        "mon": { "open": "09:00", "close": "18:00" },
        "tue": { "open": "09:00", "close": "18:00" }
      },
      "calendar_id": null           // written by google-calendar-setup, null if unbound
    }
  ],

  "scheduling_rules": {
    "min_notice_hours": 2,          // minimum hours in advance to book
    "buffer_mins": 15,              // gap between appointments
    "max_bookings_per_day": null,   // max bookings per day
    "advance_booking_days": 30,     // how far out customers can book
    "additional": []                // rules that don't fit structured fields, natural language
  },

  "intake_fields": [
    { "field": "Name", "required": true }
  ],

  "special_instructions": [
    "Before booking, ask if patient has dental insurance. If no, inform self-pay pricing.",
    "No available slots: ask customer if they'd like to be transferred to +1-555-0123."
  ]
}
```

---

## Examples

### managed — Hair salon

```json
{
  "mode": "managed",
  "mode_config": {
    "booking_link": "https://book.xxx.com/janes-salon"
  },
  "services": [
    { "name": "Haircut", "duration_mins": 30, "notes": null },
    { "name": "Colour", "duration_mins": 90, "notes": "Ask if they've coloured in the past 6 months." }
  ],
  "staff": [
    {
      "name": "Sarah",
      "services": ["Haircut", "Colour"],
      "hours": {
        "mon": { "open": "09:00", "close": "18:00" },
        "tue": { "open": "09:00", "close": "18:00" },
        "wed": { "open": "09:00", "close": "18:00" },
        "thu": { "open": "09:00", "close": "18:00" },
        "fri": { "open": "09:00", "close": "18:00" },
        "sat": { "open": "10:00", "close": "14:00" }
      },
      "calendar_id": null
    }
  ],
  "scheduling_rules": {
    "min_notice_hours": 2,
    "buffer_mins": 15,
    "max_bookings_per_day": null,
    "advance_booking_days": 30,
    "additional": []
  },
  "intake_fields": [
    { "field": "Name", "required": true }
  ],
  "special_instructions": [
    "No available slots: ask customer if they'd like to be transferred to +1-555-0123."
  ]
}
```

### notify — Barbershop

```json
{
  "mode": "notify",
  "mode_config": {
    "booking_link": "https://calendly.com/mikes-barber"
  },
  "services": [
    { "name": "Haircut", "duration_mins": 30, "notes": null },
    { "name": "Beard Trim", "duration_mins": 15, "notes": null }
  ],
  "staff": [
    {
      "name": "Mike",
      "services": ["*"],
      "hours": {
        "mon": { "open": "09:00", "close": "17:00" },
        "tue": { "open": "09:00", "close": "17:00" },
        "wed": { "open": "09:00", "close": "17:00" },
        "thu": { "open": "09:00", "close": "17:00" },
        "fri": { "open": "09:00", "close": "17:00" }
      },
      "calendar_id": null
    }
  ],
  "scheduling_rules": null,
  "intake_fields": [
    { "field": "Name", "required": true }
  ],
  "special_instructions": [
    "If booking link is unavailable or customer prefers: collect name and number, text +1-555-0789."
  ]
}
```

---

## Reset

**Reset booking config:**

1. **Warn:** "This will clear all booking configuration. You'll need to re-run setup to use booking again."
2. After confirmation:
```
votrix_run("module.setup_reset booking")
```