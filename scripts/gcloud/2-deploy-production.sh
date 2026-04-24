#!/bin/sh
# Build image and deploy production service to Cloud Run.
set -e

REGION="${1:-us-central1}"
PROJECT_ID=$(gcloud config get project)
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/votrix/votrix-backend:initial"

echo "Building and pushing image..."
gcloud builds submit --tag "$IMAGE" --quiet

echo "Deploying production..."
sed "s|IMAGE_URL|${IMAGE}|" service.production.yaml | gcloud run services replace --region="$REGION" /dev/stdin

echo "Production deployed."
