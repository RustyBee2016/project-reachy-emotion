# Service Port Mapping — Reachy_Local_08.4.2

**Date**: 2025-11-18  
**Status**: Current Configuration

---

## Ubuntu 1 (10.0.4.130) — Model Host / Backend

| Port | Service | Status | Purpose | Notes |
|------|---------|--------|---------|-------|
| 5432 | PostgreSQL | ✅ RUNNING | Metadata database | Bound to 127.0.0.1 |
| 5678 | n8n | ✅ RUNNING | Workflow orchestration | Web UI accessible |
| 8081 | Legacy Uvicorn | ✅ RUNNING | Old project instance | From `/media/rusty_admin/project_data/reachy_emotion` |
| 8082 | Nginx | ✅ RUNNING | Static file server | Serves `/videos/*` and `/thumbs/*` |
| 8083 | Media Mover API | ✅ RUNNING | Primary FastAPI service | Current project, needs restart for dialogue endpoints |
| 1234 | LM Studio | ❓ UNKNOWN | LLM inference | OpenAI-compatible API (not tested) |

---

## Ubuntu 2 (10.0.4.140) — Gateway / Frontend

| Port | Service | Status | Purpose | Notes |
|------|---------|--------|---------|-------|
| 8000 | Gateway API | ❌ NOT ACCESSIBLE | External-facing API | Port open but not responding to HTTP |
| 8501 | Streamlit | ❓ UNKNOWN | Web UI | Not tested |

---

## Service Architecture

### Current Working Configuration (Ubuntu 1)

```
┌─────────────────────────────────────────────────────────┐
│                     Ubuntu 1 (10.0.4.130)               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐     ┌──────────────┐                │
│  │ PostgreSQL   │     │    n8n       │                │
│  │  :5432       │     │   :5678      │                │
│  └──────────────┘     └──────────────┘                │
│                                                         │
│  ┌──────────────┐     ┌──────────────┐                │
│  │    Nginx     │     │ Media Mover  │                │
│  │   :8082      │     │  API :8083   │                │
│  │  (static)    │     │  (FastAPI)   │                │
│  └──────────────┘     └──────────────┘                │
│                                                         │
│  ┌──────────────┐     ┌──────────────┐                │
│  │  LM Studio   │     │Legacy Service│                │
│  │   :1234      │     │    :8081     │                │
│  └──────────────┘     └──────────────┘                │
└─────────────────────────────────────────────────────────┘
```

### Expected Configuration (Per Documentation)

```
┌────────────────────────────┐    ┌────────────────────────────┐
│  Ubuntu 2 (10.0.4.140)     │    │  Ubuntu 1 (10.0.4.130)     │
│  Gateway / Frontend        │    │  Model Host / Backend      │
├────────────────────────────┤    ├────────────────────────────┤
│                            │    │                            │
│  ┌──────────────────────┐ │    │  ┌──────────────────────┐ │
│  │   Gateway API        │ │    │  │  Media Mover API     │ │
│  │     :8000            │◄├────┤►│      :8081/8083      │ │
│  │   (FastAPI)          │ │    │  │    (FastAPI)         │ │
│  └──────────────────────┘ │    │  └──────────────────────┘ │
│                            │    │                            │
│  ┌──────────────────────┐ │    │  ┌──────────────────────┐ │
│  │   Streamlit UI       │ │    │  │     LM Studio        │ │
│  │     :8501            │ │    │  │      :1234           │ │
│  └──────────────────────┘ │    │  └──────────────────────┘ │
│                            │    │                            │
│                            │    │  ┌──────────────────────┐ │
│                            │    │  │      Nginx           │ │
│                            │    │  │      :8082           │ │
│                            │    │  └──────────────────────┘ │
│                            │    │                            │
│                            │    │  ┌──────────────────────┐ │
│                            │    │  │    PostgreSQL        │ │
│                            │    │  │      :5432           │ │
│                            │    │  └──────────────────────┘ │
│                            │    │                            │
│                            │    │  ┌──────────────────────┐ │
│                            │    │  │       n8n            │ │
│                            │    │  │      :5678           │ │
│                            │    │  └──────────────────────┘ │
└────────────────────────────┘    └────────────────────────────┘
```

---

## Issues Identified

### 1. Service on Port 8083 (Ubuntu 1)
- **Current**: Media Mover API running from `/home/rusty_admin/projects/reachy_08.4.2`
- **Status**: ✅ Working (health, media listing)
- **Problem**: Started Nov 17, before dialogue router was created
- **Solution**: Needs restart to load dialogue and WebSocket endpoints

### 2. Service on Port 8081 (Ubuntu 1)
- **Current**: Legacy service from `/media/rusty_admin/project_data/reachy_emotion`
- **Status**: ✅ Running but different codebase
- **Problem**: Confusion about which service is which
- **Solution**: Either stop this service or document its purpose

### 3. Gateway on Port 8000 (Ubuntu 2)
- **Current**: Port is open but not responding to HTTP
- **Status**: ❌ Not accessible from Ubuntu 1
- **Problem**: Service may be bound to 127.0.0.1 or not running
- **Solution**: SSH to Ubuntu 2 and check:
  ```bash
  # On Ubuntu 2:
  ss -tlnp | grep 8000
  curl http://localhost:8000/health
  # If bound to 127.0.0.1, restart with --host 0.0.0.0
  ```

### 4. Promotion Endpoints (Port 8083)
- **Current**: All `/api/v1/promote/*` endpoints return 500
- **Status**: ❌ Failing
- **Problem**: Database tables not initialized or connection issues
- **Solution**: Run database migrations:
  ```bash
  cd /home/rusty_admin/projects/reachy_08.4.2
  alembic upgrade head
  ```

### 5. Dialogue Endpoints (Port 8083)
- **Current**: Not registered in running service
- **Status**: ❌ Missing
- **Problem**: Service started before dialogue router was created
- **Solution**: Restart service on port 8083

---

## Action Items

### Immediate (Ubuntu 1)

1. **Restart Media Mover API (Port 8083)**
   ```bash
   # Find and stop the process
   ps aux | grep "uvicorn.*8083"
   kill <PID>
   
   # Restart with reload
   cd /home/rusty_admin/projects/reachy_08.4.2
   source venv/bin/activate
   uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8083 --reload
   ```

2. **Run Database Migrations**
   ```bash
   cd /home/rusty_admin/projects/reachy_08.4.2/apps/api
   alembic upgrade head
   ```

3. **Clarify Port 8081 Service**
   - Document purpose or stop if redundant

### Immediate (Ubuntu 2)

4. **Fix Gateway Binding**
   ```bash
   # SSH to Ubuntu 2
   ssh ubuntu2
   
   # Check if service is running
   ss -tlnp | grep 8000
   ps aux | grep uvicorn
   
   # If bound to 127.0.0.1, restart:
   uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8000
   ```

5. **Verify Streamlit**
   ```bash
   # On Ubuntu 2
   curl http://localhost:8501
   ```

---

## Testing Checklist

After fixes, verify:

- [ ] Ubuntu 1 Port 8083: `/api/v1/health` returns healthy
- [ ] Ubuntu 1 Port 8083: `/api/v1/dialogue/health` returns ok
- [ ] Ubuntu 1 Port 8083: `/api/v1/promote/stage` (dry-run) returns 202
- [ ] Ubuntu 1 Port 8082: Nginx serves static files
- [ ] Ubuntu 1 Port 5432: PostgreSQL accepts connections
- [ ] Ubuntu 1 Port 5678: n8n web UI loads
- [ ] Ubuntu 1 Port 1234: LM Studio responds to `/v1/models`
- [ ] Ubuntu 2 Port 8000: Gateway `/health` accessible from Ubuntu 1
- [ ] Ubuntu 2 Port 8501: Streamlit UI loads

---

## Port Assignment Reference

| Port Range | Purpose |
|------------|---------|
| 5432 | PostgreSQL (standard) |
| 5678 | n8n (default) |
| 8000 | Gateway API (external-facing) |
| 8081 | Legacy/alternate service |
| 8082 | Nginx static server |
| 8083 | Media Mover API (primary) |
| 8501 | Streamlit (default) |
| 1234 | LM Studio (default) |

---

**Last Updated**: 2025-11-18 01:25 UTC-05:00  
**Maintained By**: Cascade AI + Russell Bray
