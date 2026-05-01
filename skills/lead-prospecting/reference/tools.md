# Lead Prospecting — Tool Reference

## Apollo

### APOLLO_PEOPLE_SEARCH

Search Apollo's contact database for people matching ICP criteria. Results capped at 50,000 records.

```
APOLLO_PEOPLE_SEARCH(
  person_titles = ["VP of Marketing", "Head of Growth"],
  person_seniorities = ["vp", "director"],
  organization_num_employees_ranges = ["51,100", "101,200"],
  person_locations = ["United States"],
  per_page = 25,
  page = 1
)
→ data.people = [{id, first_name, last_name, title, email, email_status, linkedin_url, organization: {name, industry, estimated_num_employees, ...}}, ...]
→ data.pagination = {page, per_page, total_entries, total_pages}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `person_titles` | array | No | Job title keywords (e.g., "software engineer"). Each entry must be a plain string — no boolean operators |
| `person_seniorities` | array | No | Seniority levels: `"owner"`, `"c_suite"`, `"vp"`, `"director"`, `"manager"`, `"senior"`, `"entry"` |
| `person_locations` | array | No | Geographic locations (e.g., "California", "London") |
| `organization_locations` | array | No | Company HQ locations |
| `organization_num_employees_ranges` | array | No | Employee count ranges in `"min,max"` format (see mapping below) |
| `q_organization_domains` | array | No | Company domains (e.g., "apollo.io") — exclude `www.` |
| `q_keywords` | string | No | Search keywords for profile fields |
| `contact_email_status` | array | No | Filter: `"verified"`, `"unverified"`, `"likely to engage"`, `"unavailable"` |
| `per_page` | integer | No | Results per page (max 100) |
| `page` | integer | No | Page number (1-based, max 500) |

**Employee range mapping:**

| ICP Range | Apollo Format |
|-----------|---------------|
| 1-10 | `"1,10"` |
| 11-50 | `"11,20"`, `"21,50"` |
| 51-200 | `"51,100"`, `"101,200"` |
| 201-500 | `"201,500"` |
| 501-2000 | `"501,1000"`, `"1001,2000"` |
| 2001-5000 | `"2001,5000"` |
| 5000+ | `"5001,10000"`, `"10001,1000000"` |

---

## Web Search

### COMPOSIO_SEARCH_TAVILY

LLM-optimized web search for name resolution and lead validation.

```
COMPOSIO_SEARCH_TAVILY(
  query = "Jane Smith VP Marketing Acme Corp LinkedIn",
  search_depth = "basic",
  max_results = 3
)
→ data.results = [{title, url, content, score}, ...]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `max_results` | integer | No | Max results to return |
| `search_depth` | string | No | `"basic"` or `"advanced"` |
| `include_answer` | boolean | No | Include direct answer |

---

## Google Sheets

### GOOGLESHEETS_BATCH_GET

Read data from one or more ranges in a spreadsheet.

```
GOOGLESHEETS_BATCH_GET(
  spreadsheet_id = "1abc...",
  ranges = ["Leads!A1:N10000"]
)
→ data.valueRanges = [{range, values: [[row1], [row2], ...]}, ...]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `spreadsheet_id` | string | Yes | Spreadsheet ID |
| `ranges` | array | No | Cell ranges in A1 notation. Use bounded ranges for large sheets |
| `valueRenderOption` | string | No | `"FORMATTED_VALUE"` (default), `"UNFORMATTED_VALUE"`, `"FORMULA"` |

### GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND

Append rows of data after the last row with content in a sheet.

```
GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND(
  spreadsheet_id = "1abc...",
  range = "Leads!A1",
  values = [
    ["First Name", "Last Name", "Email", "Title", "Company"],
    ["Jane", "Smith", "jane@acme.com", "VP Marketing", "Acme Corp"]
  ]
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `spreadsheet_id` | string | Yes | Spreadsheet ID |
| `range` | string | Yes | Target range in A1 notation (data appends after last row) |
| `values` | array | Yes | 2D array of row data |
| `valueInputOption` | string | No | `"RAW"` or `"USER_ENTERED"` (default) |

---

## Error Codes

| Code | Meaning |
|------|---------|
| 401 | Invalid API key or expired token |
| 422 | Invalid parameters |
| 429 | Rate limited — back off and retry |
| 500 | Server error — retry with backoff |
