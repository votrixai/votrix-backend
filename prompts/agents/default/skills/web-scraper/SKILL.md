---
name: web-scraper
description: "Fetch, scrape, or read content from a URL (webpage, article, link)."
type: skill
audience: admin
---

# web-scraper

Use this skill when the user wants to **fetch**, **scrape**, or **read content from a URL** (e.g. a webpage, article, or public link).

**All capabilities come from `votrix_run`.** Use `votrix_run` with one of:

- `web-scraper "<url>"`
- `fetch "<url>"`
- `scrape "<url>"`

---

## Behavior

- The handler fetches the page content. If the content is long (> ~8000 chars), it may be summarized.
- If the URL does not start with `http`, `https://` is prepended.
- Use this for public pages the user wants to read or summarize. Do not use for authenticated or private resources unless the user has provided access.

---

## Rules

| Rule | Detail |
|------|--------|
| Use votrix_run | Run `votrix_run("web-scraper \"https://example.com\"")` or `votrix_run("fetch \"<url>\"")` |
| Quote URLs | Use quotes around the URL if it contains spaces or special characters |
