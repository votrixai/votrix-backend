#!/bin/sh
# Create Cloud Build triggers for auto-deploy on push.
# Run once per GCP project.
#
# Prerequisite: connect your GitHub repo in the GCP Console first:
#   Cloud Build > Triggers > Connect Repository
#
# Usage:
#   ./scripts/gcloud/4-setup-triggers.sh <github-owner> <repo-name>
#   ./scripts/gcloud/4-setup-triggers.sh myorg votrix-backend

set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
. "${SCRIPT_DIR}/config.sh"

OWNER="${1:?Usage: $0 <github-owner> <repo-name>}"
REPO="${2:?Usage: $0 <github-owner> <repo-name>}"

echo "Creating production trigger (main branch)..."
gcloud builds triggers create github \
  --repo-name="$REPO" \
  --repo-owner="$OWNER" \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml \
  --name=deploy-production \
  --substitutions=_SERVICE_NAME="${PRODUCTION_SERVICE}",_REPO="${REPOSITORY}",_REGION="${REGION}"

echo "Creating staging trigger (beta branch)..."
gcloud builds triggers create github \
  --repo-name="$REPO" \
  --repo-owner="$OWNER" \
  --branch-pattern="^beta$" \
  --build-config=cloudbuild.yaml \
  --name=deploy-staging \
  --substitutions=_SERVICE_NAME="${STAGING_SERVICE}",_REPO="${REPOSITORY}",_REGION="${REGION}"

echo "Done. Triggers created."
