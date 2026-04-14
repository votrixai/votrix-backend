---
name: social-media-post-publishing
description: "发布或定时发布内容到已连接的社交平台。当 admin 说「发布」「发帖」「定时发」「发到 Instagram」「发到 Facebook」「发到 Twitter」「发到 LinkedIn」「post」「schedule」时触发。生成内容见 03-content-creator。"
integrations:
  - facebook
  - instagram
  - twitter
  - linkedin
---

# Social Publisher

你负责将内容准确发布到对应平台，并将发布记录存入 `user-files/post-history/`，供 analytics 后续分析使用。

---

## 启动检查

读取 `user-files/marketing-context.md`：
- 确认 `## 已连接平台` 里目标平台有 Page ID / Account ID
- 未连接的平台 → 告知 admin 需先运行 setup 连接该平台，跳过该平台继续其他

---

## 获取待发布内容

**从 content-creator 直接衔接**
内容已在对话 context 中，直接进入发布流程。

**Admin 指定草稿**
用 `glob("user-files/drafts/*.md")` 列出所有草稿，展示给 admin 选择，读取对应文件。

**Admin 提供现成文案**
直接用 admin 给的内容，询问目标平台。

---

## 图片处理

内容带图片时，发布前先调 `image_upload` 上传到 Supabase Storage 拿公开 URL：

```
image_upload(storage_path="...", user_id="...")
→ 返回 public_url
```

---

## 链接处理

| 平台 | 处理方式 |
|---|---|
| Facebook | 正文直接放链接，自动生成预览卡 |
| Twitter | 链接放正文末尾，固定占 23 字 |
| LinkedIn | 正文末尾写「链接见评论」，发布后把链接发到第一条评论 |
| Instagram | 正文链接不可点击，改写为「链接在主页 Bio」 |

---

## 各平台发布

### Facebook

```
# 纯文字或带链接
tool_search("facebook create post")
→ FACEBOOK_CREATE_POST
  传入：page_id、message、link（如有）
  返回：post_id

# 带图片
tool_search("facebook create photo post")
→ FACEBOOK_CREATE_PHOTO_POST
  传入：page_id、url（public_url）、message
  返回：post_id

# 多图
tool_search("facebook upload photos batch")
→ FACEBOOK_UPLOAD_PHOTOS_BATCH 批量上传
→ FACEBOOK_CREATE_POST 附带 photo_ids
  返回：post_id
```

### Instagram

Instagram 发布是强制两步流程：

**单图 / 视频 / Reels：**
```
step 1 — 创建 media container
tool_search("instagram post ig user media")
→ INSTAGRAM_POST_IG_USER_MEDIA
  传入：ig_user_id（account_id）、image_url（public_url）、caption
  返回：creation_id

step 2 — 等待处理完成（status = FINISHED）后发布
tool_search("instagram publish ig user media")
→ INSTAGRAM_PUBLISH_IG_USER_MEDIA
  传入：ig_user_id、creation_id
  返回：post_id（media_id）
```

**Carousel（多图，2–10 张）：**
```
step 1 — 为每张图创建子 container（重复 N 次）
→ INSTAGRAM_POST_IG_USER_MEDIA
  传入：image_url、is_carousel_item=true
  返回：child_creation_id

step 2 — 等所有子 container 达到 FINISHED 状态

step 3 — 创建 carousel container
tool_search("instagram create carousel container")
→ INSTAGRAM_CREATE_CAROUSEL_CONTAINER
  传入：ig_user_id、children=[child_creation_ids]、caption
  返回：carousel_creation_id

step 4 — 发布
→ INSTAGRAM_PUBLISH_IG_USER_MEDIA
  传入：ig_user_id、creation_id=carousel_creation_id
  返回：post_id
```

**限制提醒：** Instagram API 每 24 小时最多发布 25 篇帖子。发布前用 `INSTAGRAM_GET_IG_USER_CONTENT_PUBLISHING_LIMIT` 检查当日剩余配额，不足时告知 admin。

### Twitter

```
# 有图片时先上传 media
tool_search("twitter upload media")
→ 上传图片，返回 media_id

# 发推
tool_search("twitter create tweet")
→ 传入：text、media_ids（如有）
  返回：tweet_id
```

### LinkedIn

```
# 有图片时先注册上传
tool_search("linkedin register image upload")
→ 返回 upload_url + asset_urn

# 用 web_fetch 或 bash_tool PUT 图片到 upload_url

# 发帖
tool_search("linkedin create post")
→ 传入：author（organization_id 或 person_id）、text、asset_urn（如有）
  返回：post_id

# 有链接时：发布成功后在第一条评论放链接
tool_search("linkedin create comment")
→ 传入：post_id、text（链接 URL）
```

---

## 定时发布

Admin 说「明天早上 9 点发」：
1. 将草稿文件里标注定时时间
2. 用 `CronCreate` 创建一次性任务，到时触发本 skill 读取该草稿发布
3. 告知 admin 定时任务已设置，并说明草稿路径

---

## 发布后处理

每个平台发布成功后，立即执行：

**1. 删除草稿文件**

用 `write` 把草稿文件内容清空（虚拟文件系统不支持 delete，写空内容代替）。

**2. 写入 post-history**

路径：`user-files/post-history/{YYYY-MM}/{YYYY-MM-DD}.md`

文件存在则读取后末尾追加，不存在则新建：

```markdown
## {HH:MM} | {平台} | {主题标题}

- **Post ID：** {post_id}
- **文案：** {文案前 100 字}...
- **Hashtag：** {hashtag 列表}
- **链接：** {链接，无则留空}
- **配图：** {storage_path，无则留空}
- **表现数据：**（由 analytics 填入）
  - 触达：-
  - 互动：-
  - 点赞：-
  - 评论：-
  - 分享：-

---
```

**3. 汇报结果**

```
✓ Instagram — 发布成功（post_id: xxx）
✓ Facebook  — 发布成功（post_id: xxx）
✗ Twitter   — 失败：media_id 上传超时，草稿已保留，建议稍后重试
```

各平台独立汇报，失败不影响其他平台。

---

## 错误处理

| 错误 | 处理方式 |
|---|---|
| 平台 token 过期 | 告知 admin 需重新连接该平台，引导运行 setup |
| Instagram container 处理超时 | 重新创建 container，原 creation_id 不可复用 |
| Instagram 超过 25 posts/日限额 | 告知 admin 剩余配额，建议明天发布 |
| 图片格式/尺寸不符 | 告知具体要求，等 admin 重新提供 |
| 发布失败（网络/限流） | 保留草稿，建议稍后重试 |
| 内容违反平台政策 | 返回平台原始错误信息，建议修改后重试 |
