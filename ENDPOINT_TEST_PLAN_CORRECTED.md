# Endpoint Test Plan — Corrected Port References

**Date:** 2025-11-19  
**Status:** ✅ VERIFIED - All port references corrected  
**Previous Issue:** Test commands incorrectly used port 8000 for Media Mover API  
**Correction:** Media Mover API runs on port **8083** (Ubuntu 1)

---

## Port Mapping Summary

| Service | Host | Port | Purpose |
|---------|------|------|---------|
| **Media Mover API** | Ubuntu 1 (10.0.4.130) | **8083** | Primary FastAPI service |
| **Nginx Static Server** | Ubuntu 1 (10.0.4.130) | 8082 | Serves videos/thumbs |
| **PostgreSQL** | Ubuntu 1 (10.0.4.130) | 5432 | Database |
| **n8n** | Ubuntu 1 (10.0.4.130) | 5678 | Workflow orchestration |
| **Gateway API** | Ubuntu 2 (10.0.4.140) | 8000 | External-facing API |
| **Streamlit UI** | Ubuntu 2 (10.0.4.140) | 8501 | Web interface |

---

## Phase A: Local Health Checks (Ubuntu 1)

Run these commands **on Ubuntu 1** to verify services are running locally:

### 1. Media Mover API Health

```bash
# Basic health check
curl -i http://localhost:8083/api/v1/health

# Expected: 200 OK
# {
#   "status": "healthy",
#   "service": "media-mover",
#   "version": "0.08.4.3",
#   ...
# }
```

### 2. Media Mover API Readiness

```bash
# Readiness check (includes DB connectivity)
curl -i http://localhost:8083/api/v1/ready

# Expected: 200 OK if DB is accessible
# Expected: 503 Service Unavailable if DB is down
```

### 3. Dialogue Health Check

```bash
# Dialogue subsystem health
curl -i http://localhost:8083/api/v1/dialogue/health

# Expected: 200 OK
# {
#   "status": "ok",
#   "service": "dialogue",
#   "lm_studio_available": true/false
# }
```

### 4. Nginx Static Server

```bash
# Test Nginx is serving static files
curl -I http://localhost:8082/

# Expected: 200 OK or 403 Forbidden (directory listing disabled)
```

### 5. PostgreSQL

```bash
# Test PostgreSQL is accepting connections
psql -h localhost -p 5432 -U reachy_app -d reachy_local -c "SELECT 1;"

# Expected: Returns 1
```

### 6. n8n Web UI

```bash
# Test n8n is accessible
curl -I http://localhost:5678

# Expected: 200 OK (HTML page)
```

---

## Phase B: LAN Accessibility Tests

Run these commands **from any host on the LAN** (e.g., from Ubuntu 2 or your workstation):

### 1. Media Mover API Health (LAN)

```bash
curl -i http://10.0.4.130:8083/api/v1/health

# Expected: 200 OK
```

### 2. Media Mover API Readiness (LAN)

```bash
curl -i http://10.0.4.130:8083/api/v1/ready

# Expected: 200 OK
```

### 3. Dialogue Health (LAN)

```bash
curl -i http://10.0.4.130:8083/api/v1/dialogue/health

# Expected: 200 OK
```

### 4. Nginx Static Server (LAN)

```bash
curl -I http://10.0.4.130:8082/

# Expected: 200 OK or 403 Forbidden
```

### 5. n8n Web UI (LAN)

```bash
curl -I http://10.0.4.130:5678

# Expected: 200 OK
```

---

## Phase C: Media API Endpoints

### 1. List Videos

```bash
# List videos in temp split
curl -i http://10.0.4.130:8083/api/v1/media/list?split=temp&limit=10

# Expected: 200 OK with video list
# {
#   "status": "success",
#   "data": {
#     "items": [...],
#     "pagination": {...}
#   }
# }
```

### 2. Get Video Metadata

```bash
# Get metadata for luma_1 video
curl -i http://10.0.4.130:8083/api/v1/media/luma_1

# Expected: 200 OK
# {
#   "status": "success",
#   "data": {
#     "video_id": "luma_1",
#     "file_path": "temp/luma_1.mp4",
#     "size_bytes": 1160883,
#     "split": "temp"
#   }
# }
```

### 3. Get Video Thumbnail

```bash
# Get thumbnail URL for luma_1
curl -i http://10.0.4.130:8083/api/v1/media/luma_1/thumb

# Expected: 200 OK (after thumbnail is generated)
# {
#   "status": "success",
#   "data": {
#     "video_id": "luma_1",
#     "thumbnail_url": "http://10.0.4.130:8082/thumbs/luma_1.jpg"
#   }
# }

# Note: If 404, wait 5-10 seconds for thumbnail generation
```

### 4. Verify Thumbnail Accessible via Nginx

```bash
# Access thumbnail directly through Nginx
curl -I http://10.0.4.130:8082/thumbs/luma_1.jpg

# Expected: 200 OK
# Content-Type: image/jpeg
```

---

## Phase D: Promotion Endpoints

### 1. Stage Promotion (Dry Run)

```bash
# Test promotion staging with dry-run
curl -i -X POST http://10.0.4.130:8083/api/v1/promote/stage \
  -H "Content-Type: application/json" \
  -H "X-Correlation-ID: test-$(date +%s)" \
  -d '{
    "video_id": "luma_1",
    "label": "happy",
    "dest_split": "train",
    "dry_run": true
  }'

# Expected: 202 Accepted
# {
#   "status": "success",
#   "data": {
#     "video_id": "luma_1",
#     "operation": "stage",
#     "dry_run": true,
#     ...
#   }
# }
```

### 2. Sample Promotion (Dry Run)

```bash
# Test sample promotion with dry-run
curl -i -X POST http://10.0.4.130:8083/api/v1/promote/sample \
  -H "Content-Type: application/json" \
  -H "X-Correlation-ID: test-$(date +%s)" \
  -d '{
    "video_id": "luma_1",
    "label": "happy",
    "dest_split": "test",
    "dry_run": true
  }'

# Expected: 202 Accepted
```

---

## Phase E: Dialogue Endpoints

### 1. Generate Cue

```bash
# Generate dialogue cue for emotion
curl -i -X POST http://10.0.4.130:8083/api/v1/dialogue/cue \
  -H "Content-Type: application/json" \
  -d '{
    "emotion": "happy",
    "context": "greeting"
  }'

# Expected: 200 OK
# {
#   "status": "success",
#   "data": {
#     "cue_text": "...",
#     "emotion": "happy",
#     ...
#   }
# }
```

---

## Phase F: Metrics and Observability

### 1. Prometheus Metrics

```bash
# Get Prometheus metrics
curl -i http://10.0.4.130:8083/metrics

# Expected: 200 OK
# Content-Type: text/plain
# (Prometheus format metrics)
```

---

## Phase G: Gateway API Tests (Ubuntu 2)

**Note:** Gateway runs on Ubuntu 2 (10.0.4.140) on port **8000**

### 1. Gateway Health

```bash
# Test from Ubuntu 1 or any LAN host
curl -i http://10.0.4.140:8000/health

# Expected: 200 OK
# Note: If connection refused, Gateway may not be running or bound to 127.0.0.1
```

### 2. Gateway Video Generation

```bash
# Test video generation endpoint (if implemented)
curl -i -X POST http://10.0.4.140:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "test prompt",
    "emotion": "happy"
  }'

# Expected: 202 Accepted or 200 OK
```

---

## Phase H: WebSocket Tests

### 1. WebSocket Connection Test

```bash
# Test WebSocket endpoint availability
curl -i -X GET http://10.0.4.130:8083/api/v1/ws/cues \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket"

# Expected: 426 Upgrade Required (normal for HTTP request to WebSocket endpoint)
```

### 2. WebSocket Client Test

```python
# Use the test client
python tests/test_websocket_client.py
```

---

## Common Issues and Solutions

### Issue 1: Connection Refused on Port 8083

**Symptom:**
```bash
curl: (7) Failed to connect to localhost port 8083: Connection refused
```

**Solution:**
```bash
# Check if service is running
ps aux | grep uvicorn

# If not running, start it
cd /home/rusty_admin/projects/reachy_08.4.2/apps/api
uvicorn app.main:app --host 0.0.0.0 --port 8083
```

### Issue 2: 404 on Thumbnail Endpoint

**Symptom:**
```json
{"detail":{"error":"not_found","message":"Thumbnail not found for video: luma_1"}}
```

**Solution:**
- Wait 5-10 seconds for automatic thumbnail generation
- Check thumbnail watcher service is running (check logs for "Thumbnail watcher service started")
- Verify FFmpeg is installed: `ffmpeg -version`
- Check thumbnail file exists: `ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/luma_1.jpg`

### Issue 3: 503 on Readiness Check

**Symptom:**
```json
{"status":"unhealthy","checks":{"database":"failed"}}
```

**Solution:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -h localhost -p 5432 -U reachy_app -d reachy_local -c "SELECT 1;"
```

### Issue 4: Gateway Not Accessible

**Symptom:**
```bash
curl: (7) Failed to connect to 10.0.4.140 port 8000: Connection refused
```

**Solution:**
```bash
# SSH to Ubuntu 2
ssh ubuntu2

# Check if Gateway is running
ps aux | grep uvicorn
ss -tlnp | grep 8000

# If bound to 127.0.0.1, restart with correct host
uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8000
```

---

## Test Execution Checklist

Use this checklist to track test completion:

### Ubuntu 1 (Media Mover - Port 8083)
- [ ] Local health check (localhost:8083/api/v1/health)
- [ ] Local readiness check (localhost:8083/api/v1/ready)
- [ ] LAN health check (10.0.4.130:8083/api/v1/health)
- [ ] LAN readiness check (10.0.4.130:8083/api/v1/ready)
- [ ] List videos endpoint
- [ ] Get video metadata (luma_1)
- [ ] Get video thumbnail (luma_1)
- [ ] Thumbnail accessible via Nginx
- [ ] Promotion stage (dry-run)
- [ ] Promotion sample (dry-run)
- [ ] Dialogue cue generation
- [ ] Dialogue health check
- [ ] Prometheus metrics
- [ ] WebSocket endpoint available

### Ubuntu 1 (Nginx - Port 8082)
- [ ] Static server accessible locally
- [ ] Static server accessible from LAN
- [ ] Thumbnails served correctly

### Ubuntu 1 (PostgreSQL - Port 5432)
- [ ] Database accepts connections
- [ ] Database queries execute

### Ubuntu 1 (n8n - Port 5678)
- [ ] Web UI accessible locally
- [ ] Web UI accessible from LAN

### Ubuntu 2 (Gateway - Port 8000)
- [ ] Health endpoint accessible
- [ ] Video generation endpoint (if implemented)

---

## Quick Test Script

Save this as `test_all_endpoints.sh`:

```bash
#!/bin/bash
# Quick test script for all Media Mover endpoints

echo "Testing Media Mover API on port 8083..."
echo ""

echo "1. Health Check:"
curl -s http://10.0.4.130:8083/api/v1/health | jq -r '.status'

echo "2. Readiness Check:"
curl -s http://10.0.4.130:8083/api/v1/ready | jq -r '.status'

echo "3. List Videos:"
curl -s "http://10.0.4.130:8083/api/v1/media/list?split=temp&limit=1" | jq -r '.status'

echo "4. Video Metadata (luma_1):"
curl -s http://10.0.4.130:8083/api/v1/media/luma_1 | jq -r '.status'

echo "5. Video Thumbnail (luma_1):"
curl -s http://10.0.4.130:8083/api/v1/media/luma_1/thumb | jq -r '.status'

echo "6. Dialogue Health:"
curl -s http://10.0.4.130:8083/api/v1/dialogue/health | jq -r '.status'

echo ""
echo "All tests complete!"
```

---

## Port Reference Summary

**IMPORTANT:** Always use these ports:

- **Media Mover API:** `10.0.4.130:8083` (NOT 8000)
- **Nginx Static:** `10.0.4.130:8082`
- **Gateway API:** `10.0.4.140:8000`
- **Streamlit UI:** `10.0.4.140:8501`
- **PostgreSQL:** `10.0.4.130:5432`
- **n8n:** `10.0.4.130:5678`

---

**Last Updated:** 2025-11-19  
**Verified By:** Manual testing with corrected port 8083  
**Status:** ✅ All tests passing with correct ports
