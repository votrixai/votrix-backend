# LinkedIn OAuth Setup

LinkedIn uses OAuth 2.0. The Composio `LINKEDIN` toolkit supports both Company Page posting and personal profile posting.

---

## Prerequisites

The admin needs:
- A LinkedIn account
- For business posting: **Super Admin or Content Admin access** to the company's LinkedIn Page
- If no Company Page exists: ask them to create one at linkedin.com/company/setup/new

Clarify with the admin upfront:
> "Do you want to post from your company's LinkedIn Page, your personal profile, or both?"

This determines which permissions to request during OAuth.

---

## Step 1 — Initiate LinkedIn Connection

调用 `manage_connections(toolkit="linkedin")`，检查连接状态：

- 返回 `connected: true` → 已连接，跳到 Step 2
- 返回 `connected: false` + `redirect_url` → 把链接发给 admin：

> 「点击这个链接授权 LinkedIn 访问权限：[redirect_url]」

LinkedIn 授权页面会列出需要的权限范围，让 admin 全部批准。等 admin 完成后，再次调用 `manage_connections(toolkit="linkedin")` 确认 `connected: true`，再继续。

---

## Step 2 — Retrieve Connected Account Details

通过 Composio LinkedIn 工具获取已连接的个人资料和公司主页信息，检索：
- `linkedin_person_id`（个人账号）
- `linkedin_organization_id`（公司 Page，如适用）
- `company_name`

如果 admin 需要用公司 Page 发帖，但 `linkedin_organization_id` 为空，说明账号可能没有 Page 管理权限——引导他去 LinkedIn Page 设置里确认自己的角色。

---

## Step 3 — 写入 marketing-context.md

将账号信息写入 `/workspace/marketing-context.md` 的 `## 已连接平台 → LinkedIn` 部分：

```
### LinkedIn
- 启用：true
- 公司名称：{company_name}
- Organization ID：{linkedin_organization_id}
- Person ID：{linkedin_person_id}
```

---

## What LinkedIn Can Do After Connection

| Capability | Available |
|---|---|
| Post text updates (personal profile) | Yes |
| Post text updates (Company Page) | Yes |
| Post with images | Yes |
| Post with video | Yes |
| Post documents / carousels (PDF) | Yes |
| Read post impressions and engagement | Yes |
| Read follower count (Company Page) | Yes |
| Read follower demographics | Yes (Company Page, limited) |
| Send InMail / DMs | No — not available via API |

---

## LinkedIn API Notes

- LinkedIn enforces a **Community Management API** requirement for posting — Composio handles this, but posting limits may apply
- Recommended frequency: **3–5 posts per week** for Company Pages, up to daily for personal profiles
- Carousel posts require uploading a PDF document via the media upload action before posting
