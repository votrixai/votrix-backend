---
name: google-search
description: "Search the web or look up information (company, product, fact)."
type: skill
audience: admin
---

# google-search

Use this skill when the user wants to **search the web** or **look up** something (e.g. a company, product, fact, or current information).

**All capabilities come from `votrix_run`.** Use `votrix_run` with one of:

- `search "<query>"`
- `google search "<query>"`

---

## Behavior

- The handler runs a Google search and returns a summarized view of the top results.
- Use for factual lookups, company/product info, and when the user asks "what is X" or "look up X".

---

## Rules

| Rule | Detail |
|------|--------|
| Use votrix_run | Run `votrix_run("search \"<query>\"")` or `votrix_run("google search \"<query>\"")` |
| Quote query | Use quotes around the query if it contains spaces or special characters |
