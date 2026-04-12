---
name: calendar-scheduling
description: "Workflow and best practices for scheduling meetings via Google Calendar — confirmation flow, event formatting, and availability checks."
type: skill
---

# Calendar Scheduling Skill

You can create and manage calendar events on behalf of the user using the Google Calendar integration.
Always follow this workflow — never create or modify an event without confirmation.

## Scheduling workflow

1. **Gather details** — collect: title, date, time, duration, attendees (email addresses), and description if relevant
2. **Check availability** — call `GOOGLECALENDAR_LIST_EVENTS` for the relevant time window if the user hasn't confirmed the slot is free
3. **Show the summary** — present the full event details clearly before acting
4. **Confirm** — ask "Shall I create this event?" and wait for explicit approval
5. **Create** — only call `GOOGLECALENDAR_CREATE_EVENT` after confirmation

## GOOGLECALENDAR_CREATE_EVENT parameters

| Parameter | Description |
|---|---|
| `summary` | Event title |
| `start_datetime` | Start time in ISO 8601 format (e.g. `2026-04-15T14:00:00+08:00`) |
| `end_datetime` | End time in ISO 8601 format |
| `attendees` | Comma-separated list of attendee email addresses |
| `description` | Optional event description or agenda |
| `location` | Optional location or video call link |

## Format rules

- Always include the time zone offset in datetime strings — never assume UTC
- Default duration is 30 minutes unless the user specifies otherwise
- For recurring meetings, confirm the recurrence pattern explicitly before setting it
- Add a video call link (Google Meet or Zoom) when the meeting has remote attendees

## Conflict handling

- If a conflict is found, surface it clearly: "You already have [event] at that time."
- Suggest the nearest free slot before and after the conflict
- Never create an overlapping event without explicit acknowledgment from the user
