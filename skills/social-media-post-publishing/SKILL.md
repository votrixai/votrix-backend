---
name: social-media-post-publishing
description: "Publish or schedule content to connected social platforms. Triggered when admin says 'publish', 'post', 'schedule', 'post to Instagram', 'post to Facebook', 'post to Twitter', 'post to LinkedIn', 'post', 'schedule'. For content generation, see social-media-post-content-creation."
integrations:
  - facebook
  - instagram
  - twitter
  - linkedin
---

# Social Publisher

You are responsible for accurately publishing content to the corresponding platforms and saving publishing records to `/workspace/post-history/` for subsequent analytics use.

---

## Cron Daily Auto-Publish Mode

When the trigger message is `[cron] content publish`:

1. Read the `## Directives` section of `/workspace/marketing-context.md` to confirm publishing behavior (requires confirmation / publish directly)
2. Search `/workspace/drafts/` for all drafts whose filenames start with **today's date**
3. Filter drafts with status "ready to publish" and group by platform
4. Files with status "draft" (not yet confirmed by admin):
   - If directive is "requires confirmation": skip, notify admin "There are X drafts pending confirmation today"
   - If directive is "publish directly": treat as confirmed, proceed to publishing flow
5. Publish content for each platform in sequence, then execute post-publish processing (write post-history, clear drafts, report results)
6. If there are no drafts for today, exit silently without notifying admin

---

## Startup Check

Read `/workspace/marketing-context.md`:
- Confirm that the target platform has a Page ID / Account ID / ig_user_id under `## Connected Platforms`
- For unconnected platforms: inform admin they need to run setup to connect that platform first, skip and continue with other platforms

---

## Retrieve Content to Publish

**Direct handoff from content-creator**
Content is already in the conversation context; proceed directly to the publishing flow.

**Admin specifies a draft**
List all drafts under `/workspace/drafts/` for admin to choose from, then read the corresponding file.

**Admin provides ready-made copy**
Use the content provided by admin directly, and ask about the target platform and content type.

---

## Determining Publish Scope (when admin says "publish")

When admin issues a publish command without specifying a particular draft, determine scope using these rules:

**Default: only publish the nearest day**

1. Scan `/workspace/drafts/` for drafts with status "ready to publish"
2. Sort by the date in draft filenames, find the **date closest to today (including today) that is not earlier than today**
3. Only take that day's drafts into the publishing flow; drafts for other dates are not processed
4. Before publishing, inform admin: "Will publish {N} posts for {date}, across {platform list}", then execute after confirmation

**When bulk publishing is implied: confirm first**

If admin's wording clearly implies publishing multiple days or all content, for example:
- "Publish everything this week", "publish all", "publish them together", "publish everything that was created"

Do not execute directly. First confirm with admin:

> "Detected drafts for {N} days ({date range}), {X} posts total. Do you want to publish all of them, or only the nearest day ({nearest date})?"

Wait for admin's explicit reply before executing, to avoid accidental operations.

---

## Publishing

Based on the draft's `platform` + `content type` fields, read the corresponding reference file and execute the API call:

| Platform | Reference File |
|---|---|
| Instagram | `/workspace/skills/social-media-post-publishing/references/instagram-publishing.md` |
| Facebook | `/workspace/skills/social-media-post-publishing/references/facebook-publishing.md` |
| LinkedIn | `/workspace/skills/social-media-post-publishing/references/linkedin-publishing.md` |
| Twitter | `/workspace/skills/social-media-post-publishing/references/twitter-publishing.md` |

Each platform publishes independently; one failure does not affect other platforms from continuing.

---

## Post-Publish Processing

After each platform publishes successfully, execute immediately:

**1. Update draft status**

Read the draft file, change the `status` field to "published", and leave all other content unchanged.

**2. Write to post-history**

Path: `/workspace/post-history/{YYYY-MM}/{YYYY-MM-DD}.md`

If the file exists, read it and append to the end; if it does not exist, create a new one:

```markdown
## {HH:MM} | {platform} | {content type} | {topic title}

- **Post ID:** {post_id}
- **Copy:** {first 100 characters of copy}...
- **Hashtag:** {hashtag list}
- **Link:** {link, leave blank if none}
- **Image:** {public_url, leave blank if none}
- **Performance Data:** (to be filled in by analytics)
  - Reach: -
  - Engagement: -
  - Likes: -
  - Comments: -
  - Shares: -

---
```

**3. Report results**

```
✓ Instagram Reels  — Published successfully (post_id: xxx)
✓ Facebook Feed    — Published successfully (post_id: xxx)
✗ LinkedIn Text    — Failed: token expired, please reconnect LinkedIn
```

---

## Error Handling

| Error | How to Handle |
|---|---|
| Platform token expired | Inform admin they need to reconnect that platform, guide them to run setup |
| Image/video format or dimensions do not meet requirements | Inform them of the specific requirements, wait for admin to provide again |
| Publishing failed (network/rate limit) | Keep draft status as "ready to publish", suggest retrying later |
| Content violates platform policy | Return the platform's original error message, suggest modifying and retrying |

See each reference file for platform-specific error handling.
