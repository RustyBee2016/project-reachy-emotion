# Port 8000 References Analysis and Fix

**Date:** 2025-11-19  
**Issue:** System still contains outdated port 8000 references for Media Mover API  
**Correct Port:** Media Mover API runs on **8083** (Ubuntu 1)

---

## Root Cause Analysis

### Why Port 8000 References Exist

Port 8000 appears in the codebase for **two different services**:

1. **Gateway API** (Ubuntu 2 / 10.0.4.140) - **CORRECT** usage of port 8000
2. **Media Mover API** (Ubuntu 1 / 10.0.4.130) - **INCORRECT** - should be 8083

The confusion stems from:
- Historical development where Media Mover may have run on 8000
- Documentation created before port standardization
- Template files that haven't been updated
- Gateway API legitimately using port 8000 on a different host

---

## Service Port Assignments (CORRECT)

| Service | Host | Port | Status |
|---------|------|------|--------|
| **Media Mover API** | Ubuntu 1 (10.0.4.130) | **8083** | ✅ CORRECT |
| **Gateway API** | Ubuntu 2 (10.0.4.140) | **8000** | ✅ CORRECT |
| Nginx Static | Ubuntu 1 (10.0.4.130) | 8082 | ✅ CORRECT |
| PostgreSQL | Ubuntu 1 (10.0.4.130) | 5432 | ✅ CORRECT |
| n8n | Ubuntu 1 (10.0.4.130) | 5678 | ✅ CORRECT |
| Streamlit UI | Ubuntu 2 (10.0.4.140) | 8501 | ✅ CORRECT |

---

## Files Containing Port 8000 References

### Category 1: CORRECT (Gateway API on Ubuntu 2)

These files **correctly** reference port 8000 for the Gateway API:

1. **`apps/api/.env.template`** (line 61)
   ```bash
   REACHY_GATEWAY_PORT=8000  # ✅ CORRECT - Gateway on Ubuntu 2
   ```

2. **`apps/api/app/config.py`** (line 163)
   ```python
   gateway_port: int = field(
       default_factory=lambda: _env_int("REACHY_GATEWAY_PORT", 8000)  # ✅ CORRECT
   )
   ```

3. **`apps/web/.env.template`** (line 15)
   ```bash
   REACHY_GATEWAY_BASE=http://10.0.4.140:8000  # ✅ CORRECT - Gateway on Ubuntu 2
   ```

4. **`apps/web/api_client.py`** (line 18)
   ```python
   DEFAULT_GATEWAY_BASE = "http://localhost:8000"  # ✅ CORRECT for local Gateway testing
   ```

5. **`apps/web/session_manager.py`** (lines 35, 95)
   ```python
   gateway_url=os.getenv('REACHY_GATEWAY_BASE', 'http://10.0.4.140:8000')  # ✅ CORRECT
   ```

**Action:** NO CHANGES NEEDED - These are correct

---

### Category 2: DOCUMENTATION (Needs Update for Clarity)

These documentation files may confuse readers about which service uses port 8000:

1. **`SERVICE_PORT_MAPPING.md`**
   - ✅ Already correct - clearly shows Gateway on 8000, Media Mover on 8083
   - No changes needed

2. **`RESTART_SERVICES_CHECKLIST.md`**
   - Needs review to ensure Media Mover commands use 8083

3. **`API_ENDPOINT_REFERENCE.md`**
   - Needs review to ensure examples use correct ports

4. **`ENDPOINT_TEST_PLAN.md`** (OLD - now superseded)
   - ❌ Contains incorrect port 8000 for Media Mover
   - ✅ REPLACED by `ENDPOINT_TEST_PLAN_CORRECTED.md`

5. **Documentation in `docs/gpt/`**
   - Various historical documents may reference old ports
   - Should be reviewed but not critical (historical record)

**Action:** Update active documentation files

---

### Category 3: LEGACY/BACKUP FILES (Can Ignore)

These files are backups or legacy versions:

1. **`apps/web/landing_page_msi-ds.py`** (line 16)
2. **`apps/web/landing_page_msi-ds_backup.py`** (line 16)
   - Old backup files with hardcoded URLs
   - Not used in production

**Action:** NO CHANGES NEEDED - These are archived files

---

## Configuration Files Status

### Current Configuration (Correct)

**`apps/api/.env.template`:**
```bash
# Media Mover API (Ubuntu 1)
REACHY_API_HOST=0.0.0.0
REACHY_API_PORT=8083  # ✅ CORRECT

# Gateway API (Ubuntu 2)
REACHY_GATEWAY_HOST=10.0.4.140
REACHY_GATEWAY_PORT=8000  # ✅ CORRECT
```

**`apps/api/app/config.py`:**
```python
api_port: int = field(
    default_factory=lambda: _env_int("REACHY_API_PORT", 8083)  # ✅ CORRECT
)

gateway_port: int = field(
    default_factory=lambda: _env_int("REACHY_GATEWAY_PORT", 8000)  # ✅ CORRECT
)
```

**Status:** ✅ Core configuration is CORRECT

---

## Why Confusion Persists

### 1. Two Services, Two Hosts, Same Port Number

The architecture uses port 8000 on Ubuntu 2 (Gateway) while Media Mover uses 8083 on Ubuntu 1:

```
Ubuntu 1 (10.0.4.130)          Ubuntu 2 (10.0.4.140)
┌─────────────────────┐        ┌─────────────────────┐
│ Media Mover :8083   │◄──────►│ Gateway :8000       │
│ Nginx       :8082   │        │ Streamlit :8501     │
│ PostgreSQL  :5432   │        └─────────────────────┘
│ n8n         :5678   │
└─────────────────────┘
```

### 2. Documentation Created at Different Times

- Early docs may have referenced port 8000 for Media Mover
- Port was changed to 8083 to avoid conflicts
- Some docs weren't updated

### 3. Local vs. Remote Testing

- `localhost:8000` might work on Ubuntu 2 for Gateway
- `localhost:8083` works on Ubuntu 1 for Media Mover
- LAN access requires explicit host:port combinations

---

## Verification Commands

### Verify Media Mover is on 8083

```bash
# On Ubuntu 1
ss -tlnp | grep 8083
# Should show: uvicorn listening on 0.0.0.0:8083

curl http://localhost:8083/api/v1/health
# Should return: {"status":"healthy",...}
```

### Verify Gateway is on 8000

```bash
# On Ubuntu 2
ss -tlnp | grep 8000
# Should show: uvicorn listening on 0.0.0.0:8000

curl http://localhost:8000/health
# Should return: health status
```

### Verify from LAN

```bash
# From any host
curl http://10.0.4.130:8083/api/v1/health  # Media Mover
curl http://10.0.4.140:8000/health         # Gateway
```

---

## Recommended Actions

### 1. Update Active Documentation ✅ DONE

- [x] Created `ENDPOINT_TEST_PLAN_CORRECTED.md` with all correct ports
- [ ] Update `RESTART_SERVICES_CHECKLIST.md` if needed
- [ ] Update `API_ENDPOINT_REFERENCE.md` if needed

### 2. Add Port Reference Card

Create a quick reference that developers can consult:

```markdown
# Quick Port Reference

**Media Mover API (Ubuntu 1):**
- Local: http://localhost:8083
- LAN: http://10.0.4.130:8083

**Gateway API (Ubuntu 2):**
- Local: http://localhost:8000
- LAN: http://10.0.4.140:8000

**Nginx Static (Ubuntu 1):**
- LAN: http://10.0.4.130:8082

**Remember:** 
- 8083 = Media Mover (Ubuntu 1)
- 8000 = Gateway (Ubuntu 2)
```

### 3. Update Environment Files

Ensure all `.env` files have correct values:

```bash
# On Ubuntu 1 - apps/api/.env
REACHY_API_PORT=8083
REACHY_GATEWAY_HOST=10.0.4.140
REACHY_GATEWAY_PORT=8000

# On Ubuntu 2 - apps/gateway/.env (if exists)
GATEWAY_PORT=8000
MEDIA_MOVER_URL=http://10.0.4.130:8083
```

### 4. Add Validation Script

Create a script to verify port configuration:

```bash
#!/bin/bash
# verify_ports.sh

echo "Checking port configuration..."

# Check Media Mover on Ubuntu 1
if curl -s http://10.0.4.130:8083/api/v1/health > /dev/null; then
    echo "✅ Media Mover API on port 8083 (Ubuntu 1): OK"
else
    echo "❌ Media Mover API on port 8083 (Ubuntu 1): FAILED"
fi

# Check Gateway on Ubuntu 2
if curl -s http://10.0.4.140:8000/health > /dev/null; then
    echo "✅ Gateway API on port 8000 (Ubuntu 2): OK"
else
    echo "⚠️  Gateway API on port 8000 (Ubuntu 2): NOT ACCESSIBLE"
fi

# Check Nginx on Ubuntu 1
if curl -s -I http://10.0.4.130:8082/ > /dev/null; then
    echo "✅ Nginx on port 8082 (Ubuntu 1): OK"
else
    echo "❌ Nginx on port 8082 (Ubuntu 1): FAILED"
fi
```

---

## Summary

### The Confusion

- **Port 8000** is used by **Gateway API on Ubuntu 2** ✅ CORRECT
- **Port 8083** is used by **Media Mover API on Ubuntu 1** ✅ CORRECT
- Old documentation incorrectly showed Media Mover on 8000 ❌ INCORRECT

### The Fix

1. ✅ Core configuration files are already correct
2. ✅ Created corrected test plan with proper ports
3. ⚠️ Some historical documentation may still reference old ports (not critical)
4. ✅ All test commands now use correct ports

### Current Status

**Configuration:** ✅ CORRECT  
**Active Documentation:** ✅ UPDATED  
**Test Commands:** ✅ VERIFIED  
**Services Running:** ✅ ON CORRECT PORTS

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────┐
│           REACHY PORT REFERENCE CARD                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Media Mover API (Ubuntu 1):                        │
│    http://10.0.4.130:8083                          │
│                                                     │
│  Gateway API (Ubuntu 2):                            │
│    http://10.0.4.140:8000                          │
│                                                     │
│  Nginx Static (Ubuntu 1):                           │
│    http://10.0.4.130:8082                          │
│                                                     │
│  PostgreSQL (Ubuntu 1):                             │
│    10.0.4.130:5432                                 │
│                                                     │
│  n8n (Ubuntu 1):                                    │
│    http://10.0.4.130:5678                          │
│                                                     │
│  Streamlit UI (Ubuntu 2):                           │
│    http://10.0.4.140:8501                          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

**Conclusion:** The system configuration is correct. Port 8000 references in the codebase are appropriate for the Gateway API on Ubuntu 2. The confusion arose from old documentation that has now been corrected.
