# Generate Video

Use case: Generate or edit video content for social media (Reels / Story / short-form video).

---

## Step 1 — Context Gathering

Read `/workspace/marketing-context.md` to extract brand tone and target audience. Combine with the user's message to determine the video topic and promotional objective.

---

## Step 2 — Asset Assessment

- **User provides video assets** → Edit directly: trim to target duration, add subtitles / music / brand elements
- **No assets, AI-generated** → Generate video clips based on the topic and combine into a complete video

---

## Step 3 — Generation

Pass in: video topic, style keywords, target duration, dimensions (portrait 9:16 / square 1:1).

`negative_prompt`: `text, watermark, logo`

---

## Step 4 — Output

Call `show_post_preview`, pass the video path in slides, briefly describe the content direction in caption, and fill in hashtags based on the brand.
