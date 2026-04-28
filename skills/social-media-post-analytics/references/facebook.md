# Facebook Analytics API

---

## Account-Level Data

```
FACEBOOK_GET_PAGE_INSIGHTS(
  page_id = {page_id},
  metric  = ["fans", "page_impressions", "page_engaged_users"],
  period  = "week"   # day / week / month
)
→ data[].name, data[].values (time series)
```

- `fans`: Net follower growth
- `page_impressions`: Total page reach
- `page_engaged_users`: Number of engaged users

---

## Single Post Performance

```
FACEBOOK_GET_POST_INSIGHTS(
  post_id = {post_id},
  metric  = ["post_impressions", "post_reactions_by_type_total", "post_clicks"]
)
→ data[].name, data[].values
```

- `post_impressions`: Number of people reached
- `post_reactions_by_type_total`: Count of each reaction type (like/love/haha/wow/sad/angry)
- `post_clicks`: Post click count

Total engagement = sum of all reactions + comment count + share count.

---

## Refresh Flow

Read post_ids from the last 30 days of posts in `/workspace/post-history/`, calling the single post endpoint one by one.  
Process a maximum of 10 per batch; ask whether to continue after completion.

---

## Error Handling

| Error | Resolution |
|---|---|
| Token expired / insufficient permissions | Inform admin that Facebook needs to be reconnected; skip that platform's data |
| post_id does not exist (deleted) | Mark as "deleted"; exclude from statistics |
| API rate limited | Inform admin; suggest retrying in 15 minutes |
