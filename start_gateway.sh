#!/bin/bash
# Startup script for Reachy Gateway on Ubuntu 2

set -e

# Change to project root
cd "$(dirname "$0")"

echo "Starting Reachy Gateway..."

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "Virtual environment activated"
else
    echo "ERROR: Virtual environment not found at venv/bin/activate"
    exit 1
fi

# Load environment variables from .env if it exists
if [ -f "apps/gateway/.env" ]; then
    echo "Loading environment from apps/gateway/.env"
    export $(grep -v '^#' apps/gateway/.env | xargs)
fi

# Set default environment variables (can be overridden by .env)
export GATEWAY_MEDIA_MOVER_URL="${GATEWAY_MEDIA_MOVER_URL:-http://10.0.4.130:8083}"
export GATEWAY_NGINX_MEDIA_URL="${GATEWAY_NGINX_MEDIA_URL:-http://10.0.4.130:8082}"
export GATEWAY_DATABASE_URL="${GATEWAY_DATABASE_URL:-postgresql+asyncpg://reachy_app:reachy_app@10.0.4.130:5432/reachy_local}"

export GATEWAY_API_HOST="${GATEWAY_API_HOST:-0.0.0.0}"
export GATEWAY_API_PORT="${GATEWAY_API_PORT:-8000}"
export GATEWAY_API_ROOT_PATH="${GATEWAY_API_ROOT_PATH:-}"

export GATEWAY_ENABLE_CORS="${GATEWAY_ENABLE_CORS:-true}"
export GATEWAY_UI_ORIGINS="${GATEWAY_UI_ORIGINS:-http://localhost:8501,http://10.0.4.140:8501}"

export GATEWAY_LOG_LEVEL="${GATEWAY_LOG_LEVEL:-INFO}"

# Log configuration (mask password)
echo "Gateway Configuration:"
echo "  Media Mover URL: $GATEWAY_MEDIA_MOVER_URL"
echo "  Nginx Media URL: $GATEWAY_NGINX_MEDIA_URL"
echo "  Database URL: $(echo $GATEWAY_DATABASE_URL | sed 's/:.*@/:****@/')"
echo "  API Host: $GATEWAY_API_HOST"
echo "  API Port: $GATEWAY_API_PORT"
echo "  CORS Enabled: $GATEWAY_ENABLE_CORS"
echo "  Log Level: $GATEWAY_LOG_LEVEL"

# Start the gateway using uvicorn
exec uvicorn apps.gateway.main:app \
    --host "$GATEWAY_API_HOST" \
    --port "$GATEWAY_API_PORT" \
    --log-level "$(echo $GATEWAY_LOG_LEVEL | tr '[:upper:]' '[:lower:]')" \
    --no-access-log
