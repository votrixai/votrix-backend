# Twitter / X 发布 API

---

## 图片上传（唯一可用路径）

Twitter 支持图片发布（每条推文最多 4 张，单张 ≤ 5 MB，支持 JPEG / PNG / WEBP）。

**必须严格按以下四步执行，缺一不可：**

```
Step 0 — 确认图片在 /mnt/session/outputs/（仅对 image_generate 输出需要）：
  image_generate 的输出在 /mnt/session/uploads/，必须先复制到 /mnt/session/outputs/：
  bash: cp /mnt/session/uploads/{filename} /mnt/session/outputs/{filename}
  poster-design 生成的图片已在 /mnt/session/outputs/，跳过此步。

Step 1 — 上传到 Composio 存储（必须先执行，才能获得 s3key）：
upload_file(
  file_path    = "/mnt/session/outputs/{filename}",   # 不能是 /mnt/session/uploads/ 路径
  toolkit_slug = "twitter",
  tool_slug    = "TWITTER_UPLOAD_MEDIA"
)
→ {s3key, name, mimetype}   ← 这是 Composio 内部 s3key，不是 Supabase URL

Step 2 — 上传到 Twitter，获取 media_id：
TWITTER_UPLOAD_MEDIA(
  media          = {s3key, name, mimetype},   # Step 1 的完整返回值，原封不动传入
  media_category = "tweet_image"
)
→ data.media_id  （纯数字字符串，如 "1782345678901234567"）

Step 3 — 发推并附图：
TWITTER_CREATION_OF_A_POST(
  text            = {推文正文，≤280 字},
  media_media_ids = ["{media_id}"]
)
→ data.id = tweet_id
```

**关键限制：**
- Step 1 不可跳过：`TWITTER_UPLOAD_MEDIA` 只接受 Composio s3key，不接受 Supabase URL
- `media_id` 有效期极短，Step 2 后立即执行 Step 3
- 最多 4 张图：每张分别执行 Step 0–2，收集所有 `media_id` 后一次传入 Step 3

---

## 视频内容限制

不支持。草稿类型为「Twitter 视频」时降级处理：有配图则附图发布，无图则生成配图后附图发布。

---

## Single Tweet

```
TWITTER_CREATION_OF_A_POST(
  text            = {推文正文，≤280 字，链接占 23 字},
  media_media_ids = ["{media_id}"]   # 可选，media_id 须通过上方四步流程获取
)
→ data.id = tweet_id（写入 post-history）
```

**注意：**
- hashtag 直接写在 `text` 里（最多 1–2 个）
- 链接直接放 `text` 末尾，无论长短固定占 23 字

---

## Thread（推文串）

Thread 通过 `reply_in_reply_to_tweet_id` 串联，依次发布：

```
Step 1 — 发第 1 条（hook）：
TWITTER_CREATION_OF_A_POST(
  text = {第 1 条文案，≤280 字}
)
→ tweet_id_1

Step 2 — 发第 2 条（reply to 第 1 条）：
TWITTER_CREATION_OF_A_POST(
  text                       = {第 2 条文案，≤280 字},
  reply_in_reply_to_tweet_id = {tweet_id_1}
)
→ tweet_id_2

... 以此类推，每条 reply to 上一条

最后一条：总结 + CTA
```

**注意：**
- 每条必须 ≤280 字（链接占 23 字）
- 必须按顺序发，拿到上一条 tweet_id 才能发下一条
- post-history 记录第 1 条的 tweet_id 即可

---

## 链接处理

Twitter 链接直接放正文末尾，无论原始 URL 长短，固定占 23 字。无需特殊处理。

---

## 错误处理

| 错误 | 处理方式 |
|---|---|
| token 过期 | 告知 admin 需重新连接 Twitter，引导运行 setup |
| 推文超过 280 字 | 检查 `text` 字数，链接记为 23 字，重新截短后重试 |
| `TWITTER_UPLOAD_MEDIA` 404 / s3key 无效 | 确认先调用了 `upload_file`，使用其返回的 s3key，不要用 Supabase URL |
| `media_media_ids` 中有非数字字符串 | 检查 media_id 是纯数字（非 placeholder），重新获取后重试 |
| `media_media_ids` invalid | media_id 可能未经过 TWITTER_UPLOAD_MEDIA，或已过期，重新执行 Step 1–2 |
| 内容违反平台政策 | 返回 Twitter 原始错误信息，建议修改后重试 |
| 发布失败（网络/限流） | 保留草稿，建议稍后重试 |
