# Web Domain Manager — Tool Reference

## Cloudflare

### CLOUDFLARE_LIST_ACCOUNTS

Get the customer's Cloudflare account IDs.

```
CLOUDFLARE_LIST_ACCOUNTS()
→ data.result = [{ id, name, type }, ...]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| (none) | — | — | No parameters required |

---

### CLOUDFLARE_LIST_ZONES

Find domain zones in the customer's Cloudflare account.

```
CLOUDFLARE_LIST_ZONES(
  name = "example.com"
)
→ data.result = [{ id, name, status, name_servers, account: { id, name } }, ...]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | Filter by exact domain name (e.g., `"example.com"`) |
| `status` | string | No | Filter by zone status: `"active"`, `"pending"`, `"initializing"` |
| `account_id` | string | No | Filter by Cloudflare account ID |

**Zone status values:**
- `"active"` — nameservers are pointed to Cloudflare, zone is live
- `"pending"` — zone added but nameservers not yet updated
- `"initializing"` — zone is being set up

---

### CLOUDFLARE_CREATE_ZONE

Add a new domain zone to the customer's Cloudflare account.

```
CLOUDFLARE_CREATE_ZONE(
  name = "example.com",
  type = "full",
  account_id = "abc123"
)
→ data.result = { id, name, status, name_servers }
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Domain name to add (e.g., `"example.com"`) |
| `type` | string | No | Zone type: `"full"` (default, full DNS management) or `"partial"` (CNAME setup) |
| `account_id` | string | Yes | Cloudflare account ID to add the zone to |
| `jump_start` | boolean | No | Automatically scan for existing DNS records (default: `true`) |

---

## Connection Management

### COMPOSIO_MANAGE_CONNECTIONS

Check or initiate OAuth connections for integrations.

```
COMPOSIO_MANAGE_CONNECTIONS(
  toolkits = ["cloudflare"]
)
→ data.connected = true | false
→ data.redirect_url = "https://..." (if not connected)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `toolkits` | array | Yes | List of toolkit names to check/connect (e.g., `["cloudflare"]`) |

---

## Error Codes

| Code | Meaning |
|------|---------|
| 401 | Invalid or expired Cloudflare token — re-authorize via OAuth |
| 403 | Insufficient permissions on the Cloudflare account |
| 404 | Zone or account not found |
| 409 | Zone already exists in another account |
| 422 | Invalid parameters (e.g., invalid domain format) |
| 429 | Rate limited — back off and retry |
| 500 | Server error — retry with backoff |
