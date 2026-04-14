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

调用 `COMPOSIO_MANAGE_CONNECTIONS`，app 设为 `INSTAGRAM`，发起授权流程。

工具会返回一个授权链接，发给 admin：

> 「点击这个链接授权 Instagram 访问权限：[url]」

等 admin 完成后再继续。

---

## Step 2 — Verify Connection

授权完成后，通过 Composio Instagram 工具获取账号详情，检索：
- `instagram_account_id`
- `username`
- `account_type`（确认是 BUSINESS 或 CREATOR，不是 PERSONAL）

如果 `account_type` 是 PERSONAL，停止并告诉 admin：
> 「Instagram API 只支持企业号或创作者账号。请在 Instagram 设置里切换账号类型后重试。」

---

## Step 3 — 写入 marketing-context.md

将账号信息写入 `/workspace/marketing-context.md` 的 `## 已连接平台 → Instagram` 部分：

```
### Instagram
- 启用：true
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
