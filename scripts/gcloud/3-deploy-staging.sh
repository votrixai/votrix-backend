#!/bin/sh
# Build image and deploy staging service to Cloud Run.
set -e

REGION="${1:-us-central1}"
PROJECT_ID=$(gcloud config get project)
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/votrix/votrix-backend-staging:initial"

echo "Building and pushing image..."
gcloud builds submit --tag "$IMAGE" --quiet

echo "Deploying staging..."
sed "s|IMAGE_URL|${IMAGE}|" service.staging.yaml | gcloud run services replace --region="$REGION" /dev/stdin

echo "Staging deployed."
