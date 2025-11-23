#!/bin/bash
# Start the Media Mover API with database-backed promotion service
# This server runs on port 8083 and provides:
# - Database-backed video metadata storage (PostgreSQL)
# - Promotion endpoints (/promote/stage, /promote/sample)
# - Media listing and serving
# - Manifest generation

set -e

# Configuration
HOST="${MEDIA_MOVER_HOST:-0.0.0.0}"
PORT="${MEDIA_MOVER_PORT:-8083}"
WORKERS="${MEDIA_MOVER_WORKERS:-1}"

# Database connection (override via environment)
export MEDIA_MOVER_DATABASE_URL="${MEDIA_MOVER_DATABASE_URL:-postgresql+psycopg2://reachy_app:reachy_app@localhost:5432/reachy_local}"

# Video storage root
export MEDIA_MOVER_VIDEOS_ROOT="${MEDIA_MOVER_VIDEOS_ROOT:-/mnt/videos}"

# Enable CORS for web UI
export MEDIA_MOVER_ENABLE_CORS="${MEDIA_MOVER_ENABLE_CORS:-true}"

# UI origins (comma-separated)
export MEDIA_MOVER_UI_ORIGINS="${MEDIA_MOVER_UI_ORIGINS:-http://localhost:8501,http://10.0.4.140:8501}"

echo "Starting Media Mover API..."
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Database: $MEDIA_MOVER_DATABASE_URL"
echo "  Videos Root: $MEDIA_MOVER_VIDEOS_ROOT"
echo ""

# Start the server
cd "$(dirname "$0")"
uvicorn apps.api.app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --log-level info \
    --access-log
