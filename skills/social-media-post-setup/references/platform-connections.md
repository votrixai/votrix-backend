# Platform Connection Reference

The connection flow is the same for every platform: call `manage_connections(toolkit="<name>")` → check status → guide authorization → record account information.

---

## Facebook

```python
manage_connections(toolkit="facebook")
```

- `connected: false` → Send `redirect_url` to admin, remind them to check the **Pages** permission
- After connecting: list Pages → let admin choose → record `page_id`, `page_name`

Write to marketing-context.md:
```
### Facebook
- Enabled: true
- Page Name: {page_name}
- Page ID: {page_id}
```

Can do: publish posts (including images/videos), read comments/ratings, reply to comments, read Page insights

---

## Instagram

Prerequisite: Requires an Instagram Business/Creator account that is linked to a Facebook Page.

```python
manage_connections(toolkit="instagram")
```

After connecting, obtain: `instagram_account_id`, `username`, `account_type`

- If `account_type` is PERSONAL, stop and prompt admin to switch to a business account

Write to marketing-context.md:
```
### Instagram
- Enabled: true
- Username: {username}
- Account ID: {instagram_account_id}
```

Can do: publish image/video posts, read insights, read/reply to comments

---

## LinkedIn

```python
manage_connections(toolkit="linkedin")
```

After connecting, obtain: `linkedin_person_id`, `linkedin_organization_id` (company Page), `company_name`

Write to marketing-context.md:
```
### LinkedIn
- Enabled: true
- Company Name: {company_name}
- Organization ID: {linkedin_organization_id}
- Person ID: {linkedin_person_id}
```

Can do: publish posts as personal or company Page (text/images/videos/PDF carousels), read insights

---

## Twitter / X

```python
manage_connections(toolkit="twitter")
```

After connecting, obtain: `twitter_user_id`, `username`

Write to marketing-context.md:
```
### Twitter
- Enabled: true
- Username: {username}
- User ID: {twitter_user_id}
```

Can do: publish tweets (including media), publish Threads, read analytics

---

## Yelp

Yelp is not a posting platform — it only supports review management. Use `tool_search("composio manage connections yelp")` to find the authorization tool and initiate the connection.

After connecting, obtain: `yelp_business_id`, `business_name`

Write to marketing-context.md:
```
### Yelp
- Business Name: {business_name}
- Business ID: {yelp_business_id}
```

Can do: read reviews, reply to reviews, read overall ratings | Cannot do: publish content/posts
