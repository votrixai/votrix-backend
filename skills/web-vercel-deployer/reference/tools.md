# Web Vercel Deployer — Tool Reference

## Vercel

### VERCEL_CREATE_PROJECT2

Create a new Vercel project linked to a GitHub repository.

```
VERCEL_CREATE_PROJECT2(
  name = "my-site",
  framework = "nextjs",
  gitRepository = { repo: "votrix-site-deploys/my-site", type: "github" }
)
→ data.id = project_id
→ data.name = project_name
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Project name (URL-safe, lowercase) |
| `framework` | string | No | Framework preset: `"nextjs"`, `"gatsby"`, `"hugo"`, `"nuxtjs"`, `"svelte"`, etc. |
| `gitRepository` | object | Yes | `{ repo: "org/repo-name", type: "github" }` |

---

### VERCEL_GET_DEPLOYMENT

Poll deployment status. Use this to wait for a deployment to finish building.

```
VERCEL_GET_DEPLOYMENT(
  idOrUrl = "dpl_abc123"
)
→ data.readyState = "QUEUED" | "BUILDING" | "READY" | "ERROR" | "CANCELED"
→ data.url = preview_url
→ data.id = deployment_id
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `idOrUrl` | string | Yes | Deployment ID (e.g., `dpl_abc123`) or deployment URL |

**Status flow:** `QUEUED` → `BUILDING` → `READY` or `ERROR`

Poll every 10-15 seconds until `readyState` is `READY` or `ERROR`.

---

### VERCEL_ADD_ENVIRONMENT_VARIABLE

Set environment variables on a Vercel project.

```
VERCEL_ADD_ENVIRONMENT_VARIABLE(
  projectId = "prj_abc123",
  key = "NEXT_PUBLIC_API_URL",
  value = "https://api.example.com",
  type = "plain",
  target = ["production", "preview"]
)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `projectId` | string | Yes | Vercel project ID |
| `key` | string | Yes | Environment variable name |
| `value` | string | Yes | Environment variable value |
| `type` | string | No | `"plain"` (default), `"secret"`, or `"encrypted"` |
| `target` | array | No | Deployment targets: `"production"`, `"preview"`, `"development"` |

---

### VERCEL_GET_DEPLOYMENT_EVENTS2

Get build logs for a deployment. Useful for debugging failed builds.

```
VERCEL_GET_DEPLOYMENT_EVENTS2(
  idOrUrl = "dpl_abc123"
)
→ data = [{ type, created, payload: { text } }, ...]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `idOrUrl` | string | Yes | Deployment ID or deployment URL |

---

### VERCEL_ADD_PROJECT_DOMAIN

Add a custom domain to a Vercel project. Also used for www redirect setup.

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
| `domain` | string | Yes | Domain to add (e.g., `"example.com"` or `"www.example.com"`) |
| `redirect` | string | No | Target domain for redirect (e.g., `"example.com"`) |
| `statusCode` | integer | No | Redirect status code: `301` (temporary) or `308` (permanent) |

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

### VERCEL_GET_DOMAIN_CONFIG

Get the DNS configuration status for a domain from Vercel's perspective.

```
VERCEL_GET_DOMAIN_CONFIG(
  domain = "example.com"
)
→ data.configuredBy = "CNAME" | "A" | null
→ data.acceptedChallenges = [...]
→ data.misconfigured = true | false
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `domain` | string | Yes | Domain to check |

---

### VERCEL_CREATE_DEPLOYMENT

Create a new deployment or redeploy an existing one. Use when environment variables are changed and a redeployment is needed.

```
VERCEL_CREATE_DEPLOYMENT(
  name = "my-site",
  project = "prj_abc123",
  target = "production",
  deploymentId = "dpl_abc123"
)
→ data.id = new_deployment_id
→ data.readyState = "QUEUED"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Project name |
| `project` | string | No | Project ID (overrides `name` for targeting) |
| `target` | string | No | `"production"`, `"staging"`, or omit for preview |
| `deploymentId` | string | No | Existing deployment ID to redeploy |
| `forceNew` | string | No | `"1"` to force a new deployment even if similar exists |

---

## Error Codes

| Code | Meaning |
|------|---------|
| 401 | Invalid or expired Vercel token |
| 403 | Insufficient permissions on the Vercel team/project |
| 404 | Project or deployment not found |
| 409 | Domain already added to another project |
| 422 | Invalid parameters |
| 429 | Rate limited — back off and retry |
| 500 | Server error — retry with backoff |
