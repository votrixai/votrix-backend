---
name: web-domain-manager
description: "Connect customer's Cloudflare account via OAuth and verify their domain zone. Triggered after preview is approved, or when the user says 'connect domain', 'setup domain', 'add domain'."
integrations:
  - cloudflare
---

# Web Domain Manager

Connect the customer's Cloudflare account and verify their domain zone so DNS records can be created.

**Architecture note:** Vercel is Votrix's own account (no customer auth needed). Cloudflare is the customer's account, connected via OAuth.

---

## Startup Check

Read `/workspace/preview_feedback.json`:

1. Confirm `approved_for_domain_setup` is `true` — if not, tell the user to complete the preview review first

Read `/workspace/project_brief.json`:

1. Get `domain_preference` and `domain_name`
2. If `domain_preference` is `"skip_domain"`:
   - Save `/workspace/domain_config.json` with `domain_source: "skipped"` and all other fields empty
   - Tell the user the site will remain on the Vercel preview URL
   - Skip all phases below and hand off directly to `web-launch-verifier` (which will run deferred-domain verification only)

---

## Phase 1 — Cloudflare OAuth Connection

Refer to `/mnt/skills/web-domain-manager/reference/tools.md` for tool slugs.

Call `COMPOSIO_MANAGE_CONNECTIONS(toolkits=["cloudflare"])` to check connection status.

- If connected: proceed to Phase 2
- If not connected: present the OAuth redirect URL to the customer and wait for them to authorize

```
To connect your domain, I need access to your Cloudflare account.

Please click this link to authorize:
{oauth_redirect_url}

Let me know once you have completed the authorization.
```

---

## Phase 2 — Get Account ID

Call `CLOUDFLARE_LIST_ACCOUNTS()` to retrieve the customer's Cloudflare account ID.

Store the `account_id` for subsequent calls.

---

## Phase 3 — Find Domain Zone

Call `CLOUDFLARE_LIST_ZONES(name={domain_name})` to search for the customer's domain.

### Zone found and status is `"active"`

Proceed to Phase 4 (save config).

### Zone found but status is `"pending"`

Tell the customer their nameservers need updating:

```
Your domain {domain_name} is in Cloudflare but the zone is pending activation.

Please update your nameservers at your domain registrar to:
  - {nameserver_1}
  - {nameserver_2}

Nameserver changes can take up to 24 hours to propagate.
Let me know once you have updated them and I will re-check.
```

### Zone not found

Offer to add the domain to Cloudflare:

```
I could not find {domain_name} in your Cloudflare account.
Would you like me to add it?
```

If the customer agrees, call `CLOUDFLARE_CREATE_ZONE(name={domain_name}, type="full")`.

Then instruct the customer to update nameservers at their registrar to point to Cloudflare.

---

## Phase 4 — Save Domain Config

Save `/workspace/domain_config.json` (schema: `/mnt/skills/web-domain-manager/reference/domain_config.schema.json`):

| Field | Value |
|-------|-------|
| `domain` | The domain name |
| `domain_source` | `"cloudflare"` |
| `account_id` | Cloudflare account ID |
| `zone_id` | Cloudflare zone ID |
| `zone_status` | `"active"`, `"pending"`, or `"initializing"` |
| `nameservers` | Array of Cloudflare nameservers assigned to the zone |
| `connected_at` | ISO 8601 timestamp |

---

## Error Handling

| Error | Action |
|-------|--------|
| Cloudflare not connected | Show the OAuth redirect URL and wait for authorization |
| Domain not found in Cloudflare | Offer to add the domain via `CLOUDFLARE_CREATE_ZONE` |
| Zone status is `"pending"` | Guide the customer to update nameservers at their registrar |
| `CLOUDFLARE_LIST_ACCOUNTS` returns empty | Customer's Cloudflare account may not have any zones yet — proceed to create one |
| OAuth token expired | Ask customer to re-authorize via `COMPOSIO_MANAGE_CONNECTIONS` |

---

## Handoff

On successful zone verification (status `"active"`), hand off to **web-dns-binder** to create DNS records.
