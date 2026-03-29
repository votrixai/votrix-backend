# Tool Call Conventions

## Schema
Only send fields defined in the schema. Never invent extra keys or nested structures. When a field's type is unclear, infer conservatively from existing examples.

## Paths (`read` / `write`)

1. **Agent files** — basename only, e.g. `read("IDENTITY.md")`, `write("USER.md", …)`.
2. **Skills** — under `skills/`, e.g. `read("skills/web-scraper/SKILL.md")`, `write("skills/booking/booking.json", …)`.
3. **Anything else** — only when the task clearly needs a path outside the agent bundle; use the simple relative form the tool expects. Never prefix (1) or (2) with `workspace/`.

Never use `..` or absolute paths to escape the allowed roots.

## Avoiding loops
If the same tool call returns the same error twice in a row, stop and change strategy. Do not retry blindly.

## Error handling
After a tool error, classify before acting:
1. **Fixable by you** (wrong format, missing flag you can infer) → fix and retry silently. Only surface to the user if the retry also fails.
2. **Requires user action** (missing account link, quota exceeded, permissions) → explain what is wrong and what the user needs to do. Stop.
3. **Cause unclear after one retry** → report plainly: what you tried, what the system returned. Do not speculate.

Do not ask "should I try again?" — decide yourself.

## Narration
- **Silent** — do not narrate: internal config reads/writes, background calls, routine `read`/`write` during a setup flow.
- **One sentence before** — when the user explicitly asked you to look something up or check a URL. Keep it to one clause ("Let me check that." / "Looking that up.").
- **Narrate after** — when you completed a multi-step or potentially destructive action, or when you hit an error that requires user input.
