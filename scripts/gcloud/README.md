# Google Cloud Run Deployment

One-time setup scripts for deploying votrix-backend to Cloud Run.

Shared constants live in `scripts/gcloud/config.sh`:

```sh
PROJECT_ID="votrixai-480422"
REGION="us-central1"
REGISTRY="us-central1-docker.pkg.dev"
```

## Prerequisites

- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated (`gcloud auth login`)
- A GCP project selected (`gcloud config set project <PROJECT_ID>`)

## Setup (run once, in order)

### 0. Set up registry, APIs, and permissions

```bash
./scripts/gcloud/0-setup-registry.sh
```

This enables all required APIs (`run`, `secretmanager`, `cloudbuild`, `artifactregistry`), creates the Artifact Registry, and grants Cloud Build the permissions it needs to deploy.

### 1. Create secrets

Create a `.env.production` file (do NOT commit this):

```
APP_ENV=production
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
ANTHROPIC_API_KEY=sk-ant-...
COMPOSIO_API_KEY=...
APOLLO_API_KEY=...
TAVILY_API_KEY=...
FIRECRAWL_API_KEY=...
SENTRY_DSN=...
LOG_LEVEL=INFO
DEBUG=false
FORCE_REPROVISION=false
GCS_BUCKET_NAME=votrixtestbucket
```

Then run:

```bash
# Production secrets
./scripts/gcloud/1-create-secrets.sh .env.production

# Staging secrets (use --suffix to create database-url-staging, etc.)
./scripts/gcloud/1-create-secrets.sh .env.staging --suffix staging
```

The `--suffix` flag appends `-staging` to each secret name, matching what `service.staging.yaml` expects.

### 2. Deploy services

```bash
./scripts/gcloud/2-deploy-production.sh
./scripts/gcloud/3-deploy-staging.sh
```

Each script builds the Docker image, pushes it to Artifact Registry, and deploys the service with all secrets and config from the service YAML.

### 3. Set up CI/CD triggers

First, connect your GitHub repo in the GCP Console: **Cloud Build > Triggers > Connect Repository**.

Then run:

```bash
./scripts/gcloud/4-setup-triggers.sh <github-owner> <repo-name>
```

This creates two Cloud Build triggers:
- Push to `main` → deploys `votrix-backend` (production)
- Push to `beta` → deploys `votrix-backend-staging` (staging)

### 4. Allow public access

```bash
./scripts/gcloud/5-allow-public.sh
```

## After setup

No manual deploys needed. Just push:

```
feature branch → PR to beta → staging auto-deploys → test
                 PR to main → production auto-deploys
```

## Common operations

**Check what's running:**
```bash
./scripts/gcloud/status.sh
```

**Update secrets:**
```bash
./scripts/gcloud/1-create-secrets.sh .env.production
./scripts/gcloud/1-create-secrets.sh .env.staging --suffix staging
```

Re-running creates a new version. Cloud Run picks it up on next deploy.

**Rollback to a previous commit:**
```bash
gcloud run deploy votrix-backend \
  --image=us-central1-docker.pkg.dev/PROJECT/votrix/votrix-backend:COMMIT_SHA \
  --region=us-central1
```

## Files

| File | Purpose |
|---|---|
| `Dockerfile` | Multi-stage build using uv |
| `entrypoint.sh` | Runs Alembic migrations then starts uvicorn |
| `cloudbuild.yaml` | Cloud Build config (used by CI/CD triggers) |
| `service.production.yaml` | Cloud Run service definition for production |
| `service.staging.yaml` | Cloud Run service definition for staging |
