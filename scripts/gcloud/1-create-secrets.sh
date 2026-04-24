#!/bin/sh
# Creates all secrets in Google Secret Manager.
# Run once per GCP project. Reads values from a .env-style file.
#
# Usage:
#   ./scripts/gcloud/1-create-secrets.sh .env.production
#   ./scripts/gcloud/1-create-secrets.sh .env.staging --suffix staging

set -e

ENV_FILE="${1:?Usage: $0 <env-file> [--suffix <suffix>]}"
SUFFIX=""

shift
while [ $# -gt 0 ]; do
  case "$1" in
    --suffix) SUFFIX="-$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [ ! -f "$ENV_FILE" ]; then
  echo "File not found: $ENV_FILE"
  exit 1
fi

while IFS='=' read -r key value; do
  [ -z "$key" ] && continue
  case "$key" in \#*) continue ;; esac

  secret_name="$(echo "$key" | tr '[:upper:]' '[:lower:]' | tr '_' '-')${SUFFIX}"

  if gcloud secrets describe "$secret_name" >/dev/null 2>&1; then
    echo "Updating secret: $secret_name"
    printf '%s' "$value" | gcloud secrets versions add "$secret_name" --data-file=-
  else
    echo "Creating secret: $secret_name"
    printf '%s' "$value" | gcloud secrets create "$secret_name" --data-file=-
  fi
done < "$ENV_FILE"

echo "Done."
