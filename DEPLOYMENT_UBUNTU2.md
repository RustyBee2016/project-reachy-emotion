# Ubuntu 2 Deployment Checklist

This document outlines the steps to deploy the Gateway and UI services on Ubuntu 2.

## Prerequisites

- [x] Ubuntu 2 installed and accessible via SSH
- [x] Python 3.8+ installed
- [x] Virtual environment created at `/home/rusty_admin/projects/reachy_08.4.2/venv`
- [x] Project dependencies installed (Phase 1)
- [x] Network connectivity to Ubuntu 1 (10.0.4.130)

## 1. Gateway Service Deployment

### 1.1 Configure Environment

```bash
cd /home/rusty_admin/projects/reachy_08.4.2

# Copy the environment template
cp apps/gateway/.env.template apps/gateway/.env

# Edit the .env file with your values
nano apps/gateway/.env
```

**Key variables to verify:**
```bash
GATEWAY_MEDIA_MOVER_URL=http://10.0.4.130:8083
GATEWAY_NGINX_MEDIA_URL=http://10.0.4.130:8082
GATEWAY_DATABASE_URL=postgresql+asyncpg://reachy_app:reachy_app@10.0.4.130:5432/reachy_local
GATEWAY_API_PORT=8000
GATEWAY_ENABLE_CORS=true
GATEWAY_UI_ORIGINS=http://localhost:8501,http://10.0.4.140:8501
```

### 1.2 Test Gateway Manually

```bash
# Activate virtual environment
source venv/bin/activate

# Test the startup script
./start_gateway.sh
```

**In another terminal, test the endpoints:**
```bash
# Health check
curl http://localhost:8000/health

# Ready check
curl http://localhost:8000/ready

# Metrics
curl http://localhost:8000/metrics
```

**Press Ctrl+C to stop the manual test.**

### 1.3 Install as systemd Service

```bash
# Copy the service file
sudo cp systemd/reachy-gateway.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable the service (start on boot)
sudo systemctl enable reachy-gateway.service

# Start the service
sudo systemctl start reachy-gateway.service

# Check status
sudo systemctl status reachy-gateway.service
```

### 1.4 Verify Gateway is Running

```bash
# Check service status
sudo systemctl status reachy-gateway.service

# View logs
sudo journalctl -u reachy-gateway.service -n 50 --no-pager

# Test endpoints
curl http://localhost:8000/health
curl http://10.0.4.140:8000/health  # From Ubuntu 1
```

### 1.5 Test Proxying to Media Mover

**From Ubuntu 2:**
```bash
# Test that gateway can reach Media Mover
curl -v http://localhost:8000/api/videos/test_video

# Test promotion endpoint (requires valid video)
curl -X POST http://localhost:8000/api/promote \
  -H "Content-Type: application/json" \
  -H "X-API-Version: v1" \
  -H "Idempotency-Key: test-123" \
  -d '{
    "schema_version": "v1",
    "clip": "test_clip.mp4",
    "target": "train",
    "label": "happy",
    "correlation_id": "test-456"
  }'
```

**Expected results:**
- Health/ready endpoints return 200 OK
- Proxy endpoints return responses from Media Mover (or 502/503 if Media Mover is down)

---

## 2. Streamlit UI Deployment

### 2.1 Locate UI Application

```bash
# Find the Streamlit app entry point
find apps -name "*.py" | grep -E "(streamlit|web|ui)"
```

**Common locations:**
- `apps/web/app.py`
- `apps/ui/main.py`
- `apps/streamlit_app.py`

### 2.2 Create UI Startup Script

Create `/home/rusty_admin/projects/reachy_08.4.2/start_ui.sh`:

```bash
#!/bin/bash
# Startup script for Reachy Streamlit UI on Ubuntu 2

set -e

cd "$(dirname "$0")"

echo "Starting Reachy UI..."

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "Virtual environment activated"
else
    echo "ERROR: Virtual environment not found"
    exit 1
fi

# Set environment variables
export REACHY_GATEWAY_URL="${REACHY_GATEWAY_URL:-http://localhost:8000}"
export STREAMLIT_SERVER_PORT="${STREAMLIT_SERVER_PORT:-8501}"
export STREAMLIT_SERVER_ADDRESS="${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}"

echo "UI Configuration:"
echo "  Gateway URL: $REACHY_GATEWAY_URL"
echo "  Streamlit Port: $STREAMLIT_SERVER_PORT"

# Start Streamlit
exec streamlit run apps/web/app.py \
    --server.port "$STREAMLIT_SERVER_PORT" \
    --server.address "$STREAMLIT_SERVER_ADDRESS" \
    --server.headless true
```

```bash
chmod +x start_ui.sh
```

### 2.3 Test UI Manually

```bash
./start_ui.sh
```

**Open browser to:** `http://10.0.4.140:8501`

**Press Ctrl+C to stop.**

### 2.4 Create UI systemd Service

Create `/home/rusty_admin/projects/reachy_08.4.2/systemd/reachy-ui.service`:

```ini
[Unit]
Description=Reachy Streamlit UI Service (Ubuntu 2)
Documentation=https://github.com/RustyBee2016/project-reachy-emotion
After=network.target reachy-gateway.service
Requires=reachy-gateway.service

[Service]
Type=simple
User=rusty_admin
Group=rusty_admin
WorkingDirectory=/home/rusty_admin/projects/reachy_08.4.2

Environment="REACHY_GATEWAY_URL=http://localhost:8000"
Environment="STREAMLIT_SERVER_PORT=8501"
Environment="STREAMLIT_SERVER_ADDRESS=0.0.0.0"

ExecStart=/home/rusty_admin/projects/reachy_08.4.2/start_ui.sh

Restart=on-failure
RestartSec=5s
StartLimitInterval=300s
StartLimitBurst=5

StandardOutput=journal
StandardError=journal
SyslogIdentifier=reachy-ui

[Install]
WantedBy=multi-user.target
```

### 2.5 Install UI Service

```bash
sudo cp systemd/reachy-ui.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable reachy-ui.service
sudo systemctl start reachy-ui.service
sudo systemctl status reachy-ui.service
```

---

## 3. Nginx Reverse Proxy (Optional)

### 3.1 Install Nginx

```bash
sudo apt update
sudo apt install nginx
```

### 3.2 Create Nginx Configuration

Create `/etc/nginx/sites-available/reachy`:

```nginx
# Reachy Emotion System - Ubuntu 2 Reverse Proxy

upstream gateway {
    server 127.0.0.1:8000;
}

upstream ui {
    server 127.0.0.1:8501;
}

server {
    listen 80;
    server_name 10.0.4.140;

    # Gateway API
    location /api/ {
        proxy_pass http://gateway;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Health/metrics endpoints
    location ~ ^/(health|ready|metrics)$ {
        proxy_pass http://gateway;
        proxy_set_header Host $host;
    }

    # Streamlit UI (root and _stcore for websockets)
    location / {
        proxy_pass http://ui;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /_stcore/ {
        proxy_pass http://ui;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### 3.3 Enable and Test Nginx

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/reachy /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status nginx
```

### 3.4 Test via Nginx

```bash
# From Ubuntu 1
curl http://10.0.4.140/health
curl http://10.0.4.140/api/videos/test

# Open browser to http://10.0.4.140 (should show Streamlit UI)
```

---

## 4. Verification Tests

### 4.1 Service Status Check

```bash
# On Ubuntu 2
sudo systemctl status reachy-gateway.service
sudo systemctl status reachy-ui.service
sudo systemctl status nginx  # if installed
```

### 4.2 Port Connectivity

```bash
# From Ubuntu 1, test Ubuntu 2 ports
telnet 10.0.4.140 8000  # Gateway
telnet 10.0.4.140 8501  # UI
telnet 10.0.4.140 80    # Nginx (if installed)
```

### 4.3 End-to-End API Test

```bash
# From Ubuntu 1, test gateway → media mover flow
curl -X POST http://10.0.4.140:8000/api/events/emotion \
  -H "Content-Type: application/json" \
  -H "X-API-Version: v1" \
  -d '{
    "schema_version": "v1",
    "device_id": "test-device",
    "ts": "2025-11-24T21:00:00Z",
    "emotion": "happy",
    "confidence": 0.9,
    "inference_ms": 50,
    "window": {"fps": 30, "size_s": 1.0, "hop_s": 0.5},
    "meta": {},
    "correlation_id": "test-123"
  }'
```

**Expected:** 202 Accepted

### 4.4 UI Functionality Test

1. Open browser to `http://10.0.4.140:8501` (or `http://10.0.4.140` if using Nginx)
2. Verify UI loads
3. Test video listing (should fetch from Media Mover via Gateway)
4. Test video promotion (should proxy to Media Mover)

---

## 5. Troubleshooting

### Gateway won't start

```bash
# Check logs
sudo journalctl -u reachy-gateway.service -n 100 --no-pager

# Test config
source venv/bin/activate
python3 -c "from apps.gateway.config import load_config; c = load_config(); print(c.log_configuration())"

# Test connectivity to Ubuntu 1
curl http://10.0.4.130:8083/api/v1/healthz
```

### UI won't start

```bash
# Check logs
sudo journalctl -u reachy-ui.service -n 100 --no-pager

# Test Streamlit directly
source venv/bin/activate
streamlit run apps/web/app.py --server.port 8501
```

### Gateway returns 502/503

This means the gateway can't reach Media Mover on Ubuntu 1.

```bash
# From Ubuntu 2, test Media Mover
curl http://10.0.4.130:8083/api/v1/healthz

# Check Media Mover status on Ubuntu 1
ssh rusty_admin@10.0.4.130 "sudo systemctl status fastapi-media.service"
```

### CORS errors in browser

```bash
# Check CORS config
grep GATEWAY_ENABLE_CORS apps/gateway/.env
grep GATEWAY_UI_ORIGINS apps/gateway/.env

# Restart gateway after config changes
sudo systemctl restart reachy-gateway.service
```

---

## 6. Post-Deployment

### 6.1 Enable Services on Boot

```bash
sudo systemctl enable reachy-gateway.service
sudo systemctl enable reachy-ui.service
sudo systemctl enable nginx  # if installed
```

### 6.2 Set Up Monitoring

Consider setting up:
- Prometheus to scrape `http://10.0.4.140:8000/metrics`
- Grafana dashboards for gateway metrics
- Log aggregation (e.g., ELK stack or Loki)

### 6.3 Document Deployment

Update `memory-bank/runbooks/` with:
- Gateway deployment procedure
- UI deployment procedure
- Troubleshooting guide

---

## Summary

After completing this checklist, you should have:

- ✅ Gateway running on Ubuntu 2 port 8000
- ✅ UI running on Ubuntu 2 port 8501
- ✅ (Optional) Nginx reverse proxy on port 80
- ✅ All services auto-start on boot
- ✅ End-to-end connectivity verified

**Next steps:**
1. Configure Jetson to send emotion events to `http://10.0.4.140:8000/api/events/emotion`
2. Set up n8n workflows (if desired)
3. Configure monitoring and alerting
