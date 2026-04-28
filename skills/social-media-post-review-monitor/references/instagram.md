# Instagram Comment Monitoring API

---

## Fetching Comments

```
INSTAGRAM_GET_IG_MEDIA_COMMENTS(
  media_id = {post_id}
)
→ data[].id, data[].text, data[].username, data[].timestamp
```

Read post_ids from the last 30 days of posts in `/workspace/post-history/`, fetching one by one.
Only process new comments after the last patrol time (`timestamp > last patrol time`).

---

## Replying to Comments

```
INSTAGRAM_POST_IG_COMMENT_REPLIES(
  comment_id = {comment_id},
  message    = {reply content, ≤300 characters, ≤4 hashtags, ≤1 URL}
)
```

---

## Deleting Comments

Limited to spam comments on your own posts; execute after admin confirmation:

```
INSTAGRAM_DELETE_COMMENT(
  comment_id = {comment_id}
)
```

---

## Notes

- Instagram Story comments cannot be read via the API
- DMs (direct messages) are outside the scope of this tool

---

## Error Handling

| Error | Resolution |
|---|---|
| Token expired / insufficient permissions | Inform admin that Instagram needs to be reconnected; guide them to run setup |
| Invalid media_id | Skip this post and continue processing other posts |
| Reply exceeds 300 characters | Truncate and retry |
