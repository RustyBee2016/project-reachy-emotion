# Gateway Implementation Summary

## Overview

I've implemented a **separate, production-ready Gateway application** for Ubuntu 2 that is distinct from the Media Mover on Ubuntu 1.

## Why Separate Gateway?

| Aspect | Dual-Purpose `main.py` | Separate Gateway App ✅ |
|--------|------------------------|------------------------|
| **Clarity** | Confusing - same code, different behavior | Clear - dedicated purpose |
| **Dependencies** | Loads unnecessary filesystem/thumbnail code | Minimal - HTTP client only |
| **Testing** | Complex env mocking required | Easy - isolated unit tests |
| **Debugging** | Hard to trace which "mode" is active | Obvious from logs/config |
| **Deployment** | Error-prone config differences | Explicit, documented |

## Architecture

```
apps/
├── api/                          # Media Mover (Ubuntu 1)
│   ├── app/
│   │   ├── main.py              # Media Mover entry point
│   │   ├── config.py            # Filesystem-aware config
│   │   └── routers/
│   │       ├── media_v1.py      # Direct file operations
│   │       ├── promote.py       # Direct file moves
│   │       └── ...
│   └── routers/
│       └── gateway.py           # Shared gateway router (proxying logic)
│
└── gateway/                      # Gateway (Ubuntu 2) ✅ NEW
    ├── __init__.py
    ├── main.py                  # Gateway entry point
    ├── config.py                # Gateway-specific config
    ├── .env.template            # Gateway env vars
    └── README.md                # Gateway documentation
```

## What Was Created

### 1. Gateway Application (`apps/gateway/`)

**`apps/gateway/main.py`**
- Minimal FastAPI app
- No filesystem dependencies
- Registers only the `gateway.router` (proxying endpoints)
- Uses `httpx.AsyncClient` for efficient HTTP proxying
- Stores config in `app.state` for routers to access

**`apps/gateway/config.py`**
- `GatewayConfig` dataclass with validation
- Environment variables prefixed with `GATEWAY_`
- Key settings:
  - `GATEWAY_MEDIA_MOVER_URL` → `http://10.0.4.130:8083`
  - `GATEWAY_NGINX_MEDIA_URL` → `http://10.0.4.130:8082`
  - `GATEWAY_DATABASE_URL` → PostgreSQL on Ubuntu 1
  - `GATEWAY_API_PORT` → `8000`

**`apps/gateway/.env.template`**
- Template for operators to configure the gateway
- Documents all available environment variables

**`apps/gateway/README.md`**
- Architecture diagram
- Configuration guide
- Deployment instructions
- Troubleshooting tips

### 2. Deployment Scripts

**`start_gateway.sh`**
- Activates virtualenv
- Loads environment from `apps/gateway/.env`
- Sets default values
- Runs `uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8000`

**`systemd/reachy-gateway.service`**
- systemd unit file for Ubuntu 2
- Auto-restart on failure
- Logs to journalctl
- Runs as `rusty_admin` user

### 3. Updated Gateway Router

**`apps/api/routers/gateway.py`**
- Updated all proxy endpoints to use `app.state.http_client` and `app.state.config`
- Falls back to module-level defaults if not in gateway app context
- Works in both:
  - Gateway app (Ubuntu 2) - uses `app.state`
  - Media Mover app (Ubuntu 1) - uses module defaults (though not typically used)

### 4. Tests

**`tests/test_gateway_app.py`**
- Unit tests for `GatewayConfig` validation
- Integration tests for gateway endpoints
- Tests for password masking in logs
- Tests for API version header enforcement

### 5. Documentation

**`DEPLOYMENT_UBUNTU2.md`**
- Complete deployment checklist
- Step-by-step instructions for:
  - Gateway service setup
  - Streamlit UI setup
  - Nginx reverse proxy (optional)
- Verification tests
- Troubleshooting guide

**`GATEWAY_SUMMARY.md`** (this file)
- Overview of the implementation
- Architecture decisions
- File inventory

## How It Works

### On Ubuntu 1 (Media Mover)
```bash
# Start Media Mover
./start_media_api.sh
# → Runs apps/api/app/main.py on port 8083
# → Has direct access to /mnt/videos
# → Serves media_v1, promote, dialogue routers
```

### On Ubuntu 2 (Gateway)
```bash
# Start Gateway
./start_gateway.sh
# → Runs apps/gateway/main.py on port 8000
# → No filesystem access needed
# → Serves only gateway router (proxying)
# → Forwards requests to Ubuntu 1
```

### Request Flow

```
Streamlit UI (Ubuntu 2:8501)
    │
    ▼
Gateway (Ubuntu 2:8000)
    │ apps/gateway/main.py
    │ ├─ Loads apps/api/routers/gateway.py
    │ └─ Proxies via httpx.AsyncClient
    │
    ▼
Media Mover (Ubuntu 1:8083)
    │ apps/api/app/main.py
    │ ├─ Direct filesystem access (/mnt/videos)
    │ └─ Returns video metadata, thumbnails, etc.
    │
    ▼
Response flows back to UI
```

## Configuration Comparison

### Media Mover (Ubuntu 1)
```bash
# apps/api/.env
REACHY_VIDEOS_ROOT=/mnt/videos
REACHY_API_PORT=8083
MEDIA_MOVER_ENABLE_CORS=true
```

### Gateway (Ubuntu 2)
```bash
# apps/gateway/.env
GATEWAY_MEDIA_MOVER_URL=http://10.0.4.130:8083
GATEWAY_NGINX_MEDIA_URL=http://10.0.4.130:8082
GATEWAY_DATABASE_URL=postgresql+asyncpg://reachy_app:reachy_app@10.0.4.130:5432/reachy_local
GATEWAY_API_PORT=8000
GATEWAY_ENABLE_CORS=true
GATEWAY_UI_ORIGINS=http://localhost:8501,http://10.0.4.140:8501
```

**Key difference:** Gateway has **no filesystem paths**, only **upstream URLs**.

## Testing the Gateway

### 1. Manual Test
```bash
cd /home/rusty_admin/projects/reachy_08.4.2
source venv/bin/activate
./start_gateway.sh
```

In another terminal:
```bash
curl http://localhost:8000/health        # Should return "ok"
curl http://localhost:8000/ready         # Should return "ready"
curl http://localhost:8000/metrics       # Should return Prometheus metrics
```

### 2. Unit Tests
```bash
pytest tests/test_gateway_app.py -v
```

### 3. Integration Test (requires Media Mover running on Ubuntu 1)
```bash
# Test proxying
curl -X POST http://localhost:8000/api/events/emotion \
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

Expected: `202 Accepted`

## Next Steps

1. **Deploy Gateway on Ubuntu 2:**
   ```bash
   # Copy env template
   cp apps/gateway/.env.template apps/gateway/.env
   
   # Edit with your values
   nano apps/gateway/.env
   
   # Test manually
   ./start_gateway.sh
   
   # Install as service
   sudo cp systemd/reachy-gateway.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now reachy-gateway.service
   ```

2. **Verify Connectivity:**
   ```bash
   # From Ubuntu 2
   curl http://localhost:8000/health
   
   # From Ubuntu 1
   curl http://10.0.4.140:8000/health
   ```

3. **Deploy Streamlit UI** (see `DEPLOYMENT_UBUNTU2.md` section 2)

4. **Set Up Nginx** (optional, see `DEPLOYMENT_UBUNTU2.md` section 3)

5. **Configure Jetson** to send events to `http://10.0.4.140:8000/api/events/emotion`

## Benefits Achieved

✅ **Clear separation** - Gateway and Media Mover are distinct apps  
✅ **Minimal dependencies** - Gateway doesn't load filesystem code  
✅ **Easy testing** - Isolated unit tests for gateway  
✅ **Production-ready** - systemd service, logging, health checks  
✅ **Documented** - README, deployment guide, troubleshooting  
✅ **Flexible** - Can run both apps on same machine if needed (different ports)  

## Files Modified/Created

### Created
- `apps/gateway/__init__.py`
- `apps/gateway/main.py`
- `apps/gateway/config.py`
- `apps/gateway/.env.template`
- `apps/gateway/README.md`
- `start_gateway.sh`
- `systemd/reachy-gateway.service`
- `tests/test_gateway_app.py`
- `DEPLOYMENT_UBUNTU2.md`
- `GATEWAY_SUMMARY.md`

### Modified
- `apps/api/routers/gateway.py` - Updated to use `app.state` for config/client

### Unchanged
- `apps/api/app/main.py` - Media Mover entry point (Ubuntu 1)
- `apps/api/app/config.py` - Media Mover config (Ubuntu 1)
- All other Media Mover routers and services
