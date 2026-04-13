# Yelp OAuth Setup

Yelp uses OAuth 2.0 for business owner access. The Composio `YELP` toolkit provides access to reviews and the ability to respond on behalf of the business.

---

## Important: What Yelp Allows

Yelp is a review platform, not a social publishing platform. The API does **not** support creating or scheduling posts. What it does support:

- Reading customer reviews
- Responding to reviews
- Reading aggregate rating and review count
- Reading business profile data

---

## Prerequisites

The admin needs:
- A **Yelp Business Account** (claim their business at biz.yelp.com if not done yet)
- Admin access to the Yelp business listing

If the business isn't claimed on Yelp, stop and guide the admin to claim it first — responses are not possible on unclaimed listings.

---

## Step 1 — Initiate Yelp Connection

用 `tool_search("composio manage connections yelp")` 找到 OAuth 发起工具，启动 Yelp 授权流程。

The tool returns an authorization URL. Send it to the admin:

> "To connect Yelp, please open this link and authorize access with your Yelp Business account: [url]"

Wait for the admin to confirm before proceeding.

---

## Step 2 — Verify Business Listing

After authorization, search for an action to retrieve the connected business details:

```
tool_search("yelp get business")
```

Execute and confirm:
- `yelp_business_id`
- `business_name`
- `rating` (current aggregate)
- `review_count`

---

## Step 3 — 写入 marketing-context.md

将商家信息写入 `user-files/marketing-context.md` 的 `## 已连接平台 → Yelp` 部分：

```
### Yelp
- 商家名称：{business_name}
- Business ID：{yelp_business_id}
```

---

## What Yelp Can Do After Connection

| Capability | Available |
|---|---|
| Read reviews (all, filtered by rating/date) | Yes |
| Respond to reviews | Yes |
| Read aggregate rating and review count | Yes |
| Read business profile info | Yes |
| Post content / promotions | No — Yelp does not support this via API |
| Delete reviews | No — Yelp does not allow this |
