# Web DNS Binder — Tool Reference

## Cloudflare

### CLOUDFLARE_LIST_DNS_RECORDS

List DNS records in a Cloudflare zone. Use to check for existing or conflicting records before creating new ones.

```
CLOUDFLARE_LIST_DNS_RECORDS(
  zone_id = "zone_abc123"
)
→ data.result = [{ id, type, name, content, proxied, ttl, created_on, modified_on }, ...]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `zone_id` | string | Yes | Cloudflare zone ID |
| `type` | string | No | Filter by record type: `"A"`, `"AAAA"`, `"CNAME"`, `"MX"`, `"TXT"`, etc. |
| `name` | string | No | Filter by record name (e.g., `"example.com"`, `"www.example.com"`) |

---

### CLOUDFLARE_CREATE_DNS_RECORD

Create a new DNS record in a Cloudflare zone.

```
CLOUDFLARE_CREATE_DNS_RECORD(
  zone_id = "zone_abc123",
  type = "A",
  name = "@",
  content = "76.76.21.21",
  proxied = false,
  ttl = 1
)
→ data.result = { id, type, name, content, proxied, ttl }
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `zone_id` | string | Yes | Cloudflare zone ID |
| `type` | string | Yes | Record type: `"A"`, `"AAAA"`, `"CNAME"`, `"MX"`, `"TXT"`, etc. |
| `name` | string | Yes | Record name: `"@"` for root, `"www"` for subdomain |
| `content` | string | Yes | Record value (IP address, hostname, etc.) |
| `proxied` | boolean | No | `true` = orange cloud (Cloudflare proxy), `false` = grey cloud (DNS-only). **Must be `false` for Vercel** |
| `ttl` | integer | No | TTL in seconds. `1` = automatic |

---

### CLOUDFLARE_UPDATE_DNS_RECORD

Update an existing DNS record in a Cloudflare zone.

```
CLOUDFLARE_UPDATE_DNS_RECORD(
  zone_id = "zone_abc123",
  dns_record_id = "rec_abc123",
  type = "A",
  name = "@",
  content = "76.76.21.21",
  proxied = false,
  ttl = 1
)
→ data.result = { id, type, name, content, proxied, ttl }
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `zone_id` | string | Yes | Cloudflare zone ID |
| `dns_record_id` | string | Yes | ID of the DNS record to update |
| `type` | string | Yes | Record type |
| `name` | string | Yes | Record name |
| `content` | string | Yes | New record value |
| `proxied` | boolean | No | `true` = orange cloud, `false` = grey cloud. **Must be `false` for Vercel** |
| `ttl` | integer | No | TTL in seconds. `1` = automatic |

---

### CLOUDFLARE_DELETE_DNS_RECORD

Delete a DNS record from a Cloudflare zone. Use to remove conflicting records before creating new ones.

```
CLOUDFLARE_DELETE_DNS_RECORD(
  zone_id = "zone_abc123",
  dns_record_id = "rec_abc123"
)
→ data.result = { id }
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `zone_id` | string | Yes | Cloudflare zone ID |
| `dns_record_id` | string | Yes | ID of the DNS record to delete |

---

## Vercel

### VERCEL_ADD_PROJECT_DOMAIN

Add a custom domain to a Vercel project.

```
VERCEL_ADD_PROJECT_DOMAIN(
  idOrName = "prj_abc123",
  domain = "example.com"
)
→ data.name = domain
→ data.verified = true | false
```

For www redirect:

```
VERCEL_ADD_PROJECT_DOMAIN(
  idOrName = "prj_abc123",
  domain = "www.example.com",
  redirect = "example.com",
  statusCode = 308
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `idOrName` | string | Yes | Vercel project ID or project name |
| `domain` | string | Yes | Domain to add |
| `redirect` | string | No | Target domain for redirect |
| `statusCode` | integer | No | Redirect status code: `301` or `308` |

---

### VERCEL_VERIFY_PROJECT_DOMAIN

Verify domain ownership for a Vercel project.

```
VERCEL_VERIFY_PROJECT_DOMAIN(
  idOrName = "prj_abc123",
  domain = "example.com"
)
→ data.verified = true | false
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `idOrName` | string | Yes | Vercel project ID or project name |
| `domain` | string | Yes | Domain to verify |

---

## Error Codes

| Code | Meaning |
|------|---------|
| 401 | Invalid or expired token |
| 403 | Insufficient permissions |
| 404 | Zone, record, or project not found |
| 409 | Domain already added to another Vercel project |
| 422 | Invalid parameters |
| 429 | Rate limited — back off and retry |
| 500 | Server error — retry with backoff |
