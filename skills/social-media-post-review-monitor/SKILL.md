---
name: social-media-post-review-monitor
description: "Monitor and reply to post comments across platforms (Facebook, Instagram, Twitter). Triggered when admin says 'check comments', 'any new comments', 'reply to bad reviews', 'customer feedback', 'customer messages', or 'reviews'."
integrations:
  - facebook
  - instagram
  - twitter
---

# Review Monitor

You are responsible for monitoring customer comments on posts across platforms, summarizing sentiment trends, and drafting replies for admin to confirm before submitting.

---

## Startup Check

Read `/workspace/marketing-context.md`:
- Confirm connected platforms
- Read `## Operational Status` for each platform's last patrol time and last processed ID to determine where to start fetching new data

---

## Data Sources

Read post records from the last 30 days from `/workspace/post-history/` to obtain each post's post_id.

Based on connected platforms, read the corresponding reference files to execute API calls:

| Platform | Reference File |
|---|---|
| Facebook | `/workspace/skills/social-media-post-review-monitor/references/facebook.md` |
| Instagram | `/workspace/skills/social-media-post-review-monitor/references/instagram.md` |
| Twitter | `/workspace/skills/social-media-post-review-monitor/references/twitter.md` |

Each platform is fetched independently; a failure on one does not affect the others.

---

## Sentiment Classification

Classify all new comments by sentiment:

| Category | Criteria |
|---|---|
| Positive | Praise, gratitude, expressions of appreciation |
| Neutral | General remarks, questions |
| Negative | Complaints, dissatisfaction, bad reviews |

Extract recurring themes: flag any issue that appears 2 or more times separately, for example:
> ⚠️ 3 comments mention "wait time too long"

---

## Topic Signal Write-back

After sentiment classification, if recurring themes are found (same issue appears 2+ times), write the signal to `## Content Strategy > Recent Key Topics` in `/workspace/marketing-context.md`:

```
- {date} [review] {topic description} ({N} comments mentioned) > Suggestion: {content action recommendation}
```

Examples:
```
- 2024-01-15 [review] Customers asking about business hours (3 comments) > Suggestion: Create a pinned Story with business hours
- 2024-01-18 [review] Multiple mentions of parking inconvenience (2 comments) > Suggestion: Post proactively about nearby parking locations
```

Keep a maximum of 5 entries; delete the oldest one when exceeded. Update the `Recent Key Topics > Last Updated` timestamp.

---

## Displaying Comments

Display in priority order:

1. **Negative comments** — highest priority
2. **Neutral comments**
3. **Positive comments**

Each comment shows: Platform / Author / Time / Content / Draft Reply

---

## Drafting Replies

Generate a draft reply for each comment, incorporating the brand tone from `/workspace/marketing-context.md`:

| Type | Strategy |
|---|---|
| Praise | Thank + brief acknowledgment, keep it warm and friendly |
| Question | Answer directly; if information is insufficient, invite them to DM |
| Complaint | Apologize + invite them to DM for resolution; never argue in public comments |
| Spam | Suggest admin delete it; do not reply |

**Rule: Draft replies must be confirmed by admin; never submit automatically.**

See detailed reply templates at `/workspace/skills/social-media-post-review-monitor/references/response-templates.md`.

---

## Admin Confirmation and Reply Submission

After displaying drafts, wait for admin:
- **Confirm**: Submit the reply
- **Edit**: Update the draft, then confirm again
- **Skip**: Mark as "reviewed, no reply for now"
- **Delete comment** (Facebook / Instagram only): Execute delete action after confirmation; Twitter does not allow deleting others' comments

See each platform's reference file for reply / delete API details.

---

## Writing Records

After each batch of comments is processed:

**1. Update `## Operational Status` in `/workspace/marketing-context.md`**

Update each platform's last patrol time and last processed ID.

**2. Write to review-history**

Path: `/workspace/review-history/{YYYY-MM}/{YYYY-MM-DD}.md`

```markdown
## {HH:MM} | {Platform} | Comment

- **Author:** {author}
- **Content:** {original text}
- **Sentiment:** Positive / Neutral / Negative
- **Reply Status:** Replied / Skipped / Pending
- **Reply Content:** {submitted reply, if any}

---
```

**3. Update comment count in post-history** (if there are new comments)

Read the corresponding date's post-history file and update the `Comments: -` field to the actual count.

---

## Sentiment Report

When admin says "generate a comment report" or "how are this month's comments":

Read records from `/workspace/review-history/` for the specified time range and generate:

- Total comment count per platform + positive / neutral / negative ratios
- Frequently mentioned positive keywords (great service, fast delivery, etc.)
- Frequently mentioned negative keywords (wait time, expensive, etc.)
- List of unreplied comments (need follow-up)
- Actionable suggestions (e.g., "4 negative reviews this month mentioned long weekend wait times; consider adding weekend staff")
