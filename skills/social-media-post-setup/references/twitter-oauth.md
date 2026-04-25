# Twitter / X OAuth Setup

Twitter uses OAuth 2.0 with PKCE. The Composio `TWITTER` toolkit handles the full auth flow.

---

## Prerequisites

The admin needs:
- A Twitter/X account (personal or brand account)
- For posting on behalf of a brand: they should be logged into the brand account before authorizing

---

## Step 1 — Initiate Twitter Connection

调用 `manage_connections(toolkit="twitter")`，检查连接状态：

- 返回 `connected: true` → 已连接，跳到 Step 2
- 返回 `connected: false` + `redirect_url` → 把链接发给 admin：

> 「点击这个链接授权 Twitter/X 访问权限：[redirect_url]」

等 admin 完成后，再次调用 `manage_connections(toolkit="twitter")` 确认 `connected: true`，再继续。

---

## Step 2 — Verify Connection

授权完成后，通过 Composio Twitter 工具获取账号详情，检索：
- `twitter_user_id`
- `username`（@handle）
- `name`（显示名称）

---

## Step 3 — 写入 marketing-context.md

将账号信息写入 `/workspace/marketing-context.md` 的 `## 已连接平台 → Twitter` 部分：

```
### Twitter
- 启用：true
- 用户名：{username}
- User ID：{twitter_user_id}
```

---

## What Twitter Can Do After Connection

| Capability | Available |
|---|---|
| Post tweets (text) | Yes |
| Post tweets with media | Yes |
| Post threads | Yes (sequential tweets) |
| Delete tweets | Yes |
| Read tweet analytics (impressions, engagements) | Yes — via Twitter API v2 |
| Read follower count | Yes |
| Read mentions and replies | Yes |
| Schedule tweets natively | No — agent handles timing |

---

## Twitter API Rate Limits (relevant to us)

- **Free tier**: 1,500 tweets/month write limit
- **Basic tier**: 3,000 tweets/month
- Post at most 1–3 times per day to stay well within limits and avoid appearing spammy
