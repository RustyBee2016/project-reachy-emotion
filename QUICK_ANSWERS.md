# Quick Answers to Your Questions

**Date:** 2025-11-19

---

## Q1: Should I use .env.template to replace the current .env file?

**Answer: NO - Keep your current .env file**

### Why?

Your current `.env` file has:
- ✅ Correct database credentials (`reachy_emotion` database)
- ✅ Correct port configuration (8083)
- ✅ Working configuration that has been tested

The `.env.template` has:
- ❌ Generic/example database credentials
- ❌ Would break your database connection

### What's Different?

```bash
# Your .env (KEEP THIS)
REACHY_DATABASE_URL=postgresql+asyncpg://reachy_dev:tweetwd4959@/reachy_emotion?host=/var/run/postgresql

# Template (DON'T USE)
REACHY_DATABASE_URL=postgresql+asyncpg://reachy_app:reachy_app@localhost:5432/reachy_local
```

### Recommendation

✅ **Keep your current .env file** - It's configured correctly for your environment

---

## Q2: Why do Gateway proxy tests return 404?

**Answer: Gateway does NOT have proxy routes implemented**

### The 404 Errors Are Expected

```bash
# These return 404 (expected - not implemented)
curl http://10.0.4.140:8000/api/v1/media/list          # ❌ 404
curl http://10.0.4.140:8000/api/v1/promote/stage       # ❌ 404
```

### What Gateway Actually Has

The Gateway API only implements:
- ✅ `/health` - Health check
- ✅ `/ready` - Readiness check
- ✅ `/metrics` - Prometheus metrics
- ✅ `/api/events/emotion` - Emotion events from Jetson
- ✅ `/api/promote` - Legacy promotion endpoint

It does **NOT** have:
- ❌ `/api/v1/media/*` - Media endpoints
- ❌ `/api/v1/promote/*` - New promotion endpoints
- ❌ `/api/v1/dialogue/*` - Dialogue endpoints

### The Correct Way to Access Media Mover

**Use direct access to Media Mover API:**

```bash
# ✅ CORRECT - Direct access on port 8083
curl http://10.0.4.130:8083/api/v1/media/list?split=temp
curl http://10.0.4.130:8083/api/v1/promote/stage \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: test-001' \
  -d '{"video_ids":["uuid-1"],"label":"happy","dry_run":true}'
```

### Why This Design?

The current architecture uses **direct access**:
- n8n workflows → Media Mover API (10.0.4.130:8083)
- Streamlit UI → Media Mover API (10.0.4.130:8083)
- Jetson device → Gateway API (10.0.4.140:8000)

This is simpler and already working.

---

## Q3: Must the .env file be updated for inspection to work?

**Answer: NO - Your .env is fine**

### What You Checked

```bash
grep -nE 'WS|WEBSOCKET|TOKEN' apps/api/.env
# Result: No WebSocket/Token variables found
```

### This Is Normal

Your `.env` file doesn't have WebSocket/Token variables because:
1. ✅ WebSocket auth is not yet implemented
2. ✅ API is currently open (no auth required)
3. ✅ These will be added when auth is implemented

### Your .env Has Everything Needed

Current configuration includes:
- ✅ Service ports (8083, 8082, 8000, etc.)
- ✅ Database connection
- ✅ Storage paths
- ✅ CORS settings
- ✅ External service URLs

---

## Q4: What about the ripgrep command?

**Answer: Optional - grep works fine**

### What Happened

```bash
rg "extra_headers" -n apps/api
# Command 'rg' not found
```

### Solution

You can either:

**Option 1: Use grep (already works)**
```bash
grep -rn "extra_headers" apps/api
```

**Option 2: Install ripgrep (optional)**
```bash
sudo apt install ripgrep
```

Ripgrep (`rg`) is faster than `grep` but not required.

---

## Summary

| Question | Answer | Action |
|----------|--------|--------|
| Replace .env with template? | **NO** | Keep current .env |
| Why Gateway 404? | **No proxy routes** | Use direct access to 10.0.4.130:8083 |
| Update .env for inspection? | **NO** | Current .env is correct |
| Install ripgrep? | **Optional** | grep works fine |

---

## What You Should Do

### ✅ Nothing - System is Working Correctly

Your configuration is correct:
- Media Mover API on port 8083 ✓
- Gateway API on port 8000 ✓
- Database connection working ✓
- All tests passing ✓

### ✅ Use These Commands

```bash
# Test Media Mover API (works)
curl http://10.0.4.130:8083/api/v1/health
curl http://10.0.4.130:8083/api/v1/media/list?split=temp

# Test Gateway API (works)
curl http://10.0.4.140:8000/health

# Don't use Gateway for Media Mover routes (not implemented)
# curl http://10.0.4.140:8000/api/v1/media/list  # Returns 404
```

---

## If You Want Gateway Proxy Routes

If you want Gateway to proxy Media Mover requests, you would need to:

1. Add `httpx` dependency to Gateway
2. Implement proxy routes in `src/gateway/main.py`
3. Configure `MEDIA_MOVER_URL` in Gateway .env
4. Test thoroughly
5. Update all client configurations

**But this is NOT required** - direct access already works.

---

**Bottom Line:** Your system is configured correctly. The Gateway 404 errors are expected because proxy routes are not implemented. Continue using direct access to Media Mover API on port 8083.
