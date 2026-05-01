# Vercel DNS Requirements

DNS records required to connect a custom domain to a Vercel deployment.

## Required Records

### Root Domain (example.com)

| Type | Name | Value | Proxy | TTL |
|------|------|-------|-------|-----|
| A | @ | 76.76.21.21 | DNS Only (grey cloud) | Auto |

### WWW Subdomain (www.example.com)

| Type | Name | Value | Proxy | TTL |
|------|------|-------|-------|-----|
| CNAME | www | cname.vercel-dns.com | DNS Only (grey cloud) | Auto |

## Cloudflare Proxy Compatibility

### Recommended: DNS Only (Grey Cloud)
- Set `proxied: false` on all records
- Vercel handles SSL via Let's Encrypt
- Vercel's global CDN serves the traffic
- Simplest configuration, fewest issues

### Alternative: Proxied (Orange Cloud)
If using Cloudflare proxy (e.g., for WAF or additional caching):
- Set SSL mode to **Full (Strict)** in Cloudflare dashboard
- Enable **Always Use HTTPS**
- Vercel and Cloudflare both terminate SSL — Full (Strict) ensures the connection between them is also encrypted
- May cause SSL handshake issues if not configured correctly

## Vercel Domain Verification

After adding DNS records:

1. Add the domain to the Vercel project via the Vercel API/dashboard
2. Vercel will check DNS propagation automatically
3. Once verified, Vercel provisions an SSL certificate via Let's Encrypt
4. SSL provisioning typically takes 1-5 minutes after DNS propagates

### Verification TXT Record (if needed)

Vercel may require a TXT record for domain verification:

| Type | Name | Value |
|------|------|-------|
| TXT | _vercel | verification-token-from-vercel |

This is only needed if Vercel can't verify ownership via A/CNAME records.

## DNS Propagation

- Cloudflare DNS updates are typically near-instant (< 5 minutes)
- If the domain was just added to Cloudflare (nameserver change), propagation can take up to 24-48 hours
- Use `dig` to check propagation from multiple nameservers:
  ```bash
  dig @8.8.8.8 +short A example.com
  dig @1.1.1.1 +short A example.com
  dig @ns1.cloudflare.com +short A example.com
  ```

## Troubleshooting

### SSL Certificate Not Provisioning
- Ensure DNS records are set to DNS Only (not proxied)
- Check that the domain is verified in Vercel
- Wait up to 10 minutes for Let's Encrypt issuance
- Check Vercel project domains page for error messages

### "Domain Not Verified" in Vercel
- Verify A record points to `76.76.21.21`
- Check for conflicting DNS records (old A records, conflicting CNAMEs)
- Try adding the verification TXT record

### WWW Not Working
- Ensure CNAME record for `www` points to `cname.vercel-dns.com`
- Check that both root and www are added to the Vercel project
- Vercel automatically handles www → root redirect (or vice versa)
