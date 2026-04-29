# Instagram 发布 API

---

## 发布前检查配额

每日上限 25 条，发布前先确认剩余配额：

```
INSTAGRAM_GET_IG_USER_CONTENT_PUBLISHING_LIMIT(
  ig_user_id = {ig_user_id}
)
→ quota_usage（今日已用）、config.quota_total（上限，通常 25）
```

超出配额时告知 admin 剩余等待时间，不尝试发布。

---

## Single Feed（单图）

```
Step 1 — 创建媒体容器：
INSTAGRAM_POST_IG_USER_MEDIA(
  ig_user_id  = {ig_user_id},
  image_url   = {public_url},   # 必须是直链 HTTPS，不能带 query string
  caption     = {文案 + hashtag}
)
→ data.id = creation_id

Step 2 — 发布：
INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH(
  ig_user_id  = {ig_user_id},
  creation_id = {creation_id}
)
→ data.id = post_id（媒体 ID，写入 post-history）
```

---

## Carousel（多图轮播）

使用 `INSTAGRAM_CREATE_CAROUSEL_CONTAINER` 一步创建，直接传图片 URL 数组，无需逐张创建子容器：

```
Step 1 — 创建 Carousel 容器（含所有图片）：
INSTAGRAM_CREATE_CAROUSEL_CONTAINER(
  ig_user_id       = {ig_user_id},
  child_image_urls = [{url_1}, {url_2}, ...],  # 2–10 张，按顺序排列
  caption          = {文案 + hashtag}
)
→ data.id = creation_id

Step 2 — 发布：
INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH(
  ig_user_id  = {ig_user_id},
  creation_id = {creation_id}
)
→ data.id = post_id
```

**注意：**
- 图片必须同一比例（建议 1:1），JPEG 格式，最大 8MB
- 所有 URL 必须可公开访问，不能是带认证参数的 signed URL
- 容器在 24 小时内过期，创建后尽快发布

---

## Reels

```
Step 1 — 创建 Reels 容器：
INSTAGRAM_POST_IG_USER_MEDIA(
  ig_user_id    = {ig_user_id},
  video_url     = {public_video_url},  # MP4，直链
  caption       = {简短文案 + 3–5 个 hashtag},
  media_type    = "REELS",
  share_to_feed = true,                # 同时出现在 Feed tab
  cover_url     = {封面图 url}         # 可选，不含 query string
)
→ data.id = creation_id

Step 2 — 发布（视频需要处理时间，工具会自动等待）：
INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH(
  ig_user_id       = {ig_user_id},
  creation_id      = {creation_id},
  max_wait_seconds = 120              # 视频处理最长等 120s
)
→ data.id = post_id
```

**注意：**
- 视频比例必须 9:16，MP4 格式
- `max_wait_seconds` 至少设 60，视频处理需要时间
- 不能用带 query string 的 signed URL

---

## Story

```
Step 1 — 创建 Story 容器：
INSTAGRAM_POST_IG_USER_MEDIA(
  ig_user_id = {ig_user_id},
  image_url  = {public_url},   # 9:16 比例
  media_type = "STORIES"
)
→ data.id = creation_id

Step 2 — 发布：
INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH(
  ig_user_id  = {ig_user_id},
  creation_id = {creation_id}
)
→ data.id = post_id
```

**注意：** 互动贴纸（Poll / Question）不支持，需在 IG App 内手动添加。

---

## 链接处理

正文链接不可点击，改写为「链接在主页 Bio」。

---

## 错误处理

| 错误 | 处理方式 |
|---|---|
| 超出 25 posts/日配额 | 调 `GET_CONTENT_PUBLISHING_LIMIT` 确认，告知 admin 建议明天发布 |
| error 9007（容器未 FINISHED） | `PUBLISH` 工具已内置等待，若仍报错则重新创建容器 |
| 容器已过期（>24h） | 重新调 `POST_IG_USER_MEDIA` 创建新容器，原 creation_id 不可复用 |
| image_url 无法访问 | 确认 URL 是直链 HTTPS，不带 query string，可被 Meta 服务器访问 |
| 图片格式/尺寸不符 | 告知具体要求（JPEG、比例 4:5–1.91:1、最大 8MB） |
| token 过期 | 告知 admin 需重新连接 Instagram，引导运行 setup |
