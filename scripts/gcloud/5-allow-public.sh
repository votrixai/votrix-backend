#!/bin/sh
# Allow unauthenticated access to Cloud Run services (public API).
set -e

REGION="${1:-us-central1}"

gcloud run services add-iam-policy-binding votrix-backend \
  --region="$REGION" \
  --member="allUsers" \
  --role="roles/run.invoker"

gcloud run services add-iam-policy-binding votrix-backend-staging \
  --region="$REGION" \
  --member="allUsers" \
  --role="roles/run.invoker"

echo "Both services are now publicly accessible."
