---
name: file-building
description: "Create a downloadable file for the user — CSV, JSON, TXT, Markdown, XLSX, PDF, etc. Triggers when the user asks to create, generate, build, produce, export, or make a file or document they can download."
type: skill
---

# File Building

Produce the file in the sandbox first. Only present it via tools when the user asks for the file, download, export, or attachment.

## Paths

- **Output directory:** `/mnt/session/outputs/` — all files you create for the user MUST go here. Only files in this directory can be surfaced via `download_file` or `publish_file`.
- **User uploads:** `/workspace/<filename>` — read-only input files the user attached. You can read these but do not write output here.

## Tools

### `download_file(file_path)` — private download card

Surfaces the file as a download link in the user's chat UI. The user clicks to download.

```
download_file(file_path="/mnt/session/outputs/report.csv")
→ { file_id, filename, mime_type }
```

### `publish_file(file_path)` — public URL

Uploads the file to cloud storage and returns a public URL. Use when you need a link to pass to an external API (social media post, email, etc.).

```
publish_file(file_path="/mnt/session/outputs/chart.png")
→ { url, filename, mime_type }
```

## Workflow

1. **Clarify** — if schema, columns, format, or filename is ambiguous, ask one concise question. Skip when the request is obvious.
2. **Write the file** — use `write` for small text files, `bash` for anything else (xlsx via openpyxl, pdf via reportlab, images via Pillow). Save to `/mnt/session/outputs/` with a concise, descriptive filename.
3. **Surface the file** — call `download_file` when the user asks for the file. Call `publish_file` when you need a URL for an external API.
4. **Confirm** — one short sentence telling the user the file is ready. Don't paste the full contents back in chat.

## Examples

### CSV (via `write`)

Write to `/mnt/session/outputs/sample_users.csv`:
```
name,email,signup_date
Alice,alice@example.com,2026-01-14
Bob,bob@example.com,2026-01-15
```
Then:
```
download_file(file_path="/mnt/session/outputs/sample_users.csv")
```

### XLSX (via `bash`)

```bash
python3 - <<'PY'
import openpyxl
wb = openpyxl.Workbook(); ws = wb.active
ws.append(["name","amount"])
ws.append(["Alice",123.45])
wb.save("/mnt/session/outputs/ledger.xlsx")
PY
```
Then:
```
download_file(file_path="/mnt/session/outputs/ledger.xlsx")
```

### Image for social media post (via `bash` + `publish_file`)

```bash
python3 - <<'PY'
from PIL import Image, ImageDraw
img = Image.new("RGB", (1200, 630), "#1a1a2e")
ImageDraw.Draw(img).text((100, 280), "Hello World", fill="white")
img.save("/mnt/session/outputs/og_image.png")
PY
```
Then:
```
publish_file(file_path="/mnt/session/outputs/og_image.png")
```

## Rules

- Always write the file first. The tools only surface existing files — they never create or modify content.
- All output files go directly to `/mnt/session/outputs/`. Writing elsewhere will cause the tool to fail.
- Do NOT create subdirectories under `/mnt/session/outputs/` — write files directly in the root of that directory. Subdirectory paths are stripped by the file registry and will cause lookup failures.
- Pass the full path including the directory prefix. Never invent a `file_id`.
- CSV output always includes a header row.
- Use UTF-8 for text files.
- Filenames use underscores, not spaces.
- For large datasets (>10k rows or >5 MB), confirm scope with the user first.
