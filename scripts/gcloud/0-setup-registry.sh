#!/bin/sh
# Create Artifact Registry and set up IAM permissions. Run once per project.
#
# Usage:
#   ./scripts/gcloud/0-setup-registry.sh
#   ./scripts/gcloud/0-setup-registry.sh us-central1

set -e

REGION="${1:-us-central1}"
PROJECT_ID=$(gcloud config get project)
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

echo "Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com

echo "Creating Artifact Registry..."
gcloud artifacts repositories create votrix \
  --repository-format=docker \
  --location="$REGION" \
  --description="Votrix Docker images" 2>/dev/null || echo "Registry already exists."

COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Granting Cloud Build permissions..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/run.admin" --quiet

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/iam.serviceAccountUser" --quiet

echo "Granting Cloud Run runtime access to secrets..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/secretmanager.secretAccessor" --quiet

echo ""
echo "Registry: ${REGION}-docker.pkg.dev/${PROJECT_ID}/votrix"
echo "Done."
