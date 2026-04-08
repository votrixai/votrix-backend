# Instagram OAuth Setup

Instagram Business API runs through Facebook's Graph API. Connecting Instagram requires a Facebook Page that is linked to an Instagram Business (or Creator) Account.

---

## Prerequisites

Before starting, confirm with the admin:

1. They have an **Instagram Business or Creator Account** (not a personal account)
2. That Instagram account is **linked to a Facebook Page** they manage
   - If not linked: ask them to go to Instagram Settings → Account → Switch to Professional Account, then link their Facebook Page

---

## Step 1 — Initiate Instagram Connection

用 `tool_search("composio manage connections instagram")` 找到 OAuth 发起工具，启动 Instagram 授权流程。

The tool returns an authorization URL. Send it to the admin:

> "To connect Instagram, please open this link and authorize access: [url]"

Wait for the admin to confirm they've completed the authorization before proceeding.

---

## Step 2 — Verify Connection

After the admin confirms, search for an action to retrieve the connected Instagram account details:

```
tool_search("instagram get account")
```

Execute the action to retrieve:
- `instagram_account_id`
- `username`
- `account_type` (confirm it's BUSINESS or CREATOR, not PERSONAL)

If `account_type` is PERSONAL, stop and tell the admin:
> "Instagram's API only supports Business or Creator accounts for publishing and insights. Please switch your account type in Instagram Settings and try again."

---

## Step 3 — 写入 marketing-context.md

将账号信息写入 `user-files/marketing-context.md` 的 `## 已连接平台 → Instagram` 部分：

```
### Instagram
- 用户名：{username}
- Account ID：{instagram_account_id}
```

---

## What Instagram Can Do After Connection

| Capability | Available |
|---|---|
| Publish photo/video posts | Yes |
| Publish Stories | Limited (via Content Publishing API) |
| Read post insights (reach, impressions, engagement) | Yes |
| Read follower count and growth | Yes |
| Read comments | Yes |
| Reply to comments | Yes |
| Read DMs | No (restricted by Meta) |
