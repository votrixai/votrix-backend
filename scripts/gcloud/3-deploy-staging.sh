#!/bin/sh
# Build image and deploy staging service to Cloud Run.
set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
. "${SCRIPT_DIR}/config.sh"

REGION="${1:-$REGION}"
IMAGE="${REGISTRY}/${PROJECT_ID}/${REPOSITORY}/${STAGING_SERVICE}:initial"

echo "Building and pushing image..."
gcloud builds submit --tag "$IMAGE" --quiet

echo "Deploying staging..."
sed "s|IMAGE_URL|${IMAGE}|" service.staging.yaml | gcloud run services replace --region="$REGION" /dev/stdin

echo "Staging deployed."
