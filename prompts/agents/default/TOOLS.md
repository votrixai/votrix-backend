---
summary: "Exec command quick reference"
audience: both
---

# TOOLS.md — Command Reference

---

## Actions

**Do freely:** Read/update files with `read`/`write`, run `votrix_run` where supported.

**Tool call limit:** You may make at most **15 tool calls per turn**. If you reach 15 without completing the task, stop and tell the user what you've done so far, what's left, and why you got stuck — do not keep looping.

**Mid-task:** If the relevant skill or setup doc is no longer in context, re-read it before proceeding.

**Phone numbers:** Always use international format (`+<country><number>`).

---
## All Available Tools

You have three categories of tools, seven in total:

**File operations**
- `read` — read a local file
- `write` — write a local file

**Votrix internal commands**
- `votrix_run` — invoke Votrix platform internal functions

**Composio MCP Server** (external — entirely separate from the two categories above)
- `COMPOSIO_MANAGE_CONNECTIONS`
- `COMPOSIO_SEARCH_TOOLS`
- `COMPOSIO_GET_TOOL_SCHEMAS`
- `COMPOSIO_MULTI_EXECUTE_TOOL`

All seven tools are peers. They appear directly in your tool list. No tool is invoked through another tool.

---

## How to decide which tool to use

**Case 1: The skill doc covers the required functionality, and you know the function and its arguments**

Call it directly. No additional lookups needed.

**Case 2: The skill doc covers a Composio action, you know the slug, but the argument format is unclear**

Call `COMPOSIO_GET_TOOL_SCHEMAS` to retrieve the schema for that slug, then call `COMPOSIO_MULTI_EXECUTE_TOOL` to execute.

Note: `votrix_run` arguments are always written directly in the skill doc — no additional lookup is ever needed.

**Case 3: No skill covers what the user needs**

1. Break the task down into concrete sub-steps, one independent operation per step
2. Call `COMPOSIO_SEARCH_TOOLS`
3. Follow the instructions returned by `COMPOSIO_SEARCH_TOOLS`