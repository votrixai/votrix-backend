# Web Launch Verifier — Tool Reference

## Vercel

### VERCEL_GET_DOMAIN_CONFIG

Get the DNS configuration status for a domain from Vercel's perspective. Use to confirm Vercel recognizes the domain as properly configured.

```
VERCEL_GET_DOMAIN_CONFIG(
  domain = "example.com"
)
→ data.configuredBy = "CNAME" | "A" | null
→ data.acceptedChallenges = [{ type, domain, value }]
→ data.misconfigured = true | false
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `domain` | string | Yes | Domain to check configuration for |

**Response fields:**

| Field | Description |
|-------|-------------|
| `configuredBy` | How the domain is pointed: `"A"` (A record), `"CNAME"`, or `null` (not configured) |
| `acceptedChallenges` | SSL verification challenges accepted by the domain |
| `misconfigured` | `true` if DNS records do not match Vercel's expectations |

---

## Bash Verification Commands

The following standard Unix commands are used for DNS, SSL, and HTTP verification. They run in the agent sandbox and do not require Composio.

| Command | Purpose | Example |
|---------|---------|---------|
| `dig +short A {domain} @{resolver}` | DNS propagation check | `dig +short A example.com @8.8.8.8` → `76.76.21.21` |
| `openssl s_client -connect {domain}:443 -servername {domain}` | SSL certificate verification | Check issuer, validity dates |
| `curl -sI http://{domain}` | HTTP redirect check | Expect 301/308 → https |
| `curl -s -o /dev/null -w "%{http_code}" https://{domain}/` | Site health (status code) | Expect 200 |
| `curl -s -o /dev/null -w "%{time_starttransfer}" https://{domain}/` | TTFB measurement | Expect < 500ms |

---

## Error Codes

| Code | Meaning |
|------|---------|
| 401 | Invalid or expired Vercel token |
| 404 | Domain not found in Vercel |
| 429 | Rate limited — back off and retry |
| 500 | Server error — retry with backoff |
