# Twitter Analytics API

---

## Single Post Performance

```
TWITTER_GET_POST_ANALYTICS(
  ids        = [{tweet_id}],   # up to 100, passed in batch
  start_time = {YYYY-MM-DDTHH:mm:ssZ},
  end_time   = {YYYY-MM-DDTHH:mm:ssZ},
  granularity = "total"        # hourly / daily / weekly / total
)
→ data[].impression_count, like_count, retweet_count, reply_count, quote_count
```

Read tweet_ids from the last 30 days of tweets in `/workspace/post-history/`, passed in batch (up to 100 per request).

---

## Account Follower Count

```
TWITTER_USER_LOOKUP_ME()
→ data.public_metrics.followers_count, data.public_metrics.following_count
```

---

## Notes

- `impression_count` only works for your own account's tweets; returns 0 when searching others' tweets
- For Threads, only the first tweet's tweet_id is recorded; analytics also only fetches the first tweet's data to represent the entire Thread

---

## Error Handling

| Error | Resolution |
|---|---|
| Token expired | Inform admin that Twitter needs to be reconnected; skip that platform's data |
| tweet_id does not exist (deleted) | Mark as "deleted"; exclude from statistics |
| API rate limited (429) | Inform admin; suggest retrying in 15 minutes |
