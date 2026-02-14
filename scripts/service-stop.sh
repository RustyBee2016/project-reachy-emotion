#!/bin/bash
# Service stop script with graceful shutdown
# This script stops the FastAPI service gracefully

set -e

echo "🛑 Stopping FastAPI Media Service..."

# Check if service is running
if ! systemctl is-active --quiet fastapi-media.service; then
    echo "⚠️  Service is not running"
    exit 0
fi

# Stop the service
echo "🔄 Stopping service..."
sudo systemctl stop fastapi-media.service

# Wait for service to stop
echo "⏳ Waiting for service to stop..."
for i in {1..10}; do
    if ! systemctl is-active --quiet fastapi-media.service; then
        echo "✅ Service stopped successfully"
        exit 0
    fi
    sleep 1
done

# If still running, force stop
if systemctl is-active --quiet fastapi-media.service; then
    echo "⚠️  Service did not stop gracefully, forcing stop..."
    sudo systemctl kill fastapi-media.service
    sleep 2
    
    if systemctl is-active --quiet fastapi-media.service; then
        echo "❌ Failed to stop service"
        exit 1
    else
        echo "✅ Service force-stopped"
    fi
fi
