#!/bin/sh
# Build image and deploy production service to Cloud Run.
set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "${SCRIPT_DIR}/../.." && pwd)
. "${SCRIPT_DIR}/config.sh"

REGION="${1:-$REGION}"
MANIFEST="${REPO_ROOT}/service.production.yaml"
if git -C "$REPO_ROOT" rev-parse --short HEAD >/dev/null 2>&1; then
  TAG=$(git -C "$REPO_ROOT" rev-parse --short HEAD)
else
  TAG=$(date -u +%Y%m%d%H%M%S)
fi
IMAGE="${REGISTRY}/${PROJECT_ID}/${REPOSITORY}/${PRODUCTION_SERVICE}:${TAG}"

echo "Building and pushing image..."
gcloud builds submit "$REPO_ROOT" --tag "$IMAGE" --quiet

echo "Deploying production..."
sed "s|IMAGE_URL|${IMAGE}|" "$MANIFEST" | gcloud run services replace --region="$REGION" /dev/stdin

echo "Production deployed."
