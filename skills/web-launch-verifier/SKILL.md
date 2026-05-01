---
name: web-launch-verifier
description: "Verify DNS propagation, SSL certificate, and site health on the custom domain. Triggered after DNS records are created, or when the user says 'verify', 'check site', 'launch status'."
integrations:
  - vercel
---

# Web Launch Verifier

Verify that the site is fully live on the custom domain: DNS propagation, SSL certificate, HTTP redirects, and page health.

---

## Startup Check

Read `/workspace/dns_records.json` (or `/workspace/domain_config.json` if domain was skipped):

1. If domain was skipped (`domain_source: "skipped"`): skip to Phase 7 (preview-only verification)
2. Otherwise extract `domain` and `records`

Read `/workspace/deployment.json`:

1. Extract `preview_url` and `project_id`

---

## Phase 1 — DNS Propagation

Refer to `/mnt/skills/web-launch-verifier/reference/tools.md` for tool slugs and `/mnt/skills/web-launch-verifier/reference/verification_checklist.md` for detailed check specifications.

Run DNS lookups against public resolvers:

```
dig +short A {domain} @8.8.8.8
dig +short A {domain} @1.1.1.1
```

Expected result: `76.76.21.21`

If DNS has not propagated:
- Tell the user: "DNS changes can take 15-30 minutes to propagate, and up to 48 hours in some cases."
- Offer to re-check later

---

## Phase 2 — SSL Certificate

Run SSL check:

```
openssl s_client -connect {domain}:443 -servername {domain}
```

Verify:
- Issuer contains "Let's Encrypt" (Vercel's SSL provider)
- Certificate is valid (not expired, correct domain)
- Valid date range covers current date

If SSL is not provisioned:
- Check Vercel domain verification status via `VERCEL_GET_DOMAIN_CONFIG(domain={domain})`
- Let's Encrypt can take up to 10 minutes to provision after DNS propagates
- Tell the user to wait and offer to re-check

---

## Phase 3 — HTTP to HTTPS Redirect

Run redirect check:

```
curl -sI http://{domain}
```

Expected: HTTP 301 or 308 redirect to `https://{domain}`

---

## Phase 4 — Site Health

Curl each configured page path and verify HTTP 200:

```
curl -s -o /dev/null -w "%{http_code}" https://{domain}/
curl -s -o /dev/null -w "%{http_code}" https://{domain}/about
```

Check all pages defined in the project configuration.

---

## Phase 5 — Response Time

Measure Time to First Byte (TTFB):

```
curl -s -o /dev/null -w "%{time_starttransfer}" https://{domain}/
```

Expected: TTFB under 500ms for Vercel Edge Network.

---

## Phase 6 — WWW Redirect

Verify that `www.{domain}` resolves or redirects to the root domain:

```
curl -sI https://www.{domain}
```

Expected: 301 or 308 redirect to `https://{domain}`

---

## Phase 7 — Deferred Domain (Preview Only)

If the domain was skipped or deferred:

1. Verify the Vercel preview URL is accessible
2. Confirm HTTP 200 on the preview URL
3. Measure TTFB on the preview URL
4. Set overall status to `"deferred"`

---

## Phase 8 — Vercel Domain Status

Call `VERCEL_GET_DOMAIN_CONFIG(domain={domain})` to check Vercel's view of the domain configuration status.

Verify that Vercel reports the domain as properly configured.

---

## Phase 9 — Generate Reports

Save `/workspace/launch_report.json` (schema: `/mnt/skills/web-launch-verifier/reference/launch_report.schema.json`):

| Field | Value |
|-------|-------|
| `domain` | The domain name (or preview URL if deferred) |
| `overall_status` | `"live"`, `"partial"`, `"failed"`, or `"deferred"` |
| `checks.dns_propagation` | `{ status, expected, actual, resolvers }` |
| `checks.ssl_certificate` | `{ status, issuer, valid_from, valid_to }` |
| `checks.http_redirect` | `{ status, from, to, status_code }` |
| `checks.site_health` | `{ status, pages: [{ path, status_code }] }` |
| `checks.response_time` | `{ status, ttfb_ms }` |
| `checks.www_redirect` | `{ status, from, to, status_code }` |
| `checks.vercel_config` | `{ status, vercel_response }` |
| `verified_at` | ISO 8601 timestamp |

**Overall status logic:**
- `"live"`: all checks pass
- `"partial"`: some non-critical checks fail (e.g., www redirect)
- `"failed"`: critical checks fail (DNS, SSL, or site health)
- `"deferred"`: domain was skipped, only preview URL verified

Save `/workspace/project_summary.txt` with a human-readable summary of the launch.

---

## Phase 10 — Present Final Report

Present the results to the user:

```
Launch Report for {domain}
========================

Status: {overall_status}

Live URL:    https://{domain}
Preview URL: {preview_url}

Verification Results:
  DNS Propagation:   {pass/fail}
  SSL Certificate:   {pass/fail} — {issuer}
  HTTP → HTTPS:      {pass/fail}
  Site Health:        {pass/fail} — {N}/{total} pages OK
  Response Time:      {ttfb_ms}ms (target: <500ms)
  WWW Redirect:      {pass/fail}
  Vercel Config:     {pass/fail}

Would you like to make any changes to the site?
```

---

## Error Handling

| Error | Action |
|-------|--------|
| DNS not propagated | Tell user to wait 15-30 minutes (up to 48 hours), offer to re-check later |
| SSL not provisioned | Check Vercel verification status, wait up to 10 minutes for Let's Encrypt, retry |
| HTTP redirect missing | Check Vercel project domain configuration |
| Site returns non-200 | Check deployment status, review build logs |
| TTFB exceeds 500ms | Note in report but do not block — may be temporary |
| WWW redirect not working | Check www CNAME record in Cloudflare |
| `dns_records.json` missing | Hand back to `web-dns-binder` to complete DNS setup |

---

## Handoff

This is the **final skill** in the website-builder pipeline. There is no handoff.

Present the launch report and ask the user if they would like to make any changes to their site.
