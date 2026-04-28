# Facebook Comment Monitoring API

---

## Fetching Comments

```
FACEBOOK_GET_COMMENTS(
  post_id = {post_id}
)
→ data[].id, data[].message, data[].from, data[].created_time
```

Read post_ids from the last 30 days of posts in `/workspace/post-history/`, fetching one by one.
Only process new comments after the last patrol time (`created_time > last patrol time`).

---

## Replying to Comments

```
FACEBOOK_CREATE_COMMENT(
  post_id = {post_id},
  message = {reply content}
)
```

---

## Deleting Comments

Limited to spam comments on your own page; execute after admin confirmation:

```
FACEBOOK_DELETE_COMMENT(
  comment_id = {comment_id}
)
```

---

## Error Handling

| Error | Resolution |
|---|---|
| Token expired / insufficient permissions | Inform admin that Facebook needs to be reconnected; guide them to run setup |
| Invalid post_id | Skip this post and continue processing other posts |
