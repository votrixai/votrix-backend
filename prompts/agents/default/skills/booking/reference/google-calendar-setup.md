---
name: google-calendar-setup
description: "Connect Google Calendar and bind staff to calendars. Admin only. Run booking setup first."
type: setup
audience: admin
updates_config: skills/booking/booking.json
---

# Google Calendar Setup

> **Admin only.** Never run during a customer conversation.

Bind each staff member to a Google Calendar. Bindings are written directly into `booking.json`'s `staff[].calendar_id` — no separate config file.

Booking setup must be completed first — booking.json must exist and be complete before running this.

---

## Pre-flight check

Read **skills/booking/booking.json** and confirm all of the following:

- `mode` is `"managed"`
- `staff` has at least one member
- `services` has at least one entry with a duration

If anything is missing → stop, guide the merchant to run **skills/booking/reference/booking-setup.md** first.

Once the above pass, check Google Calendar connection status from **registry.json**:

- `connections.google-calendar` is `true` → already connected, proceed to binding flow
- `connections.google-calendar` is `false` → run connect flow below

**Connect flow (when not connected):**

1. Call `COMPOSIO_MANAGE_CONNECTIONS` (toolkit: `googlecalendar`):
   - Returns `redirect_url` → present to merchant: *"Click this link to connect Google Calendar. A small window will open — sign in, then come back here."*
   - Returns `has_active_connection: true` → registry is out of sync, proceed directly to binding flow
2. Wait for the merchant to confirm they've signed in.
3. Call `COMPOSIO_MANAGE_CONNECTIONS` again to verify:
   - Connected → `votrix_run("connection.set google-calendar")`, confirm: *"Google Calendar connected ([email])."* Proceed to binding flow.
   - Not connected → tell the merchant it wasn't detected, ask them to try again.

---

## Binding flow

Goal: every staff member's `calendar_id` is not null.

1. Read `staff` from booking.json — find members where `calendar_id` is null
2. `COMPOSIO_MULTI_EXECUTE_TOOL`, `tool_slug: "GOOGLECALENDAR_LIST_CALENDARS"` — get available calendars
3. Match by name, suggest bindings for all unbound staff at once
4. Merchant confirms or adjusts
5. **No matching calendar** → create one: `COMPOSIO_MULTI_EXECUTE_TOOL`, `tool_slug: "GOOGLECALENDAR_DUPLICATE_CALENDAR"`, arguments: `{"summary": "<name>"}`
6. **No calendars at all** → tell the merchant: *"There are no calendars in this Google account. I'll create one for each staff member — please confirm these names: [staff list]"*, then batch create
7. **Some bindings fail** → do not proceed, tell the merchant which staff are still unbound and guide them to resolve before continuing
8. Once all staff are bound, read `timezone` from booking.json and set it on each calendar:
   `COMPOSIO_MULTI_EXECUTE_TOOL`, `tool_slug: "GOOGLECALENDAR_PATCH_CALENDAR"`, arguments: `{"calendar_id": "<id>", "timezone": "<IANA>"}`
   - If timezone set fails, don't block — tell the merchant: *"Calendars are bound, but timezone couldn't be set automatically. Please confirm the timezone in Google Calendar manually."*
9. Write all `calendar_id`s into the corresponding staff entries in booking.json:

```
write("skills/booking/booking.json", { ... })
```

---

## Return to booking-setup

Once binding is written, tell the merchant the calendar binding is complete, then:

```
read("skills/booking/reference/booking-setup.md")
```

Return to booking-setup. booking-setup will handle any remaining steps and call `module.setup_complete booking`.

---

## Staff changes

### Adding a staff member

1. Add the new member to `staff` in booking.json (`calendar_id: null`)
2. `COMPOSIO_MULTI_EXECUTE_TOOL` → `GOOGLECALENDAR_LIST_CALENDARS` to find a match, or create one with `GOOGLECALENDAR_DUPLICATE_CALENDAR`
3. Write the `calendar_id` into their entry, update booking.json

### Removing a staff member

1. If they have upcoming appointments, let the merchant know and confirm
2. Remove them from `staff` in booking.json, update booking.json

---

## Reset

Disconnect all Google Calendar bindings:

1. Let the merchant know: *"This will unbind all calendars. Existing bookings won't be affected, but I won't be able to manage new ones until reconnected."*
2. After confirmation, set all `calendar_id` fields in booking.json to null, write the file:

```
write("skills/booking/booking.json", { ... })
votrix_run("connection.reset google-calendar")
```

---

## Tool reference

### COMPOSIO_MANAGE_CONNECTIONS

One call covers both "check" and "initiate" — the response determines next steps:
- Returns `has_active_connection: true` → already connected, includes account email
- Returns `redirect_url` → not connected, use this URL to initiate OAuth

Connection state is written to registry.json via `votrix_run("connection.set google-calendar")` — do not write it to booking.json.

### COMPOSIO_MULTI_EXECUTE_TOOL

Execute any Composio tool by slug. Key slugs for Google Calendar setup:

| Tool slug | Purpose |
|-----------|---------|
| `GOOGLECALENDAR_LIST_CALENDARS` | List all calendars |
| `GOOGLECALENDAR_DUPLICATE_CALENDAR` | Create a new calendar (`summary`: name) |
| `GOOGLECALENDAR_PATCH_CALENDAR` | Update calendar properties (`calendar_id`, `timezone`) |
| `GOOGLECALENDAR_CALENDARS_DELETE` | Delete a calendar (`calendar_id`) — verify no staff are bound first |

### votrix_run("connection.set google-calendar")

Sets `connections.google-calendar` to `true` in registry.json. Call immediately after OAuth is verified.

### votrix_run("connection.reset google-calendar")

Sets `connections.google-calendar` to `false` in registry.json. Call after merchant confirms reset.