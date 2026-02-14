#!/bin/bash
# Service restart script
# This script restarts the FastAPI service and validates it's working

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔄 Restarting FastAPI Media Service..."

# Stop the service
"$SCRIPT_DIR/service-stop.sh"

# Wait a moment
sleep 1

# Start the service
"$SCRIPT_DIR/service-start.sh"
