#!/bin/bash
set -e

uv sync
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
