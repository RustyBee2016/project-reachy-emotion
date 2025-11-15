#!/bin/bash
# Install or update systemd service
# This script copies the service file and enables it

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVICE_FILE="$PROJECT_ROOT/systemd/fastapi-media.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "📦 Installing FastAPI Media Service..."
echo ""

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Service file not found: $SERVICE_FILE"
    exit 1
fi

echo "📋 Service file: $SERVICE_FILE"
echo "📁 Target: $SYSTEMD_DIR/fastapi-media.service"
echo ""

# Check if service is currently running
if systemctl is-active --quiet fastapi-media.service; then
    echo "⚠️  Service is currently running"
    read -p "Stop service before updating? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🛑 Stopping service..."
        sudo systemctl stop fastapi-media.service
    else
        echo "❌ Cannot update service while running"
        exit 1
    fi
fi

# Copy service file
echo "📋 Copying service file..."
sudo cp "$SERVICE_FILE" "$SYSTEMD_DIR/fastapi-media.service"

# Reload systemd
echo "🔄 Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service
echo "✅ Enabling service (start on boot)..."
sudo systemctl enable fastapi-media.service

echo ""
echo "✅ Service installed successfully!"
echo ""
echo "Next steps:"
echo "  1. Create .env file: cp apps/api/.env.template apps/api/.env"
echo "  2. Edit .env file with your configuration"
echo "  3. Start service: ./scripts/service-start.sh"
echo "  4. Check status: ./scripts/service-status.sh"
echo ""
echo "Or start now:"
echo "  sudo systemctl start fastapi-media.service"
