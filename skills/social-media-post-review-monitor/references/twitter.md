# Twitter Comment Monitoring API

---

## Fetching Mentions / Replies

Twitter does not support fetching reply lists directly by tweet_id. Instead, use full-text search to capture @mentions:

```
TWITTER_FULL_ARCHIVE_SEARCH(
  query       = "@{twitter_handle}",
  start_time  = {last patrol time, ISO 8601, e.g. 2024-01-15T10:00:00Z},
  max_results = 50
)
→ data[].id, data[].text, data[].author_id, data[].created_at
```

`twitter_handle` is read from `## Connected Platforms > Twitter` in `/workspace/marketing-context.md`.

Filter out tweets from your own account (`author_id` = own account ID); only process @mentions and replies from others.

---

## Replying to Tweets

```
TWITTER_CREATION_OF_A_POST(
  text                       = {reply content, ≤280 characters},
  reply_in_reply_to_tweet_id = {original tweet id}
)
```

---

## Notes

- Cannot delete others' tweets; spam comments can only be left without a reply
- Twitter API has rate limits; patrol intervals should be no shorter than 6 hours

---

## Error Handling

| Error | Resolution |
|---|---|
| Token expired | Inform admin that Twitter needs to be reconnected; guide them to run setup |
| Search returns empty | Normal situation, no new mentions; skip silently |
| Reply exceeds 280 characters | Truncate and retry |
| Rate limited (429) | Record current progress; continue on next patrol |
