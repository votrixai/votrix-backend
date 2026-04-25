#!/bin/sh
# Build image and deploy production service to Cloud Run.
set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
. "${SCRIPT_DIR}/config.sh"

REGION="${1:-$REGION}"
IMAGE="${REGISTRY}/${PROJECT_ID}/${REPOSITORY}/${PRODUCTION_SERVICE}:initial"

echo "Building and pushing image..."
gcloud builds submit --tag "$IMAGE" --quiet

echo "Deploying production..."
sed "s|IMAGE_URL|${IMAGE}|" service.production.yaml | gcloud run services replace --region="$REGION" /dev/stdin

echo "Production deployed."
