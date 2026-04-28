# Facebook Publishing API

---

## Prerequisite: Obtain Page ID

`page_id` is read from `## Connected Platforms → Facebook` in `/workspace/marketing-context.md`.
To verify, you can call:

```
FACEBOOK_LIST_MANAGED_PAGES()
→ Returns data[].id (page_id) and data[].name
```

---

## Feed Post — Text Only / Link

```
FACEBOOK_CREATE_POST(
  page_id   = {page_id},
  message   = {body text},
  link      = {link url},   # Optional, auto-generates preview card
  published = true
)
→ data.id = post_id (format: pageId_postId)
```

**Notes:**
- At least one of `message` or `link` must be provided
- Including a link auto-generates a preview card; the body text does not need to repeat the link content
- Hashtags have weak effect on Facebook; just place them at the end of the body text

---

## Feed Post — With Image

```
FACEBOOK_CREATE_PHOTO_POST(
  page_id   = {page_id},
  url       = {image_public_url},  # Direct HTTPS link, cannot be an HTML page
  message   = {body text + hashtag},
  published = true
)
→ data.id = post_id (format: pageId_postId)
```

**Notes:**
- `url` must be a direct link to an image file, returning the correct MIME type (image/jpeg or image/png)
- Redirect URLs or links requiring authentication are not supported

---

## Reels / Video

```
FACEBOOK_CREATE_VIDEO_POST(
  page_id     = {page_id},
  file_url    = {video_public_url},  # Direct MP4 link, H.264 + AAC encoding
  description = {short copy},
  title       = {video title},       # Optional
  published   = true
)
→ data.id = post_id
```

**Notes:**
- `file_url` must be a direct MP4 link; links to YouTube or other player pages are not accepted
- After uploading, the video enters a processing state and becomes visible to users only after processing is complete
- Facebook Reels and Instagram Reels can use the same video asset

---

## Story

Not supported.

---

## Error Handling

| Error | How to Handle |
|---|---|
| Token expired / insufficient permissions | Inform admin they need to reconnect Facebook, guide them to run setup |
| Image URL inaccessible | Confirm URL is a direct HTTPS link returning the correct MIME type |
| Video format not supported | Suggest using MP4 + H.264/AAC, inform admin to provide again |
| Publishing failed (network/rate limit) | Keep draft, suggest retrying later |
| Content violates platform policy | Return Facebook's original error message, suggest modifying and retrying |
