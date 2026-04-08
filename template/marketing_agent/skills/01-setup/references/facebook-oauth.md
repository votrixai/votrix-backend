# Facebook OAuth Setup

Facebook uses OAuth 2.0 via Facebook Login. The Composio `FACEBOOK` toolkit handles auth and provides access to Pages, posts, reviews, and insights.

---

## Prerequisites

The admin needs:
- A Facebook account with **admin or editor access** to the business's Facebook Page
- If no Page exists yet, ask them to create one at facebook.com/pages/create before proceeding

---

## Step 1 — Initiate Facebook Connection

用 `tool_search("composio manage connections facebook")` 找到 OAuth 发起工具，启动 Facebook 授权流程。

The tool returns an authorization URL. Send it to the admin:

> "To connect Facebook, please open this link and authorize access: [url]"

During the Facebook authorization screen, the admin must grant permissions for **Pages** — remind them to check that box if prompted.

Wait for the admin to confirm before proceeding.

---

## Step 2 — Select the Facebook Page

After authorization, search for an action to list Pages the admin manages:

```
tool_search("facebook get pages")
```

Execute and display the list of Pages returned. If only one Page exists, confirm with the admin and proceed. If multiple Pages exist, ask the admin which one to use.

Retrieve and save:
- `page_id`
- `page_name`

---

## Step 3 — 写入 marketing-context.md

将 Page 信息写入 `user-files/marketing-context.md` 的 `## 已连接平台 → Facebook` 部分：

```
### Facebook
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
