# Configuration Update Guide - Endpoint System v0.08.4.3

**Date**: 2025-11-14  
**Purpose**: Update configuration files to use new v1 endpoint system

---

## ⚠️ Action Required

The endpoint system has been rewritten with versioned APIs. Configuration files need updating.

---

## 1. API Service Configuration

### Create `/apps/api/.env`

```bash
# Copy template
cp apps/api/.env.template apps/api/.env

# Edit with your values
nano apps/api/.env
```

**Key Settings**:
- `REACHY_API_BASE=http://localhost:8083` (default, change if needed)
- `REACHY_VIDEOS_ROOT=/media/rusty_admin/project_data/reachy_emotion/videos`
- `REACHY_DATABASE_URL=postgresql+asyncpg://reachy_app:reachy_app@localhost:5432/reachy_local`
- `REACHY_ENABLE_LEGACY_ENDPOINTS=true` (for backward compatibility)

---

## 2. Web UI Configuration

### Update `/apps/web/.env`

**Current .env has old format**. Update to match template:

```bash
# Backup current .env (contains API keys)
cp apps/web/.env apps/web/.env.backup

# Copy template
cp apps/web/.env.template apps/web/.env

# Restore API keys from backup
# LUMAAI_API_KEY=... (copy from backup)
# N8N_INGEST_TOKEN=... (copy from backup)
```

**Required Settings**:
```bash
# API Configuration
REACHY_API_BASE=http://localhost:8083
REACHY_GATEWAY_BASE=http://10.0.4.140:8000

# n8n Configuration
N8N_HOST=10.0.4.130
N8N_PORT=5678
N8N_WEBHOOK_PATH=webhook/video_gen_hook
N8N_INGEST_TOKEN=tkn3848

# Luma AI Configuration
LUMAAI_API_KEY=<your_key_here>
```

---

## 3. Endpoint Changes Summary

### Old Endpoints (Deprecated)
```
GET  /api/videos/list
GET  /api/media/videos/list
POST /api/media/promote
GET  /media/health
```

### New V1 Endpoints (Production)
```
GET  /api/v1/health
GET  /api/v1/ready
GET  /api/v1/media/list
GET  /api/v1/media/{video_id}
GET  /api/v1/media/{video_id}/thumb
POST /api/v1/promote/stage
POST /api/v1/promote/sample
POST /api/v1/promote/reset-manifest
```

**Response Format Change**:
```json
// Old format
{
  "items": [...],
  "total": 42
}

// New v1 format
{
  "status": "success",
  "data": {
    "items": [...],
    "pagination": {
      "total": 42,
      "limit": 50,
      "offset": 0,
      "has_more": false
    }
  },
  "meta": {
    "correlation_id": "uuid",
    "timestamp": "2025-11-14T...",
    "version": "v1"
  }
}
```

---

## 4. Client Code Updates

The `apps/web/api_client.py` has been updated to use v1 endpoints automatically.

**No code changes required** - the client handles response unwrapping for backward compatibility.

---

## 5. Verification Steps

### Test API Service
```bash
# Start service
./scripts/service-start.sh

# Check health
curl http://localhost:8083/api/v1/health

# List videos
curl "http://localhost:8083/api/v1/media/list?split=temp&limit=10"

# Check service status
./scripts/service-status.sh
```

### Test Web UI
```bash
# Start Streamlit
cd apps/web
streamlit run landing_page.py

# Verify:
# - Videos load correctly
# - Thumbnails display
# - Promotion works
```

---

## 6. Migration Timeline

### Phase 1: Compatibility Mode (Current)
- ✅ V1 endpoints active
- ✅ Legacy endpoints active
- ✅ Both formats work
- **Action**: Update .env files

### Phase 2: V1 Only (Future)
- Set `REACHY_ENABLE_LEGACY_ENDPOINTS=false`
- Remove legacy endpoint support
- **Timeline**: After all clients migrated

---

## 7. Troubleshooting

### Issue: Connection Refused
```bash
# Check if service is running
./scripts/service-status.sh

# Check port
sudo lsof -i :8083

# Restart service
./scripts/service-restart.sh
```

### Issue: 404 Errors
- Verify using `/api/v1/` prefix
- Check `REACHY_API_BASE` in .env
- Ensure service restarted after config changes

### Issue: Empty Response
- Check `REACHY_VIDEOS_ROOT` path exists
- Verify directory permissions
- Check logs: `journalctl -u fastapi-media.service -f`

---

## 8. Configuration Validation

```bash
# Validate API config
python -c "from apps.api.app.config import load_and_validate_config; load_and_validate_config()"

# Expected output:
# Configuration validated successfully
```

---

## 9. Environment Variables Reference

### API Service (`apps/api/.env`)
| Variable | Default | Purpose |
|----------|---------|---------|
| `REACHY_API_HOST` | `0.0.0.0` | Bind address |
| `REACHY_API_PORT` | `8083` | Service port |
| `REACHY_VIDEOS_ROOT` | `/media/.../videos` | Storage path |
| `REACHY_DATABASE_URL` | `postgresql+asyncpg://...` | DB connection |
| `REACHY_NGINX_HOST` | `10.0.4.130` | Nginx host |
| `REACHY_NGINX_PORT` | `8082` | Nginx port |
| `REACHY_ENABLE_CORS` | `true` | Enable CORS |
| `REACHY_ENABLE_LEGACY_ENDPOINTS` | `true` | Legacy support |

### Web UI (`apps/web/.env`)
| Variable | Default | Purpose |
|----------|---------|---------|
| `REACHY_API_BASE` | `http://localhost:8083` | API URL |
| `REACHY_GATEWAY_BASE` | `http://10.0.4.140:8000` | Gateway URL |
| `N8N_HOST` | `10.0.4.130` | n8n host |
| `N8N_PORT` | `5678` | n8n port |
| `LUMAAI_API_KEY` | - | Luma API key |

---

## 10. Quick Reference Commands

```bash
# Service Management
./scripts/service-start.sh      # Start service
./scripts/service-stop.sh       # Stop service
./scripts/service-restart.sh    # Restart service
./scripts/service-status.sh     # Check status

# Configuration
cp apps/api/.env.template apps/api/.env
cp apps/web/.env.template apps/web/.env.new

# Testing
python -m pytest tests/test_config.py -v
python -m pytest tests/test_v1_endpoints.py -v
python -m pytest tests/test_integration_full.py -v

# Health Checks
curl http://localhost:8083/api/v1/health
curl http://localhost:8083/api/v1/ready
```

---

## 11. Documentation References

- **API Reference**: `API_ENDPOINT_REFERENCE.md`
- **Endpoint Rewrite**: `ENDPOINT_REWRITE_PROJECT_COMPLETE.md`
- **Architecture**: `ENDPOINT_ARCHITECTURE_ANALYSIS.md`
- **Service Scripts**: `scripts/README.md` (if exists)

---

**Last Updated**: 2025-11-14  
**Version**: 0.08.4.3  
**Status**: Configuration update required ⚠️
