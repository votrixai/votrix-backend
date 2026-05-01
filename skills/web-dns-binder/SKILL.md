---
name: web-dns-binder
description: "Create DNS records in customer's Cloudflare zone and add domain to Vercel project. Triggered after domain zone is verified."
integrations:
  - cloudflare
  - vercel
---

# Web DNS Binder

Create the required DNS records in the customer's Cloudflare zone and register the domain with the Vercel project.

---

## Startup Check

Read `/workspace/domain_config.json`:

1. Confirm `zone_status` is `"active"` — if not, hand back to `web-domain-manager` to complete zone verification
2. Extract `zone_id` and `domain`

Read `/workspace/deployment.json`:

1. Extract `project_id` for the Vercel project

---

## Phase 1 — Check Existing DNS Records

Refer to `/mnt/skills/web-dns-binder/reference/tools.md` for tool slugs and `/mnt/skills/web-dns-binder/reference/vercel_dns_requirements.md` for DNS record specifications.

Call `CLOUDFLARE_LIST_DNS_RECORDS(zone_id={zone_id})` to check for existing A or CNAME records at the root (`@`) and `www` subdomain.

If conflicting records exist:
- Call `CLOUDFLARE_UPDATE_DNS_RECORD` to modify them in place, or
- Call `CLOUDFLARE_DELETE_DNS_RECORD` to remove them, then create new ones

---

## Phase 2 — Create DNS Records

### Root domain A record

```
CLOUDFLARE_CREATE_DNS_RECORD(
  zone_id = "{zone_id}",
  type = "A",
  name = "@",
  content = "76.76.21.21",
  proxied = false,
  ttl = 1
)
```

**CRITICAL:** `proxied` must be `false` (DNS-only, grey cloud) so that Vercel handles SSL via Let's Encrypt. If proxied is enabled, SSL provisioning will fail.

### WWW subdomain CNAME record

```
CLOUDFLARE_CREATE_DNS_RECORD(
  zone_id = "{zone_id}",
  type = "CNAME",
  name = "www",
  content = "cname.vercel-dns.com",
  proxied = false,
  ttl = 1
)
```

---

## Phase 3 — Add Domain to Vercel

Add the root domain:

```
VERCEL_ADD_PROJECT_DOMAIN(
  idOrName = "{project_id}",
  domain = "{domain}"
)
```

Add the www redirect (www -> root, 308 permanent redirect):

```
VERCEL_ADD_PROJECT_DOMAIN(
  idOrName = "{project_id}",
  domain = "www.{domain}",
  redirect = "{domain}",
  statusCode = 308
)
```

---

## Phase 4 — Verify Domain in Vercel

Call `VERCEL_VERIFY_PROJECT_DOMAIN(idOrName={project_id}, domain={domain})` to verify domain ownership.

If verification fails, check that DNS records were created correctly and retry.

---

## Phase 5 — Confirm DNS Records

Call `CLOUDFLARE_LIST_DNS_RECORDS(zone_id={zone_id})` to verify that both records were created successfully:

| Record | Type | Name | Content | Proxied |
|--------|------|------|---------|---------|
| Root | A | `@` | `76.76.21.21` | `false` (DNS-only) |
| WWW | CNAME | `www` | `cname.vercel-dns.com` | `false` (DNS-only) |

---

## Phase 6 — Save DNS Records

Save `/workspace/dns_records.json` (schema: `/mnt/skills/web-dns-binder/reference/dns_records.schema.json`):

| Field | Value |
|-------|-------|
| `domain` | The domain name |
| `zone_id` | Cloudflare zone ID |
| `records` | Array of created DNS records with `record_id`, `type`, `name`, `content`, `proxied`, `ttl` |
| `vercel_domain_added` | `true` |
| `vercel_domain_verified` | `true` or `false` |
| `www_redirect` | `{ redirect: "{domain}", statusCode: 308 }` |
| `created_at` | ISO 8601 timestamp |

---

## Error Handling

| Error | Action |
|-------|--------|
| DNS conflict with existing records | Update or delete old records before creating new ones |
| Vercel domain verification fails | Check DNS records are correct, wait a few minutes, retry verification |
| Zone not active | Hand back to `web-domain-manager` to resolve zone status |
| `CLOUDFLARE_CREATE_DNS_RECORD` fails | Check for duplicate records, resolve conflicts, retry |
| Vercel project not found | Re-read `deployment.json` and verify project ID |

---

## Handoff

On successful DNS setup and domain verification, hand off to **web-launch-verifier** to verify propagation, SSL, and site health.
