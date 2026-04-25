# LinkedIn 发布 API

---

## 前置：获取 Author URN

发布前需要 author URN，从 `/workspace/marketing-context.md` 的 `## 已连接平台 → LinkedIn` 读取。

- 个人账号：`urn:li:person:{person_id}`
- 公司主页：`urn:li:organization:{org_id}`

如需获取：
```
LINKEDIN_GET_MY_INFO()
→ 返回 person_id

LINKEDIN_GET_COMPANY_INFO(role="ADMINISTRATOR")
→ 返回 organization_id
```

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

`LINKEDIN_CREATE_LINKED_IN_POST` 支持直接传图片 URL 数组，内部自动处理上传：

```
LINKEDIN_CREATE_LINKED_IN_POST(
  author      = "urn:li:organization:{org_id}",
  commentary  = {正文},
  images      = [{url: {image_url}, alt_text: ""}],  # 1–20 张
  visibility  = "PUBLIC",
  lifecycleState = "PUBLISHED"
)
→ data = ugcPost URN
```

如 `images` 参数不支持直接传 URL，则走两步流程：

```
Step 1 — 初始化上传：
LINKEDIN_INITIALIZE_IMAGE_UPLOAD(
  owner = "urn:li:organization:{org_id}"
)
→ upload_url, image_urn

Step 2 — 上传图片（PUT 请求到 upload_url，传图片二进制）

Step 3 — 创建帖子：
LINKEDIN_CREATE_LINKED_IN_POST(
  author     = "urn:li:organization:{org_id}",
  commentary = {正文},
  images     = [{id: image_urn}],
  visibility = "PUBLIC"
)
→ data = ugcPost URN
```

---

## Document Carousel（PDF 轮播）

当前 Composio LinkedIn 工具集中**不包含 PDF 上传工具**，无法通过 API 自动发布 Document Carousel。

处理方式：告知 admin「LinkedIn Document Carousel 需要手动在 LinkedIn 平台上传 PDF 发布，已为你准备好分页大纲（见草稿文件的 `## 分页大纲` 字段）」。

---

## Video Post

```
LINKEDIN_CREATE_LINKED_IN_POST(
  author      = "urn:li:organization:{org_id}",
  commentary  = {正文},
  visibility  = "PUBLIC",
  lifecycleState = "PUBLISHED"
  # 视频上传需通过 LinkedIn Video API，当前 Composio 工具集暂不支持
)
```

视频发布如 Composio 不支持，告知 admin 需手动在 LinkedIn 上传视频。

---

## Article

Article 使用 LinkedIn 独立编辑器，**不走普通发布 API**，告知 admin 需手动在 LinkedIn 平台排版发布。草稿文件的 `## 正文大纲` 包含完整内容结构供参考。

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
| 图片上传失败 | 确认图片 URL 可公开访问，格式为 JPEG/PNG |
| 内容违反平台政策 | 返回 LinkedIn 原始错误，建议修改后重试 |
