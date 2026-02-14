#!/bin/bash
# Restart the FastAPI media service to pick up code changes

echo "Restarting FastAPI media service..."
sudo systemctl restart fastapi-media.service

echo "Waiting for service to start..."
sleep 3

echo ""
echo "Service status:"
systemctl status fastapi-media.service --no-pager | head -20

echo ""
echo "Testing health endpoint..."
curl -s http://localhost:8083/media/health

echo ""
echo ""
echo "Testing list videos endpoint..."
curl -s "http://localhost:8083/api/media/videos/list?split=temp&limit=3" | python3 -m json.tool 2>/dev/null || echo "Failed"

echo ""
