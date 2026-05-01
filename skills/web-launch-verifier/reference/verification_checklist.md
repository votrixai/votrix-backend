# Launch Verification Checklist

Step-by-step verification for a deployed site with custom domain.

## 1. DNS Propagation

Check that DNS records resolve correctly from multiple nameservers:

```bash
# Root domain A record
dig +short A example.com
# Expected: 76.76.21.21

# WWW CNAME
dig +short CNAME www.example.com
# Expected: cname.vercel-dns.com

# Check from Google DNS
dig @8.8.8.8 +short A example.com

# Check from Cloudflare DNS
dig @1.1.1.1 +short A example.com
```

**Expected timeline**: Near-instant for Cloudflare-managed domains. Up to 48 hours for nameserver changes, but typically 15-30 minutes.

## 2. SSL Certificate

Verify HTTPS is working and certificate is valid:

```bash
# Check SSL certificate details
echo | openssl s_client -connect example.com:443 -servername example.com 2>/dev/null \
  | openssl x509 -noout -subject -dates -issuer

# Check HTTPS response headers
curl -sI "https://example.com" | head -20
```

**Expected**: Let's Encrypt certificate, valid for 90 days from issuance. Provisioning takes 1-5 minutes after DNS propagates.

## 3. HTTP to HTTPS Redirect

Verify HTTP automatically redirects to HTTPS:

```bash
curl -sI "http://example.com" | grep -i location
# Expected: Location: https://example.com/
```

## 4. Site Health

Check that all pages return HTTP 200:

```bash
# Check each page
for page in "" "/about" "/services" "/contact" "/pricing"; do
  STATUS=$(curl -s -o /dev/null -w '%{http_code}' "https://example.com${page}")
  echo "${page:-/}: $STATUS"
done
```

**Expected**: HTTP 200 for all configured pages.

## 5. Response Time

Measure page load time:

```bash
curl -s -o /dev/null -w 'DNS: %{time_namelookup}s\nConnect: %{time_connect}s\nTTFB: %{time_starttransfer}s\nTotal: %{time_total}s\n' "https://example.com"
```

**Expected**: Total time < 2 seconds for a Next.js static site.

## 6. WWW Redirect

Verify www subdomain works:

```bash
curl -sI "https://www.example.com" | head -5
# Expected: Either HTTP 200 or 301/308 redirect to root domain
```

## 7. Deferred Domain (Preview URL Only)

If no custom domain was configured, verify the preview URL:

```bash
curl -s -o /dev/null -w '%{http_code}' "https://project-slug-xxxx.vercel.app"
# Expected: 200
```

## Troubleshooting

### DNS not resolving
- Wait 15-30 minutes for propagation
- Verify records in Cloudflare dashboard
- Check for conflicting records (old A records)

### SSL errors
- Ensure Cloudflare proxy is set to DNS Only
- Check Vercel domain verification status
- Wait up to 10 minutes for Let's Encrypt

### 404 errors on pages
- Check Vercel deployment logs for build errors
- Verify the page exists in the deployed source
- Check next.config.js for rewrite/redirect rules

### Slow response
- Expected: < 500ms TTFB for Vercel Edge
- If slow: check if using SSR vs. static generation
- Consider: Vercel region selection, ISR configuration
