# LinkedIn Analytics API

---

## Post Performance (Organization Page)

```
LINKEDIN_GET_SHARE_STATS(
  organizational_entity = "urn:li:organization:{org_id}",
  time_intervals        = "(timeRange:(start:{start_ms},end:{end_ms}),timeGranularityType:DAY)"
  # Timestamps are millisecond-level epoch; omitting time_intervals returns all-time cumulative data
)
→ impressionCount, clickCount, likeCount, commentCount, shareCount
```

`org_id` is read from `## Connected Platforms > LinkedIn` in `/workspace/marketing-context.md`.

**Note:** This endpoint returns aggregated data for all content on the organization page; it cannot be broken down by individual post.  
Per-post data is not currently supported by the Composio LinkedIn toolset; only aggregated data can be used to analyze overall trends.

---

## Account Follower Count

```
LINKEDIN_GET_NETWORK_SIZE(
  edgeType = "COMPANY_FOLLOWED_BY_MEMBER"
)
→ followerCountsByAssociationType (follower count)
```

---

## Page View Data

```
LINKEDIN_GET_ORG_PAGE_STATS(
  organization       = "urn:li:organization:{org_id}",
  timeRangeStart     = {start_ms},   # millisecond-level epoch, optional
  timeRangeEnd       = {end_ms},     # millisecond-level epoch, optional
  timeGranularityType = "DAY"        # DAY / MONTH, optional
)
→ pageViews, uniqueVisitors, customButtonClicks
```

---

## Limitations

LinkedIn Analytics currently only supports the organization page dimension, with no per-post breakdown. When analyzing:
- Use aggregated data to assess overall content performance trends
- Combine with publishing frequency and content types from post-history for correlation analysis

---

## Error Handling

| Error | Resolution |
|---|---|
| Token expired / insufficient permissions | Inform admin that LinkedIn needs to be reconnected; skip that platform's data |
| 429 rate limit | LinkedIn shared OAuth rate limiting is strict; suggest retrying later |
| Invalid org_id | Verify that the LinkedIn org_id format in marketing-context.md is correct |
