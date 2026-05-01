---
name: web-vercel-deployer
description: "Deploy the customized site to Vercel and wait for build completion. Triggered after site customization is pushed to GitHub, or when the user says 'deploy site', 'deploy to Vercel', 'push to production', 'create deployment'."
integrations:
  - vercel
---

# Web Vercel Deployer

## Startup Check

Read `/workspace/site_config.json`:

1. Confirm the file exists and contains a valid `github_repo` and `github_url` -- if not, tell the user to run web-site-customizer first
2. Check `/workspace/pipeline_state.json` to verify web-site-customizer is in `completed_stages`

Read `/workspace/deployment.json` if it exists:
- Already has a successful deployment -- ask the user if they want to redeploy or keep the current deployment
- Has a failed deployment -- offer to retry

Refer to `/mnt/skills/web-vercel-deployer/reference/tools.md` for all Vercel tool slugs and parameters.

---

## Phase 1 -- Create Vercel Project

Call `VERCEL_CREATE_PROJECT2` to create a new Vercel project linked to the GitHub repository:

| Parameter | Value |
|-----------|-------|
| name | `{project_slug}` from site_config.json |
| framework | `nextjs` |
| gitRepository.type | `github` |
| gitRepository.repo | `votrix-site-deploys/{project_slug}` |

The Vercel project uses Votrix's pre-configured Vercel account. Do not ask the user for Vercel credentials.

If the project already exists (409 conflict), ask the user whether to use the existing project or create with a different name.

---

## Phase 2 -- Wait for Auto-Deploy

When a Vercel project is linked to a GitHub repo, Vercel automatically triggers a deployment on the latest commit. Wait for this deployment to complete.

1. Call `VERCEL_GET_DEPLOYMENT` to check the deployment status
2. Poll every 10 seconds until the status is `READY`
3. Typical build time is 30-90 seconds for Next.js projects

**Status values and actions:**

| Status | Action |
|--------|--------|
| QUEUED | Continue polling |
| BUILDING | Continue polling |
| READY | Deployment successful -- proceed to Phase 3 |
| ERROR | Deployment failed -- go to error recovery |
| CANCELED | Inform user, offer to retry |

**Timeout:** If the deployment has not completed after 5 minutes (30 polls), inform the user and offer options:
- Continue waiting (some builds take longer)
- Check build logs for issues
- Cancel and investigate

---

## Phase 3 -- Verify Deployment

Once the deployment status is `READY`:

1. Extract the preview URL from the deployment response (typically `https://{project_slug}.vercel.app`)
2. Confirm the URL is accessible
3. Record the deployment details:
   - Deployment ID
   - Project ID
   - Preview URL
   - Build duration
   - Deployment timestamp

---

## Phase 4 -- Set Environment Variables (if needed)

If the site requires environment variables (e.g. analytics ID, API keys for contact forms, CMS tokens):

1. Call `VERCEL_ADD_ENVIRONMENT_VARIABLE` for each variable
2. Variables should be set for the `production` target

Common environment variables by feature:

| Feature | Variable | Example |
|---------|----------|---------|
| analytics | NEXT_PUBLIC_GA_ID | G-XXXXXXXXXX |
| contact_form | CONTACT_FORM_ENDPOINT | https://formspree.io/f/xxxxx |
| newsletter | NEXT_PUBLIC_MAILCHIMP_URL | https://xxx.list-manage.com/... |
| chat_widget | NEXT_PUBLIC_CHAT_ID | widget-id-xxx |

If environment variables are added, trigger a redeployment by calling `VERCEL_CREATE_DEPLOYMENT` and wait for it to complete (repeat Phase 2 polling).

---

## Phase 5 -- Save and Handoff

Write `/workspace/deployment.json` (schema: `/mnt/skills/web-vercel-deployer/reference/deployment.schema.json`):

```json
{
  "vercel_project_id": "",
  "vercel_project_name": "",
  "deployment_id": "",
  "preview_url": "",
  "deployment_url": "",
  "status": "READY",
  "framework": "nextjs",
  "github_repo": "votrix-site-deploys/{project_slug}",
  "build_duration_seconds": 0,
  "environment_variables_set": [],
  "deployed_at": ""
}
```

Update `/workspace/pipeline_state.json`:
- Add `"web-vercel-deployer"` to `completed_stages`
- Set `current_stage` to `"web-vercel-deployer"`
- Update `updated_at` timestamp

Report to the user:

```
Deployment complete:
- Project:    {project_slug}
- Preview:    {preview_url}
- Status:     READY
- Build time: {duration}s
- Deployed:   {timestamp}
```

Tell the user the site is deployed and hand off to `web-preview-gate`.

---

## Error Recovery -- Build Failure

If the deployment status is `ERROR`:

1. Call `VERCEL_GET_DEPLOYMENT_EVENTS2` to retrieve the build logs
2. Parse the logs for the root cause:

| Common Error | Likely Cause | Fix |
|-------------|--------------|-----|
| Module not found | Missing dependency | Check package.json, run install |
| Build error in page | Syntax or type error in customized code | Fix the code, push, redeploy |
| Out of memory | Build too large | Check for large assets, optimize |
| Environment variable missing | Required env var not set | Set via Phase 4 |

3. Present the error and suggested fix to the user
4. If the fix requires code changes, tell the user to re-run web-site-customizer to fix and push, then re-run this skill
5. If the fix is an environment variable, set it via Phase 4 and redeploy

---

## Error Handling

| Error | Action |
|-------|--------|
| Vercel API not connected | Call `COMPOSIO_MANAGE_CONNECTIONS(toolkits=["vercel"])` -- this should not normally happen as Vercel uses Votrix's account |
| Project creation fails (409 conflict) | Ask user to use existing project or pick a new name |
| Project creation fails (other) | Report the error details, suggest retrying |
| Deployment timeout (>5 min) | Inform user, offer to continue waiting or check logs |
| Build failure | Follow Error Recovery flow above |
| Rate limit (429) | Wait 30 seconds and retry; inform user if persistent |
| GitHub repo not accessible from Vercel | Verify the repo exists and is public or that Vercel GitHub integration has access |
