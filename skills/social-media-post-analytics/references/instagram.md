# Instagram Analytics API

---

## Account-Level Data

```
INSTAGRAM_GET_USER_INSIGHTS(
  ig_user_id = {ig_user_id},
  metric     = ["reach", "impressions", "profile_views", "follower_count"],
  period     = "week"   # day / week / month
)
→ data[].name, data[].values (time series)
```

`ig_user_id` is read from `## Connected Platforms > Instagram` in `/workspace/marketing-context.md`.

---

## Single Post Performance

```
INSTAGRAM_GET_IG_MEDIA_INSIGHTS(
  media_id = {post_id},
  metric   = ["reach", "impressions", "likes", "comments", "shares", "saved"]
)
→ data[].name, data[].values
```

Engagement Rate = (likes + comments + shares + saved) / reach x 100%

---

## Notes

- Story insights can only be fetched within 24 hours of publishing; data becomes unavailable after that
- Reels `reach` and `impressions` may be significantly higher than regular Feed posts; distinguish content types when analyzing

---

## Refresh Flow

Read post_ids from the last 30 days of posts in `/workspace/post-history/`, calling the single post endpoint one by one.  
Process a maximum of 10 per batch; ask whether to continue after completion.

---

## Error Handling

| Error | Resolution |
|---|---|
| Token expired / insufficient permissions | Inform admin that Instagram needs to be reconnected; skip that platform's data |
| media_id does not exist (deleted) | Mark as "deleted"; exclude from statistics |
| Story data unavailable (past 24h) | Record as "data expired"; do not retry |
| API rate limited | Inform admin; suggest retrying in 15 minutes |
