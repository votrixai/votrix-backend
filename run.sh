#!/bin/bash
set -e

uv sync
alembic upgrade head
uvicorn app.main:app --reload --port 8000
