---
name: social-media-post-analytics
description: "Fetch data from each platform, analyze post performance and audience growth, and generate reports. Triggered when admin says 'data report', 'how's performance', 'how many views', 'follower growth', 'which post performed best', 'analytics', or 'insights'."
integrations:
  - facebook
  - instagram
  - twitter
  - linkedin
---

# Analytics

You are responsible for fetching performance data from each platform, combining it with local post-history records, and generating actionable analysis reports.

---

## Startup Check

Read `/workspace/marketing-context.md` to confirm:
- List of connected platforms (only analyze connected platforms)
- Page ID / Account ID (required for API calls)

---

## Data Architecture: Two-Layer Retrieval

**Principle: Read local data first; only call APIs for missing data.**

### Layer 1: Local post-history

Path: `/workspace/post-history/{YYYY-MM}/{YYYY-MM-DD}.md`

Each post record format:
```
- Reach: -
- Engagement: -
- Likes: -
- Comments: -
- Shares: -
```

A field value of `-` means it has not been fetched yet and requires an API refresh.

### Layer 2: Platform API (refresh on demand)

Only called when local data is `-`. Process a maximum of **10 posts** per batch; after completion, inform admin and ask whether to continue.

---

## Platform API Calls

Based on connected platforms, read the corresponding reference files to execute API calls:

| Platform | Reference File |
|---|---|
| Facebook | `/workspace/skills/social-media-post-analytics/references/facebook.md` |
| Instagram | `/workspace/skills/social-media-post-analytics/references/instagram.md` |
| Twitter | `/workspace/skills/social-media-post-analytics/references/twitter.md` |
| LinkedIn | `/workspace/skills/social-media-post-analytics/references/linkedin.md` |

Each platform is fetched independently; a failure on one does not affect the others.

---

## Refreshing Local Data

After fetching from APIs, immediately update the `-` fields in the corresponding post-history files:

Read file > replace `Reach: -`, `Engagement: -`, `Likes: -`, `Comments: -`, `Shares: -` under the corresponding post > write back to file.

Also write the refresh timestamp to the corresponding platform field under `## Operational Status` in `/workspace/marketing-context.md`.

---

## Report Types

When admin says "generate a report", ask which type they want, or infer directly from the question:

### 1. Quick Summary (default)

> Admin says "how's recent performance" or "show me the data"

- Each platform's last 7 days: total reach, total engagement, new followers
- Best-performing post (per platform)
- One-sentence conclusion + 1 actionable suggestion

### 2. Post Ranking

> Admin says "which post performed best" or "post rankings"

Read all posts within the specified time range from post-history, sorted by engagement rate:

```
Engagement Rate = (Likes + Comments + Shares) / Reach x 100%
```

Display Top 5, noting platform, topic, publish time, and key metrics.
Analyze common traits: time slots, content types, hashtag combinations.

### 3. Account Growth

> Admin says "how's follower growth" or "how many new followers"

- Follower count changes per platform (this week vs last week)
- Fastest growth periods
- What content was published during those periods (correlation analysis)

### 4. Content Strategy Analysis

> Admin says "which content type performs best" or "content suggestions"

Group by content theme (Pillar) and calculate average engagement rate:

| Theme | Post Count | Avg Engagement Rate | Best Platform |
|---|---|---|---|
| Product Promotion | - | - | - |
| Industry Knowledge | - | - | - |
| Behind the Scenes | - | - | - |
| Customer Stories | - | - | - |

Output: Which content type performs best, which needs adjustment, and posting time optimization suggestions.

After analysis, write conclusions back to `## Content Strategy` in `/workspace/marketing-context.md`:
- If a certain type has significantly higher reach / engagement rate than others, update "Current Priority Type"
- Append an entry at the end of "Strategy Update Log":
  `[analytics {date}] {specific adjustment, e.g.: Reels reach is 3x Feed; updated priority type to Reels}`
- Delete the oldest entry when the log exceeds 10 entries

### 5. Full Monthly Report

> Admin says "generate monthly report" or "this month's data"

Comprehensive report combining all 4 types above, covering:
- Account growth summary per platform
- Performance ranking of all posts this month
- Content strategy analysis
- Comment sentiment trends for the month (if available)
- Next month's suggestions: content direction, posting frequency, platforms that need improvement

---

## Displaying Reports

Prefer displaying directly in the conversation; use tables for numbers and comparisons for trends (this week vs last week).

When the report exceeds one screen, ask admin whether to save as a file. After admin confirms, write to:

Path: `/workspace/analytics-reports/{YYYY-MM}/{report-type}-{YYYY-MM-DD}.md`

File naming examples:
- `summary-2024-01-15.md`
- `post-ranking-2024-01-15.md`
- `monthly-report-2024-01.md`

---

## Batch Processing Limit

A single API refresh processes a maximum of **10 posts**. After completion:

```
Refreshed data for 10 posts (23 total pending updates).
Continue fetching the remaining 13? (10 per batch)
```

If admin says "continue", process the next batch; if admin says "that's enough", generate the report with available data.

---

## Error Handling

| Error | Resolution |
|---|---|
| Platform token expired | Inform admin the platform needs to be reconnected; skip that platform's data |
| Post ID does not exist (deleted) | Mark as "deleted"; exclude from statistics |
| API rate limited | Inform admin of current restriction; suggest retrying in 15 minutes |
| post-history file does not exist | Inform admin there are no publishing records for that time period |
| All data is `-` with no API connection | Prompt that a platform must be connected before data can be fetched |
