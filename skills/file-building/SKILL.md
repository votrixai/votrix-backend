---
name: file-building
description: "Create a downloadable file for the user — CSV, JSON, TXT, Markdown, XLSX, PDF, etc. Triggers when the user asks to create, generate, build, produce, export, or make a file or document they can download."
type: skill
---

# File Building

Produce a downloadable file for the user in two steps: **write the file to the sandbox**, then **signal it as a downloadable** via the `create_downloadable_file` tool.

## Workflow

1. **Clarify** — if schema, columns, format, or filename is ambiguous, ask one concise question. Skip when the request is obvious (e.g. "give me a sample CSV with 10 rows of user data").
2. **Write the file** — use the `write` tool (for small text files) or the `bash` tool (for anything else, e.g. generating xlsx with openpyxl). Save under `/workspace/` with a concise, descriptive filename.
3. **Call `create_downloadable_file`** with just the filename (basename, not full path). The backend finds the file in the session and surfaces it as a download link in the UI.
4. **Confirm** — one short sentence telling the user the file is ready. Do not paste the full file contents back in chat unless asked.

## Tool schema

```
create_downloadable_file(filename: str) → { file_id, filename, mime_type }
```

`filename` is the basename you saved — e.g. `"report.csv"`, not `"/workspace/report.csv"`.

## Examples

### CSV (via `write` tool)
Write to `/workspace/sample_users.csv`:
```
name,email,signup_date
Alice,alice@example.com,2026-01-14
Bob,bob@example.com,2026-01-15
```
Then:
```
create_downloadable_file(filename="sample_users.csv")
```

### JSON (via `write` tool)
Write to `/workspace/report.json`:
```json
{"total": 42, "items": []}
```
Then:
```
create_downloadable_file(filename="report.json")
```

### XLSX (via `bash` tool)
```bash
python3 - <<'PY'
import openpyxl
wb = openpyxl.Workbook(); ws = wb.active
ws.append(["name","amount"])
ws.append(["Alice",123.45])
wb.save("/workspace/ledger.xlsx")
PY
```
Then:
```
create_downloadable_file(filename="ledger.xlsx")
```

## Rules

- Always write the file FIRST, then call `create_downloadable_file`.
- Pass only the basename to `create_downloadable_file`. Never invent a `file_id`.
- CSV output always includes a header row.
- Use UTF-8 for text files.
- Filenames use underscores, not spaces.
- For large datasets (>10k rows or >5 MB), confirm scope with the user before generating.
