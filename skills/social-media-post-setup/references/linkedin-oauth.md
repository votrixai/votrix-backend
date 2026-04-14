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

用 `tool_search("composio manage connections linkedin")` 找到 OAuth 发起工具，启动 LinkedIn 授权流程。

The tool returns an authorization URL. Send it to the admin:

> "To connect LinkedIn, please open this link and authorize access: [url]"

LinkedIn may ask which permissions to grant — the admin should approve all requested scopes. Wait for confirmation before proceeding.

---

## Step 2 — Retrieve Connected Account Details

Search for an action to get the connected profile and any associated Company Pages:

```
tool_search("linkedin get profile")
tool_search("linkedin get organization")
```

Execute and retrieve:
- `linkedin_person_id` (personal profile)
- `linkedin_organization_id` (Company Page, if applicable)
- `company_name`

If the admin wants Company Page posting, confirm `linkedin_organization_id` is present. If it's missing, they may not have Page admin access — guide them to check their role in LinkedIn Page settings.

---

## Step 3 — 写入 marketing-context.md

将账号信息写入 `user-files/marketing-context.md` 的 `## 已连接平台 → LinkedIn` 部分：

```
### LinkedIn
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
