# Apollo API Reference

## APOLLO_PEOPLE_SEARCH

Search Apollo's contact database for people using ICP filters. Results capped at 50,000 records. Does not enrich contact data — records may have null email, phone, or organization fields.

```
APOLLO_PEOPLE_SEARCH(
  person_titles = ["VP of Marketing", "Head of Growth"],
  person_seniorities = ["vp", "director"],
  organization_num_employees_ranges = ["51,100", "101,200"],
  person_locations = ["United States"],
  per_page = 25,
  page = 1
)
```

### Key Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `person_titles` | array[string] | Job title keywords. Each entry must be a plain string — do not embed boolean operators (e.g., "title1 OR title2") |
| `person_seniorities` | array[string] | `"owner"`, `"c_suite"`, `"vp"`, `"director"`, `"manager"`, `"senior"`, `"entry"` |
| `person_locations` | array[string] | Person locations (e.g., "United States", "California") |
| `organization_locations` | array[string] | Company HQ locations |
| `organization_num_employees_ranges` | array[string] | Ranges in `"min,max"` format (see mapping below) |
| `q_organization_domains` | array[string] | Company domains — exclude `www.` prefix |
| `q_keywords` | string | Search keywords for profile fields. Avoid full names (last names often obfuscated) |
| `contact_email_status` | array[string] | `"verified"`, `"unverified"`, `"likely to engage"`, `"unavailable"` |
| `per_page` | integer | Results per page (max 100) |
| `page` | integer | Page number (1-based, max 500) |

### Response Structure

```json
{
  "people": [
    {
      "id": "string",
      "first_name": "string",
      "last_name": "string",
      "title": "string",
      "seniority": "string",
      "departments": ["string"],
      "email": "string",
      "email_status": "verified|guessed|unavailable",
      "linkedin_url": "string",
      "organization": {
        "name": "string",
        "website_url": "string",
        "industry": "string",
        "estimated_num_employees": 100,
        "city": "string",
        "state": "string",
        "country": "string"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 25,
    "total_entries": 500,
    "total_pages": 20
  }
}
```

### Employee Range Mapping

| ICP Range | Apollo Format |
|-----------|---------------|
| 1-10 | `"1,10"` |
| 11-50 | `"11,20"`, `"21,50"` |
| 51-200 | `"51,100"`, `"101,200"` |
| 201-500 | `"201,500"` |
| 501-2000 | `"501,1000"`, `"1001,2000"` |
| 2001-5000 | `"2001,5000"` |
| 5000+ | `"5001,10000"`, `"10001,1000000"` |

### Rate Limits

- Standard: 50 requests/minute
- Credit cost: ~1 credit per person record accessed
- Free plan: max ~25 results per search, limited total credits

### Error Codes

| Code | Meaning |
|------|---------|
| 401 | Invalid API key |
| 422 | Invalid parameters — start broad and narrow iteratively |
| 429 | Rate limited — back off and retry |
| 500 | Server error — retry with backoff |
