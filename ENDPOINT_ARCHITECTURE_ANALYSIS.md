# Endpoint Architecture Analysis & Rewrite Recommendations

**Date**: 2025-11-14  
**Version**: 0.08.4.3  
**Status**: PROPOSAL - AWAITING APPROVAL

---

## Executive Summary

**Recommendation**: **YES - Rewrite the endpoint system**

The current architecture exhibits multiple systemic issues that have led to recurring configuration errors, port conflicts, and integration failures. A focused rewrite will eliminate confusion, establish clear boundaries, and provide a maintainable foundation for future development.

---

## Current State Analysis

### 1. Architecture Overview

**Current Components:**
- **FastAPI Media Service** (port 8083) - Database-backed promotion service
- **Legacy Media Router** (`apps/api/routers/media.py`) - Filesystem-only operations
- **New Promote Router** (`apps/api/app/routers/promote.py`) - Database-backed workflows
- **Nginx** (port 8082) - Static file serving (thumbnails)
- **API Client** (`apps/web/api_client.py`) - Web UI integration layer
- **Landing Page** (`apps/web/landing_page.py`) - Streamlit UI

### 2. Identified Problems

#### Problem 1: Dual Routing Architecture
**Issue**: Two separate router systems serving overlapping functionality
- `apps/api/routers/media.py` - Legacy filesystem-only endpoints
- `apps/api/app/routers/promote.py` - New database-backed endpoints

**Symptoms**:
- `/api/media/promote` (legacy stub) vs `/promote/stage` (new implementation)
- Confusion about which endpoint to use
- Duplicate code paths for similar operations

#### Problem 2: Port Configuration Chaos
**Issue**: Multiple port references scattered across codebase
- Port 8082: Nginx (static files)
- Port 8083: FastAPI backend
- Historical port 8081: Old configuration still referenced in docs

**Symptoms**:
- Service crashes due to port conflicts
- Environment variable overrides (`REACHY_API_BASE`) causing unexpected behavior
- Hardcoded URLs in multiple files (landing_page.py line 93, api_client.py line 6)

#### Problem 3: Inconsistent Path Configuration
**Issue**: Filesystem paths defined in multiple locations
- `media.py` line 21: `VIDEOS_ROOT` with environment override
- `settings.py`: `videos_root` configuration
- Hardcoded paths in landing_page.py line 94

**Recent Bug**: Wrong path `/media/project_data/...` vs correct `/media/rusty_admin/project_data/...`

#### Problem 4: Response Format Inconsistency
**Issue**: Different endpoints return different response structures
- Some return `{"items": [...]}` 
- Others return `{"videos": [...]}`
- Client code must handle both formats (landing_page.py line 66)

#### Problem 5: Endpoint Naming Confusion
**Issue**: Multiple URL patterns for similar operations
- `/api/media/videos/list` (compatibility endpoint)
- `/api/videos/list` (primary endpoint)
- `/promote/stage` (new database-backed)
- `/api/media/promote` (legacy stub)

#### Problem 6: Service Management Complexity
**Issue**: systemd service not enabled by default, manual restarts required
- Service status: `disabled; inactive (dead)`
- No automatic startup on boot
- Manual intervention required after code changes

---

## Root Causes

### 1. **Incremental Evolution Without Refactoring**
The system evolved from filesystem-only to database-backed without removing legacy code paths.

### 2. **Configuration Sprawl**
Settings distributed across:
- Environment variables (`REACHY_API_BASE`, `MEDIA_VIDEOS_ROOT`)
- Hardcoded values in multiple files
- systemd service files
- No single source of truth

### 3. **Lack of API Versioning**
No clear versioning strategy leads to compatibility endpoints and format variations.

### 4. **Mixed Responsibilities**
Single routers handling both legacy compatibility and new functionality.

---

## Proposed Solution: Unified Endpoint Architecture

### Design Principles

1. **Single Source of Truth**: One configuration file for all paths and ports
2. **Clear Separation**: Legacy vs current endpoints clearly delineated
3. **Consistent Responses**: Standardized response schemas across all endpoints
4. **Explicit Versioning**: `/api/v1/` prefix for all new endpoints
5. **Service Reliability**: systemd service enabled by default with health checks

---

## Rewrite Recommendations

### Phase 1: Configuration Consolidation (Priority: CRITICAL)

**Goal**: Eliminate configuration sprawl and hardcoded values

**Actions**:
1. Create centralized configuration file: `apps/api/app/config.py`
   - Single definition for all paths, ports, URLs
   - Environment variable overrides with clear precedence
   - Validation on startup

2. Remove all hardcoded values from:
   - `landing_page.py` (lines 91-94)
   - `api_client.py` (line 6)
   - `media.py` (line 21)

3. Create `.env.template` files with documentation:
   - `apps/api/.env.template` - Backend configuration
   - `apps/web/.env.template` - Frontend configuration

**Expected Outcome**:
- One place to change port/path configuration
- Clear documentation of all configuration options
- Validation errors on startup if misconfigured

---

### Phase 2: Endpoint Unification (Priority: HIGH)

**Goal**: Single, versioned API with clear responsibilities

**Proposed Structure**:
```
/api/v1/
├── /media/
│   ├── GET  /list              # List videos (replaces /api/videos/list)
│   ├── GET  /{video_id}        # Get video metadata
│   └── GET  /{video_id}/thumb  # Get thumbnail
├── /promote/
│   ├── POST /stage             # Stage to dataset_all (KEEP - already good)
│   ├── POST /sample            # Sample train/test splits (KEEP - already good)
│   └── POST /reset-manifest    # Reset manifest (KEEP - already good)
├── /health                     # Service health check
└── /metrics                    # Prometheus metrics
```

**Legacy Compatibility** (deprecated, to be removed in v0.09.x):
```
/api/media/
├── POST /promote               # Redirect to /api/v1/promote/stage
├── GET  /videos/list           # Redirect to /api/v1/media/list
└── GET  /                      # Service status
```

**Actions**:
1. Create new `apps/api/app/routers/media_v1.py` with clean implementation
2. Migrate database-backed logic from `promote.py` (already good)
3. Add deprecation warnings to legacy endpoints
4. Update `api_client.py` to use v1 endpoints
5. Remove `apps/api/routers/media.py` (legacy router)

**Expected Outcome**:
- Clear API versioning
- No duplicate endpoints
- Consistent response formats
- Easy to deprecate legacy endpoints

---

### Phase 3: Response Schema Standardization (Priority: HIGH)

**Goal**: All endpoints return consistent, well-documented schemas

**Standard Response Envelope**:
```json
{
  "status": "success" | "error",
  "data": { ... },
  "meta": {
    "correlation_id": "uuid",
    "timestamp": "ISO8601",
    "version": "v1"
  },
  "errors": [ ... ]  // Only present on error
}
```

**List Response Format**:
```json
{
  "status": "success",
  "data": {
    "items": [ ... ],
    "pagination": {
      "total": 100,
      "limit": 50,
      "offset": 0,
      "has_more": true
    }
  },
  "meta": { ... }
}
```

**Actions**:
1. Define Pydantic schemas in `apps/api/app/schemas/responses.py`
2. Update all endpoints to use standard envelope
3. Remove format detection logic from client (landing_page.py line 66)

**Expected Outcome**:
- No more format guessing in client code
- Self-documenting API via OpenAPI/Swagger
- Easy to add fields without breaking clients

---

### Phase 4: Service Reliability (Priority: MEDIUM)

**Goal**: FastAPI service runs reliably without manual intervention

**Actions**:
1. Update systemd service file:
   - Enable service: `WantedBy=multi-user.target`
   - Add restart policy: `Restart=on-failure`, `RestartSec=5s`
   - Add health check: `ExecStartPost` to verify service is responding
   - Add environment file: `EnvironmentFile=/path/to/.env`

2. Create service management scripts:
   - `scripts/service-start.sh` - Start with validation
   - `scripts/service-stop.sh` - Graceful shutdown
   - `scripts/service-restart.sh` - Restart with health check
   - `scripts/service-status.sh` - Detailed status report

3. Add startup validation:
   - Check database connectivity
   - Verify filesystem paths exist and are writable
   - Validate configuration before binding port
   - Log all configuration on startup

**Expected Outcome**:
- Service starts automatically on boot
- Automatic recovery from crashes
- Clear error messages when misconfigured
- No more manual systemctl commands

---

### Phase 5: Client Simplification (Priority: MEDIUM)

**Goal**: Clean, maintainable client library

**Actions**:
1. Refactor `api_client.py`:
   - Remove all hardcoded URLs
   - Use configuration from environment
   - Consistent error handling
   - Type hints for all functions
   - Remove format detection hacks

2. Create `api_client_v2.py` (already exists, needs completion):
   - Modern async/await support
   - Retry logic with exponential backoff
   - Request/response logging
   - Connection pooling

3. Update `landing_page.py`:
   - Remove hardcoded hosts/ports
   - Use api_client exclusively (no direct requests)
   - Better error messages for users

**Expected Outcome**:
- Single client library for all API calls
- No URL construction in UI code
- Consistent error handling
- Easy to mock for testing

---

### Phase 6: Testing & Validation (Priority: HIGH)

**Goal**: Comprehensive test coverage to prevent regressions

**Actions**:
1. Integration tests:
   - End-to-end video classification flow
   - Port conflict detection
   - Configuration validation
   - Database connectivity

2. API contract tests:
   - Response schema validation
   - Backward compatibility checks
   - Performance benchmarks

3. Service tests:
   - Startup/shutdown sequences
   - Health check endpoints
   - Graceful degradation

4. Create test fixtures:
   - Mock video files
   - Test database with sample data
   - Configuration templates

**Expected Outcome**:
- Catch configuration errors before deployment
- Prevent port conflicts
- Validate API changes don't break clients
- Confidence in refactoring

---

## Implementation Plan

### Timeline (Estimated)

| Phase | Duration | Dependencies | Risk |
|-------|----------|--------------|------|
| Phase 1: Configuration | 2-3 hours | None | Low |
| Phase 2: Endpoint Unification | 4-6 hours | Phase 1 | Medium |
| Phase 3: Response Schemas | 2-3 hours | Phase 2 | Low |
| Phase 4: Service Reliability | 2-3 hours | Phase 1 | Low |
| Phase 5: Client Simplification | 3-4 hours | Phase 2, 3 | Medium |
| Phase 6: Testing | 4-5 hours | All phases | Low |
| **Total** | **17-24 hours** | | |

### Rollout Strategy

**Stage 1: Preparation (No Breaking Changes)**
- Phase 1: Configuration consolidation
- Phase 4: Service reliability
- Phase 6: Test infrastructure

**Stage 2: API Migration (Backward Compatible)**
- Phase 2: New v1 endpoints (legacy endpoints still work)
- Phase 3: Response standardization (with compatibility layer)
- Update documentation

**Stage 3: Client Migration**
- Phase 5: Update api_client.py to use v1 endpoints
- Update landing_page.py
- Deprecation warnings on legacy endpoints

**Stage 4: Cleanup (Breaking Changes)**
- Remove legacy endpoints
- Remove compatibility code
- Remove old router files

---

## Risk Assessment

### Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Service downtime during migration | Medium | High | Blue-green deployment, rollback plan |
| Breaking existing integrations | Low | High | Maintain legacy endpoints during transition |
| Configuration errors | Medium | Medium | Validation on startup, comprehensive tests |
| Database migration issues | Low | High | Dry-run testing, backup procedures |

### Rollback Plan

1. Keep legacy endpoints active during migration
2. Feature flags for new vs old endpoints
3. Database schema versioning
4. Automated rollback scripts
5. Monitoring and alerting for errors

---

## Success Criteria

### Must Have (Go/No-Go)
- ✅ All existing functionality works
- ✅ No port conflicts
- ✅ Service starts automatically
- ✅ Configuration in one place
- ✅ All tests passing
- ✅ Documentation updated

### Should Have
- ✅ Response time < 100ms for list endpoints
- ✅ Clear error messages
- ✅ API documentation (Swagger)
- ✅ Monitoring dashboards

### Nice to Have
- ⭐ Async client library
- ⭐ Request tracing
- ⭐ Performance metrics
- ⭐ Load testing results

---

## Alternatives Considered

### Alternative 1: Incremental Fixes (Status Quo)
**Pros**: Less work upfront, no breaking changes  
**Cons**: Technical debt accumulates, issues will recur  
**Verdict**: ❌ Not recommended - band-aids on systemic problems

### Alternative 2: Complete Rewrite from Scratch
**Pros**: Clean slate, modern architecture  
**Cons**: High risk, long timeline, potential for new bugs  
**Verdict**: ❌ Not recommended - too risky, unnecessary

### Alternative 3: Focused Refactoring (Recommended)
**Pros**: Addresses root causes, manageable scope, backward compatible  
**Cons**: Requires discipline to not add new features during refactor  
**Verdict**: ✅ **RECOMMENDED** - Best balance of risk/reward

---

## Next Steps

### Immediate Actions (Awaiting Approval)

1. **Review this proposal** - Stakeholder sign-off required
2. **Prioritize phases** - Confirm order and timeline
3. **Allocate resources** - Dedicated time for implementation
4. **Create tracking** - GitHub issues/project board

### Post-Approval Actions

1. Create feature branch: `feature/endpoint-architecture-rewrite`
2. Implement Phase 1 (Configuration)
3. Run test suite and validate
4. Proceed to Phase 2 only after Phase 1 is stable
5. Continuous integration and testing throughout

---

## Appendix A: Current Issues Log

### Issue 1: Port 8082 Conflict
- **Date**: 2025-11-13
- **Symptom**: FastAPI service crashes on startup
- **Root Cause**: Nginx already using port 8082
- **Fix**: Changed FastAPI to port 8083
- **Prevention**: This rewrite (Phase 1 + 4)

### Issue 2: Wrong Filesystem Path
- **Date**: 2025-11-14
- **Symptom**: 500 error on /api/media/videos/list
- **Root Cause**: Hardcoded `/media/project_data/` instead of `/media/rusty_admin/project_data/`
- **Fix**: Updated media.py line 21
- **Prevention**: This rewrite (Phase 1)

### Issue 3: Response Format Mismatch
- **Date**: 2025-11-14
- **Symptom**: Client code failing to parse responses
- **Root Cause**: Some endpoints return "items", others "videos"
- **Fix**: Added format detection in landing_page.py
- **Prevention**: This rewrite (Phase 3)

### Issue 4: Video ID Resolution Failure
- **Date**: 2025-11-14
- **Symptom**: "Unable to resolve video ID" error
- **Root Cause**: List endpoint failing, metadata lookup impossible
- **Fix**: Fixed filesystem path, restarted service
- **Prevention**: This rewrite (Phase 1 + 4 + 6)

---

## Appendix B: Configuration Inventory

### Current Configuration Sources

1. **Environment Variables**
   - `REACHY_API_BASE` - API base URL
   - `MEDIA_VIDEOS_ROOT` - Video storage path
   - `N8N_HOST` - n8n webhook host
   - `N8N_PORT` - n8n webhook port

2. **Hardcoded Values**
   - `landing_page.py:91-94` - Hosts and ports
   - `api_client.py:6` - Default media base URL
   - `media.py:21` - Videos root path

3. **systemd Service**
   - `/etc/systemd/system/fastapi-media.service` - Port 8083

4. **Settings Classes**
   - `apps/api/app/settings.py` - Application settings

### Proposed Unified Configuration

**Single file**: `apps/api/app/config.py`
```python
class Config:
    # Service
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8083
    API_VERSION: str = "v1"
    
    # Storage
    VIDEOS_ROOT: Path = Path("/media/rusty_admin/project_data/reachy_emotion/videos")
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://..."
    
    # External Services
    NGINX_HOST: str = "10.0.4.130"
    NGINX_PORT: int = 8082
    N8N_HOST: str = "10.0.4.130"
    N8N_PORT: int = 5678
```

---

## Appendix C: API Endpoint Mapping

### Current State (Confusing)

| Endpoint | Router | Function | Status |
|----------|--------|----------|--------|
| `/api/media/promote` | `media.py` | Stub/legacy | Deprecated |
| `/promote/stage` | `promote.py` | Database-backed | Active |
| `/api/videos/list` | `media.py` | Filesystem-only | Active |
| `/api/media/videos/list` | `media.py` | Compatibility | Active |
| `/media/health` | `media.py` | Health check | Active |

### Proposed State (Clear)

| Endpoint | Router | Function | Status |
|----------|--------|----------|--------|
| `/api/v1/media/list` | `media_v1.py` | List videos | Active |
| `/api/v1/media/{id}` | `media_v1.py` | Get metadata | Active |
| `/api/v1/media/{id}/thumb` | `media_v1.py` | Get thumbnail | Active |
| `/api/v1/promote/stage` | `promote.py` | Stage to dataset | Active |
| `/api/v1/promote/sample` | `promote.py` | Sample splits | Active |
| `/api/v1/health` | `health.py` | Health check | Active |
| `/api/media/*` | `legacy.py` | Redirects | Deprecated |

---

**END OF ANALYSIS**

**Status**: AWAITING APPROVAL TO PROCEED WITH IMPLEMENTATION

**Prepared by**: Cascade AI Assistant  
**Review Required**: Russell Bray (Product Owner)
