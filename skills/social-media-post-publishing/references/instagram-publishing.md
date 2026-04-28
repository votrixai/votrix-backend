# Instagram Publishing API

---

## Pre-Publish Quota Check

Daily limit is 25 posts. Confirm remaining quota before publishing:

```
INSTAGRAM_GET_IG_USER_CONTENT_PUBLISHING_LIMIT(
  ig_user_id = {ig_user_id}
)
→ quota_usage (used today), config.quota_total (limit, usually 25)
```

When quota is exceeded, inform admin of remaining wait time; do not attempt to publish.

---

## Single Feed (single image)

```
Step 1 — Create media container:
INSTAGRAM_POST_IG_USER_MEDIA(
  ig_user_id  = {ig_user_id},
  image_url   = {public_url},   # Must be a direct HTTPS link, no query string
  caption     = {copy + hashtag}
)
→ data.id = creation_id

Step 2 — Publish:
INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH(
  ig_user_id  = {ig_user_id},
  creation_id = {creation_id}
)
→ data.id = post_id (media ID, write to post-history)
```

---

## Carousel (multi-image carousel)

Use `INSTAGRAM_CREATE_CAROUSEL_CONTAINER` to create in one step, passing the image URL array directly without creating individual child containers:

```
Step 1 — Create Carousel container (with all images):
INSTAGRAM_CREATE_CAROUSEL_CONTAINER(
  ig_user_id       = {ig_user_id},
  child_image_urls = [{url_1}, {url_2}, ...],  # 2–10 images, in order
  caption          = {copy + hashtag}
)
→ data.id = creation_id

Step 2 — Publish:
INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH(
  ig_user_id  = {ig_user_id},
  creation_id = {creation_id}
)
→ data.id = post_id
```

**Notes:**
- Images must have the same aspect ratio (1:1 recommended), JPEG format, max 8MB
- All URLs must be publicly accessible; signed URLs with authentication parameters are not allowed
- Containers expire within 24 hours; publish as soon as possible after creation

---

## Reels

```
Step 1 — Create Reels container:
INSTAGRAM_POST_IG_USER_MEDIA(
  ig_user_id    = {ig_user_id},
  video_url     = {public_video_url},  # MP4, direct link
  caption       = {short copy + 3–5 hashtags},
  media_type    = "REELS",
  share_to_feed = true,                # Also appears in Feed tab
  cover_url     = {cover image url}    # Optional, no query string
)
→ data.id = creation_id

Step 2 — Publish (video requires processing time, tool will auto-wait):
INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH(
  ig_user_id       = {ig_user_id},
  creation_id      = {creation_id},
  max_wait_seconds = 120              # Max wait 120s for video processing
)
→ data.id = post_id
```

**Notes:**
- Video aspect ratio must be 9:16, MP4 format
- `max_wait_seconds` should be set to at least 60; video processing takes time
- Signed URLs with query strings cannot be used

---

## Story

```
Step 1 — Create Story container:
INSTAGRAM_POST_IG_USER_MEDIA(
  ig_user_id = {ig_user_id},
  image_url  = {public_url},   # 9:16 aspect ratio
  media_type = "STORIES"
)
→ data.id = creation_id

Step 2 — Publish:
INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH(
  ig_user_id  = {ig_user_id},
  creation_id = {creation_id}
)
→ data.id = post_id
```

**Note:** Interactive stickers (Poll / Question) are not supported; they must be added manually in the IG App.

---

## Link Handling

Links in the body text are not clickable; rewrite as "Link in bio".

---

## Error Handling

| Error | How to Handle |
|---|---|
| Exceeded 25 posts/day quota | Call `GET_CONTENT_PUBLISHING_LIMIT` to confirm, inform admin and suggest publishing tomorrow |
| Error 9007 (container not FINISHED) | `PUBLISH` tool has built-in waiting; if it still errors, recreate the container |
| Container expired (>24h) | Call `POST_IG_USER_MEDIA` again to create a new container; original creation_id cannot be reused |
| image_url inaccessible | Confirm URL is a direct HTTPS link, no query string, accessible by Meta servers |
| Image format/dimensions do not meet requirements | Inform of specific requirements (JPEG, aspect ratio 4:5–1.91:1, max 8MB) |
| Token expired | Inform admin they need to reconnect Instagram, guide them to run setup |
