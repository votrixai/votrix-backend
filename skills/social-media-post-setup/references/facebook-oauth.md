# Facebook OAuth Setup

Facebook uses OAuth 2.0 via Facebook Login. The Composio `FACEBOOK` toolkit handles auth and provides access to Pages, posts, reviews, and insights.

---

## Prerequisites

The admin needs:
- A Facebook account with **admin or editor access** to the business's Facebook Page
- If no Page exists yet, ask them to create one at facebook.com/pages/create before proceeding

---

## Step 1 — Initiate Facebook Connection

调用 `manage_connections(toolkit="facebook")`，检查连接状态：

- 返回 `connected: true` → 已连接，跳到 Step 2
- 返回 `connected: false` + `redirect_url` → 把链接发给 admin：

> 「点击这个链接授权 Facebook 访问权限：[redirect_url]」

授权页面上需要勾选 **Pages** 权限，提醒 admin 注意确认。等 admin 完成后，再次调用 `manage_connections(toolkit="facebook")` 确认 `connected: true`，再继续。

---

## Step 2 — Select the Facebook Page

调用对应的 Facebook 工具，列出 admin 管理的 Pages。

展示列表给 admin：只有一个 Page 就直接确认；多个的话让 admin 选。

记录：
- `page_id`
- `page_name`

---

## Step 3 — 写入 marketing-context.md

将 Page 信息写入 `/workspace/marketing-context.md` 的 `## 已连接平台 → Facebook` 部分：

```
### Facebook
- 启用：true
- 主页名称：{page_name}
- Page ID：{page_id}
```

---

## What Facebook Can Do After Connection

| Capability | Available |
|---|---|
| Publish posts to Page | Yes |
| Publish posts with images/video | Yes |
| Read Page reviews and ratings | Yes |
| Reply to reviews | Yes |
| Read Page insights (reach, impressions, engagement) | Yes |
| Read follower / Page like count | Yes |
| Read post-level performance | Yes |
| Manage Facebook Ads | No — use FACEBOOKADS toolkit separately |
