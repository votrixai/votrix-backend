#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_VARS_DIR="$SCRIPT_DIR/../../votrix-env-vars"

cp "$ENV_VARS_DIR/backend-local" "$SCRIPT_DIR/../.env"
cp "$ENV_VARS_DIR/backend-production" "$SCRIPT_DIR/../.env.production"
cp "$ENV_VARS_DIR/backend-staging" "$SCRIPT_DIR/../.env.staging"

echo "Done — copied .env, .env.production, and .env.staging for backend"
