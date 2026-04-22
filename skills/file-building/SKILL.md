---
name: file-building
description: "Create a downloadable file for the user — CSV, JSON, TXT, Markdown, XLSX, PDF, etc. Triggers when the user asks to create, generate, build, produce, export, or make a file or document they can download."
type: skill
---

# File Building

Produce the file in the sandbox first. Only present it via the `download_file` tool when the user asks for the file, download, export, or attachment.

## Workflow

1. **Clarify** — if schema, columns, format, or filename is ambiguous, ask one concise question. Skip when the request is obvious (e.g. "give me a sample CSV with 10 rows of user data").
2. **Write the file** — use `write` for small text files, `bash` for anything else (e.g. xlsx via openpyxl, pdf via reportlab, images via Pillow). Save under `/workspace/` with a concise, descriptive filename.
3. **Call `download_file` only on request** — when the user asks for the file, download, export, or attachment, call `download_file` with just the basename so the UI shows a download card.
4. **Confirm** — one short sentence telling the user the file is ready or saved. If you did not call `download_file`, tell them you can surface it as a download when they want it. Don't paste the full contents back in chat.

## Tool schema

```
download_file(filename: str) → { file_id, filename, mime_type }
```

`filename` is the basename you saved — e.g. `"report.csv"`, not `"/workspace/report.csv"`.

## Examples

### CSV (via `write`)
Write to `/workspace/sample_users.csv`:
```
name,email,signup_date
Alice,alice@example.com,2026-01-14
Bob,bob@example.com,2026-01-15
```
If the user asks for the file, then:
```
download_file(filename="sample_users.csv")
```

### JSON (via `write`)
Write to `/workspace/report.json`:
```json
{"total": 42, "items": []}
```
If the user asks for the file, then:
```
download_file(filename="report.json")
```

### XLSX (via `bash`)
```bash
python3 - <<'PY'
import openpyxl
wb = openpyxl.Workbook(); ws = wb.active
ws.append(["name","amount"])
ws.append(["Alice",123.45])
wb.save("/workspace/ledger.xlsx")
PY
```
If the user asks for the file, then:
```
download_file(filename="ledger.xlsx")
```

## Rules

- Always write the file first. Call `download_file` only when the user wants the file surfaced in the UI.
- `download_file` only surfaces an existing file — it never creates, uploads, or modifies content. Do not try to pass file contents to it.
- Pass the exact basename. Never invent a `file_id`.
- CSV output always includes a header row.
- Use UTF-8 for text files.
- Filenames use underscores, not spaces.
- For large datasets (>10k rows or >5 MB), confirm scope with the user first.
