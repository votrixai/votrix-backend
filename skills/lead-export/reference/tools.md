# Lead Export — Tool Reference

## Google Sheets

### GOOGLESHEETS_BATCH_GET

Read data from Leads and Enrichment tabs.

```
GOOGLESHEETS_BATCH_GET(
  spreadsheet_id = "1abc...",
  ranges = ["Leads!A1:N10000", "Enrichment!A1:N10000"]
)
→ data.valueRanges = [{range, values: [[row], ...]}, ...]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `spreadsheet_id` | string | Yes | Spreadsheet ID |
| `ranges` | array | No | Cell ranges in A1 notation |
| `valueRenderOption` | string | No | `"FORMATTED_VALUE"` (default), `"UNFORMATTED_VALUE"`, `"FORMULA"` |

### GOOGLESHEETS_VALUES_UPDATE

Update a specific range of cells (e.g., remove invalid leads, update statuses).

```
GOOGLESHEETS_VALUES_UPDATE(
  spreadsheet_id = "1abc...",
  range = "Leads!A2:N50",
  values = [[...], [...]]
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `spreadsheet_id` | string | Yes | Spreadsheet ID |
| `range` | string | Yes | Target range in A1 notation |
| `values` | array | Yes | 2D array of row data |
| `valueInputOption` | string | No | `"RAW"` or `"USER_ENTERED"` (default) |

### GOOGLESHEETS_ADD_SHEET

Create the Removed tab for invalid leads.

```
GOOGLESHEETS_ADD_SHEET(
  spreadsheet_id = "1abc...",
  title = "Removed",
  force_unique = true
)
→ data.sheetId
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `spreadsheet_id` | string | Yes | Spreadsheet ID |
| `title` | string | No | Tab name |
| `force_unique` | boolean | No | Auto-append suffix if exists. Default: true |

### GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND

Write removed leads and campaign summary to their respective tabs.

```
GOOGLESHEETS_SPREADSHEETS_VALUES_APPEND(
  spreadsheet_id = "1abc...",
  range = "Removed!A1",
  values = [
    ["Email", "Name", "Reason"],
    ["bad@example", "John Doe", "Invalid email format"]
  ]
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `spreadsheet_id` | string | Yes | Spreadsheet ID |
| `range` | string | Yes | Target range in A1 notation |
| `values` | array | Yes | 2D array of row data |
| `valueInputOption` | string | No | `"RAW"` or `"USER_ENTERED"` (default) |
