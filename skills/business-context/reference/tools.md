# Business Context — Tool Reference

## Web Scraping

### FIRECRAWL_SCRAPE

Scrape a publicly accessible URL to retrieve content in markdown format.

```
FIRECRAWL_SCRAPE(
  url = "https://example.com",
  onlyMainContent = true
)
→ data.markdown = scraped page content
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | Yes | Fully qualified URL (http/https) |
| `onlyMainContent` | boolean | No | Extract main content only, excluding nav/footer. Default: true |
| `formats` | array | No | Output formats. Default: `["markdown"]` |
| `timeout` | integer | No | Timeout in ms. Default: 30000 |

---

## Web Search

### COMPOSIO_SEARCH_TAVILY

Search the web for business information using LLM-optimized search.

```
COMPOSIO_SEARCH_TAVILY(
  query = "Acme Corp SaaS product overview",
  search_depth = "advanced",
  max_results = 5
)
→ data.results = [{title, url, content, score}, ...]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `max_results` | integer | No | Max results to return |
| `search_depth` | string | No | `"basic"` or `"advanced"` |
| `include_answer` | boolean | No | Include direct answer in results |
| `include_raw_content` | boolean | No | Include raw HTML content |
| `exclude_domains` | array | No | Domains to exclude |
| `include_domains` | array | No | Only return results from these domains |

---

## Google Sheets

### GOOGLESHEETS_CREATE_GOOGLE_SHEET1

Create a new Google Spreadsheet.

```
GOOGLESHEETS_CREATE_GOOGLE_SHEET1(
  title = "q2-saas-push-1714500000"
)
→ data.spreadsheetId, data.spreadsheetUrl
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | No | Spreadsheet title. Default: "Untitled spreadsheet" |
| `folder_id` | string | No | Google Drive folder ID |

### GOOGLESHEETS_ADD_SHEET

Add a new tab to an existing spreadsheet.

```
GOOGLESHEETS_ADD_SHEET(
  spreadsheet_id = "1abc...",
  title = "Leads",
  force_unique = true
)
→ data.sheetId
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `spreadsheet_id` | string | Yes | Spreadsheet ID |
| `title` | string | No | Tab name (must be unique within spreadsheet) |
| `force_unique` | boolean | No | Auto-append suffix if name exists. Default: true |

---

## Connection Management

### COMPOSIO_MANAGE_CONNECTIONS

Check or initiate connections to user's apps.

```
COMPOSIO_MANAGE_CONNECTIONS(
  toolkits = ["googlesheets"]
)
→ connected: true/false, redirect_url (if not connected)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `toolkits` | array | Yes | Toolkit slugs to check/connect |
| `reinitiate_all` | boolean | No | Force reconnection. Default: false |
