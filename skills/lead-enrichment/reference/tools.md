# Lead Enrichment — Tool Reference

## Web Search

### COMPOSIO_SEARCH_TAVILY

LLM-optimized web search for market research, industry trends, and competitor intel.

```
COMPOSIO_SEARCH_TAVILY(
  query = "SaaS industry trends 2026 B2B",
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
| `include_answer` | boolean | No | Include direct answer |
| `include_raw_content` | boolean | No | Include raw content |
| `exclude_domains` | array | No | Domains to exclude |
| `include_domains` | array | No | Only these domains |

---

## Web Scraping

### FIRECRAWL_SCRAPE

Extract full content from high-value pages (industry reports, competitor pages, articles).

```
FIRECRAWL_SCRAPE(
  url = "https://example.com/industry-report",
  onlyMainContent = true
)
→ data.markdown = scraped content
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | Yes | Fully qualified URL |
| `onlyMainContent` | boolean | No | Main content only. Default: true |
| `formats` | array | No | Output formats. Default: `["markdown"]` |
| `timeout` | integer | No | Timeout in ms. Default: 30000 |

---

## Apollo

### APOLLO_SEARCH_NEWS_ARTICLES

Search for recent news articles about companies in Apollo's database.

```
APOLLO_SEARCH_NEWS_ARTICLES(
  organization_ids = ["5e66b6381e05b4008c8331b8"],
  per_page = 10,
  page = 1
)
→ data.news_articles = [{title, url, published_at, categories, ...}, ...]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `organization_ids` | array | Yes | Apollo organization IDs |
| `per_page` | integer | No | Results per page (max 100) |
| `page` | integer | No | Page number |
| `categories` | array | No | Filter by category: `"hires"`, `"investment"`, `"contract"`, etc. |
| `published_at_min` | string | No | Lower date bound (YYYY-MM-DD) |
| `published_at_max` | string | No | Upper date bound (YYYY-MM-DD) |

### APOLLO_GET_ORGANIZATION

Get detailed information about a specific organization by its Apollo ID.

```
APOLLO_GET_ORGANIZATION(
  id = "5e66b6381e05b4008c8331b8"
)
→ data.organization = {name, website_url, industry, estimated_num_employees, funding, technologies, ...}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Apollo organization ID |

### APOLLO_GET_ORGANIZATION_JOB_POSTINGS

Get job postings for a specific organization (hiring signals).

```
APOLLO_GET_ORGANIZATION_JOB_POSTINGS(
  organization_id = "5e66b6381e05b4008c8331b8",
  per_page = 25
)
→ data.job_postings = [{title, location, department, ...}, ...]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `organization_id` | string | Yes | Apollo organization ID |
| `per_page` | integer | No | Results per page (max 100) |
| `page` | integer | No | Page number |

---

## Google Sheets

### GOOGLESHEETS_BATCH_GET

Read data from one or more ranges.

```
GOOGLESHEETS_BATCH_GET(
  spreadsheet_id = "1abc...",
  ranges = ["Leads!A1:N10000"]
)
→ data.valueRanges = [{range, values: [[row], ...]}, ...]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `spreadsheet_id` | string | Yes | Spreadsheet ID |
| `ranges` | array | No | Cell ranges in A1 notation |

### GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND

Append enrichment data to the Enrichment tab.

```
GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND(
  spreadsheet_id = "1abc...",
  range = "Enrichment!A1",
  values = [
    ["Email", "Fit Score", "Intent Score", "Timing Score", "Overall Score", "Tier", ...],
    ["jane@acme.com", 85, 70, 60, 74, "B", ...]
  ]
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `spreadsheet_id` | string | Yes | Spreadsheet ID |
| `range` | string | Yes | Target range in A1 notation |
| `values` | array | Yes | 2D array of row data |
| `valueInputOption` | string | No | `"RAW"` or `"USER_ENTERED"` (default) |
