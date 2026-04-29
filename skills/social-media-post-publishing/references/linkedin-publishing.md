# LinkedIn 发布 API

---

## 前置：获取 Author URN

发布前需要 author URN，从 `/workspace/marketing-context.md` 的 `## 已连接平台 → LinkedIn` 读取。

- 个人账号：`urn:li:person:{person_id}`
- 公司主页：`urn:li:organization:{org_id}`

---

## Text Post（纯文字）

```
LINKEDIN_CREATE_LINKED_IN_POST(
  author      = "urn:li:organization:{org_id}",
  commentary  = {正文，每 1–2 句换行，最多 3000 字},
  visibility  = "PUBLIC",
  lifecycleState = "PUBLISHED"
)
→ data = ugcPost URN（post_id，写入 post-history）
```

**注意：**
- 正文不放链接，链接发布后放第一条评论（见下方「链接处理」）

---

## Image Post（图文）

**必须走两步流程**——先用 `upload_file` 把图片传到 Composio 的 S3，再发帖：

```
Step 1 — 上传图片到 Composio S3：
upload_file(
  file_path    = "/mnt/session/outputs/{图片文件名}",  # 必须在 outputs/
  toolkit_slug = "linkedin",
  tool_slug    = "LINKEDIN_CREATE_LINKED_IN_POST"
)
→ 返回 {s3key, name, mimetype}

注意：image_generate 生成的图片在 /mnt/session/uploads/，需先复制到 outputs/：
bash(command='cp /mnt/session/uploads/{generated_xxx.jpeg} /mnt/session/outputs/{filename.jpeg}')

Step 2 — 创建帖子，images 里用 Step 1 返回的 s3key、name、mimetype：
LINKEDIN_CREATE_LINKED_IN_POST(
  author         = "urn:li:organization:{org_id}",
  commentary     = {正文},
  images         = [{s3key: "{s3key}", name: "{name}", mimetype: "{mimetype}"}],
  visibility     = "PUBLIC",
  lifecycleState = "PUBLISHED"
)
→ data = ugcPost URN（post_id，写入 post-history）
```

**注意：** images 参数只接受 `{s3key, name, mimetype}`，不能用 URL 或 URN。

---

## Document Carousel（PDF 轮播）

不支持。

---

## Video Post

不支持。

---

## Article

不支持。

---

## 链接处理

LinkedIn 算法对正文含外链的帖子降低触达，处理方式：

```
Step 1 — 发布帖子正文（不含链接）

Step 2 — 发布后立即在帖子下发评论，将链接放第一条评论：
LINKEDIN_CREATE_COMMENT_ON_POST(
  actor      = "urn:li:organization:{org_id}",
  object     = {ugcPost_urn},   # 刚发布的帖子 URN
  target_urn = {ugcPost_urn},
  message    = {text: "链接：{url}"}
)
```

---

## 错误处理

| 错误 | 处理方式 |
|---|---|
| token 过期 / 权限不足 | 告知 admin 需重新连接 LinkedIn，引导运行 setup |
| 429 rate limit | LinkedIn 共享 OAuth app 限流严格，建议稍后重试，或提示 admin 使用自有 OAuth 凭证 |
| 正文超过 3000 字 | 截短至 3000 字，告知 admin |
| upload_file 失败 | 检查 file_path 是否在 /mnt/session/outputs/；image_generate 的图片需先 cp 到 outputs/ |
| LINKEDIN_CREATE_LINKED_IN_POST 图片 404 | 确认 images 参数用的是 upload_file 返回的 s3key，不是 URL 或 URN |
| 内容违反平台政策 | 返回 LinkedIn 原始错误，建议修改后重试 |
