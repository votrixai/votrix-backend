#!/bin/sh
# Show which commit is running on each Cloud Run service.
#
# Usage:
#   ./scripts/gcloud/status.sh
#   ./scripts/gcloud/status.sh us-central1

set -e

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
. "${SCRIPT_DIR}/config.sh"

REGION="${1:-$REGION}"

for service in "$PRODUCTION_SERVICE" "$STAGING_SERVICE"; do
  image=$(gcloud run services describe "$service" --region="$REGION" --format="value(spec.template.spec.containers[0].image)" 2>/dev/null) || continue
  sha=$(echo "$image" | grep -o '[^:]*$')

  echo "[$service]"
  echo "  Image: $image"

  if git rev-parse --verify "$sha" >/dev/null 2>&1; then
    echo "  Commit: $(git log "$sha" --oneline -1)"
  else
    echo "  Commit: $sha (not found locally — try git fetch)"
  fi

  echo ""
done
