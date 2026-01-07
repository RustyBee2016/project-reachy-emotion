# Gateway Proxy Analysis and Resolution

**Date:** 2025-11-19  
**Issue:** Gateway API returns 404 for Media Mover endpoints  
**Root Cause:** Gateway does not have proxy routes configured

---

## Problem Statement

When testing Gateway API proxy routes, both requests return 404:

```bash
# Test 1: Media list endpoint
curl -i "http://10.0.4.140:8000/api/v1/media/list?split=temp&limit=20&offset=0"
# Result: HTTP/1.1 404 Not Found

# Test 2: Promotion endpoint
curl -i "http://10.0.4.140:8000/api/v1/promote/stage" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: test-key-001' \
  -d '{"video_ids":["uuid-1"],"label":"happy","dry_run":true}'
# Result: HTTP/1.1 404 Not Found
```

---

## Root Cause Analysis

### Gateway API Current Routes

The Gateway API (`src/gateway/main.py`) only implements these routes:

1. **Health/Observability:**
   - `GET /health`
   - `GET /ready`
   - `GET /metrics`

2. **Direct Endpoints:**
   - `POST /api/events/emotion` - Emotion events from Jetson
   - `POST /api/promote` - Legacy promotion endpoint

### Missing Routes

The Gateway **does NOT** have proxy routes for:
- ❌ `/api/v1/media/*` - Media Mover endpoints
- ❌ `/api/v1/promote/*` - New v1 promotion endpoints
- ❌ `/api/v1/dialogue/*` - Dialogue endpoints
- ❌ `/api/v1/health` - Media Mover health check

---

## Architecture Clarification

### Current Architecture

```
┌────────────────────────────┐    ┌────────────────────────────┐
│  Ubuntu 2 (10.0.4.140)     │    │  Ubuntu 1 (10.0.4.130)     │
│  Gateway API :8000         │    │  Media Mover API :8083     │
├────────────────────────────┤    ├────────────────────────────┤
│                            │    │                            │
│  Routes:                   │    │  Routes:                   │
│  • /health                 │    │  • /api/v1/health          │
│  • /ready                  │    │  • /api/v1/ready           │
│  • /metrics                │    │  • /api/v1/media/*         │
│  • /api/events/emotion     │    │  • /api/v1/promote/*       │
│  • /api/promote (legacy)   │    │  • /api/v1/dialogue/*      │
│                            │    │  • /metrics                │
│  ❌ NO PROXY ROUTES        │    │                            │
│                            │    │                            │
└────────────────────────────┘    └────────────────────────────┘
```

### Expected Behavior

**Option 1: Direct Access (Current Working Solution)**
```bash
# Access Media Mover API directly
curl http://10.0.4.130:8083/api/v1/media/list
curl http://10.0.4.130:8083/api/v1/promote/stage
```

**Option 2: Gateway Proxy (Requires Implementation)**
```bash
# Access through Gateway (would proxy to Media Mover)
curl http://10.0.4.140:8000/api/v1/media/list
curl http://10.0.4.140:8000/api/v1/promote/stage
```

---

## Why Gateway Proxy Might Not Be Needed

### Current Working Configuration

The system **already works correctly** with direct access:

1. **n8n workflows** can call Media Mover directly:
   ```
   http://10.0.4.130:8083/api/v1/media/list
   ```

2. **Streamlit UI** can call Media Mover directly:
   ```python
   MEDIA_MOVER_URL = "http://10.0.4.130:8083"
   ```

3. **Jetson device** sends emotion events to Gateway:
   ```
   http://10.0.4.140:8000/api/events/emotion
   ```

### When Gateway Proxy Would Be Useful

Gateway proxy routes would be beneficial if:

1. **Single Entry Point:** All external clients should only know about Gateway
2. **Load Balancing:** Gateway distributes requests across multiple Media Mover instances
3. **Authentication:** Gateway handles auth before forwarding to Media Mover
4. **Rate Limiting:** Gateway enforces rate limits
5. **Request Transformation:** Gateway modifies requests/responses

---

## Solution Options

### Option 1: Keep Current Architecture (Recommended)

**Status:** ✅ Already working

**Approach:**
- Clients access Media Mover API directly on port 8083
- Gateway handles only Jetson emotion events
- No changes needed

**Pros:**
- Already implemented and tested
- Simpler architecture
- Lower latency (no proxy hop)
- Easier to debug

**Cons:**
- Clients need to know about two services
- No centralized auth/rate limiting

**Configuration:**
```bash
# n8n workflows
MEDIA_MOVER_BASE_URL=http://10.0.4.130:8083

# Streamlit UI
REACHY_API_BASE=http://10.0.4.130:8083

# Jetson device
GATEWAY_URL=http://10.0.4.140:8000
```

---

### Option 2: Implement Gateway Proxy Routes

**Status:** ⚠️ Requires implementation

**Approach:**
- Add proxy routes to Gateway
- Forward `/api/v1/*` requests to Media Mover
- Maintain backward compatibility

**Implementation Required:**

1. **Add httpx dependency to Gateway:**
   ```bash
   pip install httpx
   ```

2. **Add proxy routes to `src/gateway/main.py`:**
   ```python
   import httpx
   
   MEDIA_MOVER_URL = os.getenv("MEDIA_MOVER_URL", "http://10.0.4.130:8083")
   
   @app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
   async def proxy_to_media_mover(request: Request, path: str):
       """Proxy all /api/v1/* requests to Media Mover API."""
       async with httpx.AsyncClient() as client:
           url = f"{MEDIA_MOVER_URL}/api/v1/{path}"
           
           # Forward headers
           headers = dict(request.headers)
           headers.pop("host", None)
           
           # Forward request
           response = await client.request(
               method=request.method,
               url=url,
               params=request.query_params,
               headers=headers,
               content=await request.body(),
           )
           
           # Return response
           return Response(
               content=response.content,
               status_code=response.status_code,
               headers=dict(response.headers),
           )
   ```

3. **Add environment variable to Gateway .env:**
   ```bash
   MEDIA_MOVER_URL=http://10.0.4.130:8083
   ```

4. **Update client configurations:**
   ```bash
   # All clients now use Gateway
   REACHY_API_BASE=http://10.0.4.140:8000
   ```

**Pros:**
- Single entry point for all APIs
- Centralized auth/rate limiting possible
- Easier client configuration

**Cons:**
- Additional latency (proxy hop)
- More complex debugging
- Requires implementation and testing
- Gateway becomes single point of failure

---

## Environment File Analysis

### Current .env File Status

**File:** `apps/api/.env`

**Comparison with template:**
- ✅ Correct port: `REACHY_API_PORT=8083`
- ✅ Correct Gateway: `REACHY_GATEWAY_HOST=10.0.4.140`, `REACHY_GATEWAY_PORT=8000`
- ⚠️ Different database: Uses `reachy_emotion` DB with different credentials
- ❌ No WebSocket/Token variables

**Missing Variables:**

The `.env` file does **not** contain:
- WebSocket configuration
- Authentication tokens
- API keys

This is **normal** if:
1. WebSocket auth is not yet implemented
2. API is currently open (no auth required)
3. Auth will be added later

---

## Recommendations

### Immediate (No Changes Needed)

**Keep current architecture:**

1. ✅ Media Mover API accessible directly on port 8083
2. ✅ Gateway handles Jetson emotion events on port 8000
3. ✅ All tests use correct ports (8083 for Media Mover)

**Test commands:**
```bash
# ✅ CORRECT - Direct access to Media Mover
curl http://10.0.4.130:8083/api/v1/media/list?split=temp
curl http://10.0.4.130:8083/api/v1/promote/stage \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: test-001' \
  -d '{"video_ids":["uuid-1"],"label":"happy","dry_run":true}'

# ✅ CORRECT - Gateway health check
curl http://10.0.4.140:8000/health

# ❌ INCORRECT - Gateway does not proxy these routes
curl http://10.0.4.140:8000/api/v1/media/list  # Returns 404
```

### Future Enhancement (Optional)

If you want Gateway to proxy Media Mover routes:

1. Implement proxy routes in `src/gateway/main.py`
2. Add `httpx` dependency
3. Configure `MEDIA_MOVER_URL` in Gateway .env
4. Update client configurations to use Gateway URL
5. Test thoroughly
6. Update documentation

---

## .env File Recommendations

### Do NOT Replace .env with .env.template

**Reason:** Your current `.env` has:
- Correct database credentials for your environment
- Working configuration that has been tested

**Action:** Keep your current `.env` file

### Optional: Add Comments from Template

If you want better documentation in your `.env`:

```bash
# Backup current .env
cp apps/api/.env apps/api/.env.backup

# Manually add comments from template while keeping your values
# DO NOT copy the entire template
```

### Add Missing Variables (If Needed)

If you plan to implement WebSocket auth or API tokens:

```bash
# Add to apps/api/.env
REACHY_WS_AUTH_ENABLED=false
REACHY_API_TOKEN=your-secret-token-here
```

---

## Summary

### Current Status

✅ **System is working correctly**
- Media Mover API: `http://10.0.4.130:8083` ✓
- Gateway API: `http://10.0.4.140:8000` ✓
- All tests passing with correct ports ✓

### Gateway 404 Errors

❌ **Expected behavior** - Gateway does not have proxy routes

**Solution:** Use direct access to Media Mover API:
```bash
# Use this (works)
curl http://10.0.4.130:8083/api/v1/media/list

# Not this (returns 404)
curl http://10.0.4.140:8000/api/v1/media/list
```

### .env File

✅ **Keep your current .env file** - It has correct configuration

❌ **Do NOT replace with template** - You'll lose your database credentials

### Next Steps

**No action required** - System is working as designed

**Optional:** Implement Gateway proxy routes if you want single entry point architecture

---

## Quick Reference

```
┌─────────────────────────────────────────────────────┐
│              WORKING CONFIGURATION                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Media Mover API (Direct Access):                   │
│    ✅ http://10.0.4.130:8083/api/v1/*               │
│                                                     │
│  Gateway API (Emotion Events Only):                 │
│    ✅ http://10.0.4.140:8000/api/events/emotion     │
│    ✅ http://10.0.4.140:8000/health                 │
│                                                     │
│  Gateway Proxy (NOT IMPLEMENTED):                   │
│    ❌ http://10.0.4.140:8000/api/v1/*               │
│       (Returns 404 - expected behavior)             │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

**Conclusion:** The Gateway 404 errors are expected because proxy routes are not implemented. The system works correctly with direct access to Media Mover API on port 8083. No changes are needed unless you want to implement Gateway proxy functionality.
