# Service Restart Checklist — Reachy_Local_08.4.2

**Date**: 2025-11-18  
**Purpose**: Fix database configuration and enable dialogue endpoints

---

## Current Status

### ✅ Completed
- [x] Fixed circular import in `dialogue.py`
- [x] Updated `alembic.ini` with correct database credentials
- [x] Verified database tables exist in `reachy_emotion` database
- [x] Confirmed alembic migrations are up to date (20251028_000000)

### ⚠️ Pending
- [ ] Update `.env` file with correct database URL
- [ ] Restart uvicorn service on Ubuntu 1 port 8083
- [ ] Verify dialogue endpoints are accessible
- [ ] Re-test promotion endpoints
- [ ] Verify Gateway on Ubuntu 2

---

## Step-by-Step Instructions

### Step 1: Update Database Configuration in .env

**File**: `/home/rusty_admin/projects/reachy_08.4.2/apps/api/.env`

**Current (INCORRECT)**:
```bash
REACHY_DATABASE_URL=postgresql+asyncpg://reachy_app:reachy_app@localhost:5432/reachy_local
```

**Should be (CORRECT)**:
```bash
REACHY_DATABASE_URL=postgresql+asyncpg://reachy_dev:tweetwd4959@/reachy_emotion?host=/var/run/postgresql
```

**Quick fix command**:
```bash
cd /home/rusty_admin/projects/reachy_08.4.2
sed -i 's|REACHY_DATABASE_URL=.*|REACHY_DATABASE_URL=postgresql+asyncpg://reachy_dev:tweetwd4959@/reachy_emotion?host=/var/run/postgresql|' apps/api/.env
```

**Verify the change**:
```bash
grep REACHY_DATABASE_URL apps/api/.env
```

---

### Step 2: Restart Uvicorn Service (Ubuntu 1, Port 8083)

**Find the current process**:
```bash
ps aux | grep "uvicorn.*8083" | grep -v grep
# Output: rusty_a+   20867  ...
```

**Stop the service**:
```bash
kill 20867
```

**Restart with correct configuration**:
```bash
cd /home/rusty_admin/projects/reachy_08.4.2
source venv/bin/activate
uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8083 --reload
```

**Alternative: Run in background with nohup**:
```bash
cd /home/rusty_admin/projects/reachy_08.4.2
source venv/bin/activate
nohup uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8083 --reload > /tmp/uvicorn_8083.log 2>&1 &
```

**Verify service started**:
```bash
# Wait a few seconds, then:
curl -s http://localhost:8083/api/v1/health | python3 -m json.tool
```

---

### Step 3: Verify Dialogue Endpoints

**Test dialogue health endpoint**:
```bash
curl -s http://localhost:8083/api/v1/dialogue/health | python3 -m json.tool
```

**Expected output**:
```json
{
  "status": "ok",
  "service": "dialogue",
  "correlation_id": "..."
}
```

**Test dialogue generation** (requires LM Studio running):
```bash
curl -s -X POST http://localhost:8083/api/v1/dialogue/generate \
  -H "Content-Type: application/json" \
  -d '{
    "emotion": "happy",
    "confidence": 0.85,
    "user_message": "Hello!"
  }' | python3 -m json.tool
```

**Check OpenAPI docs for dialogue routes**:
```bash
curl -s http://localhost:8083/openapi.json | \
  python3 -c "import sys,json; paths=json.load(sys.stdin)['paths']; print('\n'.join([p for p in sorted(paths.keys()) if 'dialogue' in p]))"
```

---

### Step 4: Re-test Promotion Endpoints

**Test stage endpoint (dry-run)**:
```bash
curl -s -w "\nHTTP Status: %{http_code}\n" \
  -X POST http://localhost:8083/api/v1/promote/stage \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-restart-001" \
  -d '{
    "video_ids": ["550e8400-e29b-41d4-a716-446655440000"],
    "label": "happy",
    "dry_run": true
  }' | python3 -m json.tool
```

**Expected output** (202 Accepted):
```json
{
  "status": "accepted",
  "data": {
    "staged_count": 0,
    "skipped_count": 0,
    "errors": ["Video not found: 550e8400-e29b-41d4-a716-446655440000"]
  }
}
```

**Test sample endpoint (dry-run)**:
```bash
curl -s -X POST http://localhost:8083/api/v1/promote/sample \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: test-restart-002" \
  -d '{
    "run_id": "test-run-001",
    "train_ratio": 0.8,
    "dry_run": true
  }' | python3 -m json.tool
```

---

### Step 5: Verify Gateway on Ubuntu 2

**On Ubuntu 2 terminal** (direct access):

**Check if service is running**:
```bash
ss -tlnp | grep 8000
ps aux | grep uvicorn | grep 8000
```

**Test locally**:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

**Check binding** (should be 0.0.0.0:8000, not 127.0.0.1:8000):
```bash
ss -tlnp | grep 8000
# Look for: 0.0.0.0:8000 (good) or 127.0.0.1:8000 (bad)
```

**If bound to 127.0.0.1, restart with correct binding**:
```bash
# Stop current service
pkill -f "uvicorn.*8000"

# Restart with 0.0.0.0
cd /path/to/gateway/project
uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8000 --reload
```

**Test from Ubuntu 1** (after fixing binding):
```bash
curl -s http://10.0.4.140:8000/health
```

---

## Verification Tests

After completing all steps, run these tests:

### Ubuntu 1 (localhost) Tests

```bash
# Health checks
curl -s http://localhost:8083/api/v1/health | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['status'])"
# Expected: healthy

curl -s http://localhost:8083/api/v1/ready | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['status'])"
# Expected: healthy

# Dialogue health
curl -s http://localhost:8083/api/v1/dialogue/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])"
# Expected: ok

# Media listing
curl -s "http://localhost:8083/api/v1/media/list?split=temp&limit=5" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])"
# Expected: success

# Metrics
curl -s http://localhost:8083/metrics | head -5
# Expected: # HELP promotion_operations_total ...

# PostgreSQL
pg_isready -h /var/run/postgresql -U reachy_dev -d reachy_emotion
# Expected: accepting connections

# n8n
curl -s http://localhost:5678/ | grep -q "<!DOCTYPE html>" && echo "n8n OK" || echo "n8n FAIL"
# Expected: n8n OK

# Nginx
curl -s http://localhost:8082/ | grep -q "nginx" && echo "Nginx OK" || echo "Nginx FAIL"
# Expected: Nginx OK
```

### Ubuntu 2 (remote) Tests

```bash
# From Ubuntu 1, test Gateway
curl -s --max-time 5 http://10.0.4.140:8000/health
# Expected: "ok" or JSON with status

curl -s --max-time 5 http://10.0.4.140:8000/ready
# Expected: "ready" or JSON with status
```

---

## Expected Results

### ✅ Success Indicators

- [ ] Health endpoint returns `{"status":"success","data":{"status":"healthy"}}`
- [ ] Dialogue health endpoint returns `{"status":"ok","service":"dialogue"}`
- [ ] OpenAPI docs include `/api/v1/dialogue/generate` and `/api/v1/dialogue/health`
- [ ] Promotion stage endpoint returns 202 (not 500)
- [ ] Gateway on Ubuntu 2 accessible from Ubuntu 1
- [ ] All services respond within 5 seconds

### ❌ Failure Indicators

- [ ] 500 Internal Server Error on promotion endpoints
- [ ] 404 Not Found on dialogue endpoints
- [ ] Connection timeout to Ubuntu 2 Gateway
- [ ] Database connection errors in logs
- [ ] Import errors when starting uvicorn

---

## Troubleshooting

### Issue: Promotion endpoints still return 500

**Check**:
```bash
# Verify .env was updated
grep REACHY_DATABASE_URL apps/api/.env

# Verify service restarted (check process start time)
ps -p $(pgrep -f "uvicorn.*8083") -o lstart=

# Check database connection
PGPASSWORD=tweetwd4959 psql -h /var/run/postgresql -U reachy_dev -d reachy_emotion -c "SELECT 1"
```

### Issue: Dialogue endpoints return 404

**Check**:
```bash
# Verify dialogue router is imported
curl -s http://localhost:8083/openapi.json | grep -q "dialogue" && echo "Found" || echo "Missing"

# Check for import errors in logs
journalctl -u uvicorn -n 50 --no-pager | grep -i error
```

### Issue: Gateway not accessible from Ubuntu 1

**Check on Ubuntu 2**:
```bash
# Verify binding
ss -tlnp | grep 8000

# Test locally
curl http://localhost:8000/health

# Check firewall
sudo iptables -L -n | grep 8000
```

---

## Rollback Plan

If issues occur after restart:

1. **Revert .env changes**:
   ```bash
   cd /home/rusty_admin/projects/reachy_08.4.2
   git checkout apps/api/.env
   ```

2. **Restart with old configuration**:
   ```bash
   kill $(pgrep -f "uvicorn.*8083")
   uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8083 --reload
   ```

3. **Check git history for working config**:
   ```bash
   git log --oneline apps/api/.env
   git show <commit>:apps/api/.env
   ```

---

## Next Steps After Successful Restart

1. **Run comprehensive endpoint tests** (ENDPOINT_TEST_PLAN.md)
2. **Test LM Studio integration** (requires LM Studio running on port 1234)
3. **Test WebSocket cue streaming** (requires WebSocket client)
4. **Verify n8n workflows** can call endpoints
5. **Document final port mapping** in SERVICE_PORT_MAPPING.md

---

**Last Updated**: 2025-11-18 02:15 UTC-05:00  
**Status**: Ready for execution
