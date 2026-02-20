#!/bin/bash
# Service status script with detailed checks
# This script provides comprehensive status information

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "📊 FastAPI Media Service Status"
echo "================================"
echo ""

# Check systemd service status
echo "🔧 Systemd Service:"
if systemctl is-active --quiet fastapi-media.service; then
    echo "   Status: ✅ RUNNING"
else
    echo "   Status: ❌ STOPPED"
fi

if systemctl is-enabled --quiet fastapi-media.service; then
    echo "   Enabled: ✅ YES (starts on boot)"
else
    echo "   Enabled: ❌ NO (manual start required)"
fi

echo ""

# Check health endpoint
echo "🏥 Health Check:"
if curl -f -s http://localhost:8083/api/v1/health > /dev/null 2>&1; then
    echo "   Status: ✅ HEALTHY"
    
    # Get detailed health info
    HEALTH_JSON=$(curl -s http://localhost:8083/api/v1/health)
    echo "   Response: $HEALTH_JSON" | head -c 200
    echo ""
else
    echo "   Status: ❌ UNREACHABLE"
fi

echo ""

# Check port
echo "🔌 Port Status:"
if lsof -i :8083 > /dev/null 2>&1; then
    echo "   Port 8083: ✅ LISTENING"
    lsof -i :8083 | grep LISTEN | head -n 1
else
    echo "   Port 8083: ❌ NOT LISTENING"
fi

echo ""

# Check configuration
echo "⚙️  Configuration:"
cd "$PROJECT_ROOT"
if python -c "from apps.api.app.config import load_and_validate_config; config = load_and_validate_config(check_port=False); print(f'   Videos root: {config.videos_root}'); print(f'   API port: {config.api_port}'); print(f'   Database: {config.database_url[:30]}...')" 2>&1; then
    echo "   Status: ✅ VALID"
else
    echo "   Status: ❌ INVALID"
fi

echo ""

# Check database connectivity (optional)
echo "🗄️  Database:"
if python -c "import asyncio; from apps.api.app.deps import get_config; from sqlalchemy.ext.asyncio import create_async_engine; config = get_config(); engine = create_async_engine(config.database_url, echo=False); asyncio.run(engine.dispose()); print('   Status: ✅ REACHABLE')" 2>/dev/null; then
    :
else
    echo "   Status: ⚠️  UNKNOWN (check logs)"
fi

echo ""

# Check filesystem
echo "📁 Filesystem:"
cd "$PROJECT_ROOT"
python -c "
from apps.api.app.config import get_config
config = get_config()
dirs = {
    'temp': config.temp_path,
    'dataset_all': config.dataset_path,
    'train': config.train_path,
    'test': config.test_path,
}
for name, path in dirs.items():
    status = '✅' if path.exists() else '❌'
    print(f'   {name}: {status} {path}')
"

echo ""

# Show recent logs
echo "📋 Recent Logs (last 5 lines):"
sudo journalctl -u fastapi-media.service -n 5 --no-pager | sed 's/^/   /'

echo ""
echo "================================"
echo "For full logs: sudo journalctl -u fastapi-media.service -f"
echo "For detailed status: systemctl status fastapi-media.service"
