#!/bin/sh
# Allow unauthenticated access to Cloud Run services (public API).
set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
. "${SCRIPT_DIR}/config.sh"

REGION="${1:-$REGION}"

gcloud run services add-iam-policy-binding "$PRODUCTION_SERVICE" \
  --region="$REGION" \
  --member="allUsers" \
  --role="roles/run.invoker"

gcloud run services add-iam-policy-binding "$STAGING_SERVICE" \
  --region="$REGION" \
  --member="allUsers" \
  --role="roles/run.invoker"

echo "Both services are now publicly accessible."
