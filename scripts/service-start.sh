#!/bin/bash
# Service start script with validation
# This script validates configuration before starting the FastAPI service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting FastAPI Media Service..."
echo "Project root: $PROJECT_ROOT"

# Validate configuration
echo "📋 Validating configuration..."
cd "$PROJECT_ROOT"

if python -c "from apps.api.app.config import load_and_validate_config; load_and_validate_config(check_port=True)" 2>&1; then
    echo "✅ Configuration valid"
else
    echo "❌ Configuration validation failed"
    exit 1
fi

# Check if service is already running
if systemctl is-active --quiet fastapi-media.service; then
    echo "⚠️  Service is already running"
    echo "Use './scripts/service-restart.sh' to restart"
    exit 1
fi

# Start the service
echo "🔄 Starting service..."
sudo systemctl start fastapi-media.service

# Wait a moment for service to start
sleep 2

# Check service status
if systemctl is-active --quiet fastapi-media.service; then
    echo "✅ Service started successfully"
    
    # Check health endpoint
    echo "🏥 Checking health endpoint..."
    if curl -f -s http://localhost:8083/api/v1/health > /dev/null 2>&1; then
        echo "✅ Health check passed"
    else
        echo "⚠️  Health check failed (service may still be starting)"
    fi
    
    # Show status
    echo ""
    echo "📊 Service Status:"
    systemctl status fastapi-media.service --no-pager -l | head -n 10
else
    echo "❌ Service failed to start"
    echo ""
    echo "📋 Recent logs:"
    sudo journalctl -u fastapi-media.service -n 20 --no-pager
    exit 1
fi

echo ""
echo "✅ Service started successfully!"
echo "   API: http://localhost:8083"
echo "   Docs: http://localhost:8083/docs"
echo "   Health: http://localhost:8083/api/v1/health"
