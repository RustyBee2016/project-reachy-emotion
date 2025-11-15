# Endpoint System Rewrite - Action Plan

**Project**: Reachy_Local_08.4.2  
**Date**: 2025-11-14  
**Status**: PROPOSAL - AWAITING APPROVAL  
**Estimated Effort**: 17-24 hours over 3-5 days

---

## Quick Summary

**Problem**: Multiple recurring configuration errors, port conflicts, and endpoint confusion  
**Solution**: Focused refactoring to unify configuration, standardize endpoints, and improve reliability  
**Approach**: Phased implementation with backward compatibility  
**Risk**: Low-Medium (with proper testing and rollback plan)

---

## Action Plan Overview

### Phase 1: Configuration Consolidation ⚙️
**Priority**: CRITICAL  
**Duration**: 2-3 hours  
**Risk**: Low

Eliminate configuration sprawl by creating single source of truth for all paths, ports, and URLs.

### Phase 2: Endpoint Unification 🔗
**Priority**: HIGH  
**Duration**: 4-6 hours  
**Risk**: Medium

Create versioned API (`/api/v1/`) with clear responsibilities, deprecate legacy endpoints.

### Phase 3: Response Schema Standardization 📋
**Priority**: HIGH  
**Duration**: 2-3 hours  
**Risk**: Low

Standardize all API responses with consistent envelope format and Pydantic schemas.

### Phase 4: Service Reliability 🛡️
**Priority**: MEDIUM  
**Duration**: 2-3 hours  
**Risk**: Low

Enable systemd service, add health checks, automatic restart, and startup validation.

### Phase 5: Client Simplification 🧹
**Priority**: MEDIUM  
**Duration**: 3-4 hours  
**Risk**: Medium

Refactor `api_client.py` to use new endpoints, remove hardcoded values and format hacks.

### Phase 6: Testing & Validation ✅
**Priority**: HIGH  
**Duration**: 4-5 hours  
**Risk**: Low

Comprehensive test suite covering integration, API contracts, and service management.

---

## Detailed Action Items

## Phase 1: Configuration Consolidation

### 1.1 Create Centralized Configuration Module

**File**: `apps/api/app/config.py`

**Tasks**:
- [ ] Define `AppConfig` class with all settings
- [ ] Add environment variable overrides with clear precedence
- [ ] Add validation methods (check paths exist, ports available)
- [ ] Add `load_config()` function with error handling
- [ ] Document all configuration options

**Configuration to Include**:
```python
# Service Configuration
API_HOST: str = "0.0.0.0"
API_PORT: int = 8083
API_VERSION: str = "v1"
API_ROOT_PATH: str = ""

# Storage Configuration
VIDEOS_ROOT: Path = "/media/rusty_admin/project_data/reachy_emotion/videos"
TEMP_DIR: str = "temp"
DATASET_DIR: str = "dataset_all"
TRAIN_DIR: str = "train"
TEST_DIR: str = "test"
THUMBS_DIR: str = "thumbs"
MANIFESTS_DIR: str = "manifests"

# Database Configuration
DATABASE_URL: str = "postgresql+asyncpg://reachy_app:***@localhost/reachy_local"

# External Services
NGINX_HOST: str = "10.0.4.130"
NGINX_PORT: int = 8082
N8N_HOST: str = "10.0.4.130"
N8N_PORT: int = 5678
GATEWAY_HOST: str = "10.0.4.140"
GATEWAY_PORT: int = 8000

# Feature Flags
ENABLE_CORS: bool = True
ENABLE_LEGACY_ENDPOINTS: bool = True  # For backward compatibility
```

**Validation Rules**:
- `VIDEOS_ROOT` must exist and be writable
- `API_PORT` must be available (not in use)
- `DATABASE_URL` must be valid connection string
- All directory paths under `VIDEOS_ROOT` must exist or be creatable

### 1.2 Create Environment Templates

**Files**: 
- `apps/api/.env.template`
- `apps/web/.env.template`

**Tasks**:
- [ ] Document all environment variables
- [ ] Provide example values
- [ ] Add comments explaining each variable
- [ ] Include security notes (e.g., don't commit .env)

### 1.3 Update Existing Code to Use Config

**Files to Update**:
- [ ] `apps/api/routers/media.py` - Remove `VIDEOS_ROOT` hardcode (line 21)
- [ ] `apps/api/app/main.py` - Use config for app initialization
- [ ] `apps/api/app/deps.py` - Use config for dependencies
- [ ] `apps/web/api_client.py` - Remove hardcoded URL (line 6)
- [ ] `apps/web/landing_page.py` - Remove hardcoded hosts/ports (lines 91-94)

### 1.4 Add Configuration Validation on Startup

**File**: `apps/api/app/main.py`

**Tasks**:
- [ ] Add `validate_config()` call in `lifespan` startup
- [ ] Log all configuration values on startup (mask secrets)
- [ ] Fail fast with clear error messages if misconfigured
- [ ] Add health check endpoint that reports config status

**Test**:
```bash
# Should fail with clear error
VIDEOS_ROOT=/nonexistent/path python -m uvicorn apps.api.app.main:app

# Should succeed and log configuration
python -m uvicorn apps.api.app.main:app --port 8083
```

---

## Phase 2: Endpoint Unification

### 2.1 Create New Versioned Media Router

**File**: `apps/api/app/routers/media_v1.py`

**Endpoints to Implement**:
- [ ] `GET /api/v1/media/list` - List videos with pagination
- [ ] `GET /api/v1/media/{video_id}` - Get video metadata
- [ ] `GET /api/v1/media/{video_id}/thumb` - Get thumbnail (redirect to Nginx)

**Features**:
- Use database for metadata (not just filesystem)
- Consistent response format (see Phase 3)
- Proper error handling with correlation IDs
- OpenAPI documentation

### 2.2 Update Promote Router for V1

**File**: `apps/api/app/routers/promote.py`

**Tasks**:
- [ ] Change prefix from `/promote` to `/api/v1/promote`
- [ ] Keep existing endpoints (already well-designed):
  - `POST /stage` - Stage to dataset_all
  - `POST /sample` - Sample train/test splits
  - `POST /reset-manifest` - Reset manifest state

### 2.3 Create Health & Metrics Routers

**Files**:
- `apps/api/app/routers/health.py`
- `apps/api/app/routers/metrics.py` (already exists, verify)

**Health Endpoint** (`GET /api/v1/health`):
- [ ] Check database connectivity
- [ ] Check filesystem access
- [ ] Report configuration status
- [ ] Return 200 if healthy, 503 if degraded

**Metrics Endpoint** (`GET /api/v1/metrics`):
- [ ] Prometheus-compatible metrics
- [ ] Request counts, latencies
- [ ] Database connection pool stats
- [ ] Filesystem usage

### 2.4 Create Legacy Compatibility Router

**File**: `apps/api/app/routers/legacy.py`

**Purpose**: Redirect old endpoints to new ones during transition

**Endpoints**:
- [ ] `POST /api/media/promote` → `POST /api/v1/promote/stage`
- [ ] `GET /api/videos/list` → `GET /api/v1/media/list`
- [ ] `GET /api/media/videos/list` → `GET /api/v1/media/list`

**Features**:
- Add deprecation warnings in response headers
- Log usage of legacy endpoints for monitoring
- Feature flag to disable: `ENABLE_LEGACY_ENDPOINTS=false`

### 2.5 Update Main App Router Registration

**File**: `apps/api/app/main.py`

**Tasks**:
- [ ] Register new v1 routers
- [ ] Register legacy router (if enabled)
- [ ] Remove old router imports
- [ ] Update OpenAPI docs with versioning info

**New Router Order**:
```python
app.include_router(health.router)
app.include_router(metrics.router)
app.include_router(media_v1.router)
app.include_router(promote.router)
if settings.enable_legacy_endpoints:
    app.include_router(legacy.router)
```

### 2.6 Remove Old Media Router

**File**: `apps/api/routers/media.py`

**Tasks**:
- [ ] Verify all functionality migrated to v1 routers
- [ ] Create backup: `media.py.backup`
- [ ] Delete `apps/api/routers/media.py`
- [ ] Remove from `apps/api/routers/__init__.py`

**⚠️ Only do this after Phase 5 (client migration) is complete**

---

## Phase 3: Response Schema Standardization

### 3.1 Define Standard Response Schemas

**File**: `apps/api/app/schemas/responses.py`

**Base Response Envelope**:
```python
class ResponseMeta(BaseModel):
    correlation_id: str
    timestamp: datetime
    version: str = "v1"

class SuccessResponse(BaseModel, Generic[T]):
    status: Literal["success"] = "success"
    data: T
    meta: ResponseMeta

class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    errors: list[ErrorDetail]
    meta: ResponseMeta
```

**Specific Response Types**:
- [ ] `ListVideosResponse` - For media list endpoint
- [ ] `VideoMetadataResponse` - For single video
- [ ] `StageResponse` - Already exists, verify format
- [ ] `SampleResponse` - Already exists, verify format
- [ ] `HealthResponse` - For health check

### 3.2 Update All Endpoints to Use Schemas

**Tasks**:
- [ ] Update `media_v1.py` endpoints
- [ ] Verify `promote.py` endpoints (already use schemas)
- [ ] Update `health.py` endpoint
- [ ] Add response_model to all route decorators

### 3.3 Update API Client to Use New Format

**File**: `apps/web/api_client.py`

**Tasks**:
- [ ] Remove format detection logic (line 66 in landing_page.py)
- [ ] Expect consistent `data` field in all responses
- [ ] Handle `meta.correlation_id` for request tracing
- [ ] Update error handling to parse `errors` array

---

## Phase 4: Service Reliability

### 4.1 Update systemd Service File

**File**: `/etc/systemd/system/fastapi-media.service`

**Changes**:
```ini
[Unit]
Description=Reachy Local 08.4.2 - Media Mover API (FastAPI)
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=rusty_admin
Group=rusty_admin
WorkingDirectory=/home/rusty_admin/projects/reachy_08.4.2
EnvironmentFile=/home/rusty_admin/projects/reachy_08.4.2/apps/api/.env
ExecStart=/media/rusty_admin/project_data/reachy_emotion/apps/api/.venv/bin/python -m uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8083
ExecStartPost=/bin/sleep 2
ExecStartPost=/usr/bin/curl -f http://localhost:8083/api/v1/health || exit 1

# Restart policy
Restart=on-failure
RestartSec=5s
StartLimitInterval=60s
StartLimitBurst=3

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=fastapi-media

[Install]
WantedBy=multi-user.target
```

**Tasks**:
- [ ] Update service file
- [ ] Create `.env` file in `apps/api/`
- [ ] Run `sudo systemctl daemon-reload`
- [ ] Run `sudo systemctl enable fastapi-media.service`
- [ ] Test restart behavior

### 4.2 Create Service Management Scripts

**Directory**: `scripts/`

**Scripts to Create**:

1. **`scripts/service-start.sh`**
   - [ ] Validate configuration before starting
   - [ ] Check port availability
   - [ ] Start service
   - [ ] Wait for health check
   - [ ] Report status

2. **`scripts/service-stop.sh`**
   - [ ] Graceful shutdown (SIGTERM)
   - [ ] Wait for connections to drain
   - [ ] Force kill if timeout (SIGKILL)
   - [ ] Report status

3. **`scripts/service-restart.sh`**
   - [ ] Call stop script
   - [ ] Call start script
   - [ ] Run health check
   - [ ] Report status

4. **`scripts/service-status.sh`**
   - [ ] Check systemd status
   - [ ] Check health endpoint
   - [ ] Check database connectivity
   - [ ] Check filesystem access
   - [ ] Report detailed status

### 4.3 Add Startup Validation

**File**: `apps/api/app/main.py`

**Lifespan Startup Checks**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Load and validate configuration
    config = load_config()
    
    # Check database
    await check_database_connectivity(config.database_url)
    
    # Check filesystem
    check_filesystem_access(config.videos_root)
    
    # Check port availability
    check_port_available(config.api_port)
    
    # Log configuration (mask secrets)
    log_configuration(config)
    
    yield
    
    # Cleanup
    await close_database_connections()
```

---

## Phase 5: Client Simplification

### 5.1 Refactor API Client

**File**: `apps/web/api_client.py`

**Tasks**:
- [ ] Remove all hardcoded URLs
- [ ] Load configuration from environment
- [ ] Use v1 endpoints exclusively
- [ ] Remove format detection hacks
- [ ] Add type hints to all functions
- [ ] Consistent error handling
- [ ] Add retry logic with exponential backoff
- [ ] Add request/response logging (debug mode)

**New Structure**:
```python
class APIClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or self._load_from_env()
        self.session = requests.Session()
        self.session.headers.update(self._default_headers())
    
    def list_videos(self, split: str, limit: int = 50, offset: int = 0) -> ListVideosResponse:
        """List videos from specified split."""
        url = f"{self.base_url}/api/v1/media/list"
        response = self._request("GET", url, params={"split": split, "limit": limit, "offset": offset})
        return ListVideosResponse(**response.json()["data"])
    
    def stage_to_dataset_all(self, video_ids: list[str], label: str, ...) -> StageResponse:
        """Stage videos to dataset_all with label."""
        url = f"{self.base_url}/api/v1/promote/stage"
        payload = {"video_ids": video_ids, "label": label, ...}
        response = self._request("POST", url, json=payload)
        return StageResponse(**response.json()["data"])
```

### 5.2 Update Landing Page

**File**: `apps/web/landing_page.py`

**Tasks**:
- [ ] Remove hardcoded hosts/ports (lines 91-94)
- [ ] Load configuration from environment
- [ ] Use `APIClient` class instead of direct requests
- [ ] Remove format detection logic (line 66)
- [ ] Better error messages for users
- [ ] Add retry logic for transient failures

**Configuration Loading**:
```python
# Load from environment
API_BASE_URL = os.getenv("REACHY_API_BASE", "http://localhost:8083")
GATEWAY_URL = os.getenv("REACHY_GATEWAY_BASE", "http://localhost:8000")

# Initialize client
api_client = APIClient(base_url=API_BASE_URL)
```

### 5.3 Complete API Client V2

**File**: `apps/web/api_client_v2.py` (already exists)

**Tasks**:
- [ ] Review existing implementation
- [ ] Add async/await support
- [ ] Add connection pooling
- [ ] Add request tracing
- [ ] Complete all endpoint methods
- [ ] Add comprehensive docstrings
- [ ] Add usage examples

---

## Phase 6: Testing & Validation

### 6.1 Configuration Tests

**File**: `tests/test_config.py`

**Test Cases**:
- [ ] Load configuration from environment
- [ ] Validate required fields
- [ ] Validate path existence
- [ ] Validate port availability
- [ ] Handle missing configuration gracefully
- [ ] Override with environment variables

### 6.2 Integration Tests

**File**: `tests/test_integration.py`

**Test Cases**:
- [ ] End-to-end video classification flow
- [ ] List videos → stage → verify database
- [ ] Upload → classify → promote → verify filesystem
- [ ] Error handling and rollback
- [ ] Concurrent requests

### 6.3 API Contract Tests

**File**: `tests/test_api_contracts.py`

**Test Cases**:
- [ ] Response schema validation (all endpoints)
- [ ] Backward compatibility (legacy endpoints)
- [ ] Error response format
- [ ] Pagination behavior
- [ ] Correlation ID propagation

### 6.4 Service Tests

**File**: `tests/test_service.py`

**Test Cases**:
- [ ] Service startup sequence
- [ ] Health check endpoint
- [ ] Graceful shutdown
- [ ] Restart behavior
- [ ] Configuration validation on startup
- [ ] Database connectivity check

### 6.5 Performance Tests

**File**: `tests/test_performance.py`

**Test Cases**:
- [ ] List endpoint latency (< 100ms)
- [ ] Promote endpoint latency (< 500ms)
- [ ] Concurrent request handling
- [ ] Database connection pooling
- [ ] Memory usage under load

### 6.6 Update Existing Tests

**Files**:
- [ ] `tests/test_video_classification_flow.py` - Update to use v1 endpoints
- [ ] `tests/test_api_endpoints.sh` - Update URLs
- [ ] `tests/manual_validation.sh` - Update for new structure

---

## Rollout Strategy

### Stage 1: Preparation (No Breaking Changes)
**Duration**: 1 day

**Tasks**:
- ✅ Complete Phase 1 (Configuration)
- ✅ Complete Phase 4 (Service Reliability)
- ✅ Complete Phase 6 (Test Infrastructure)

**Validation**:
- All existing functionality still works
- Service starts automatically
- Configuration loaded from single source
- Tests passing

**Rollback**: Revert configuration changes, restart service

---

### Stage 2: API Migration (Backward Compatible)
**Duration**: 1-2 days

**Tasks**:
- ✅ Complete Phase 2 (Endpoint Unification)
- ✅ Complete Phase 3 (Response Schemas)
- ✅ Keep legacy endpoints active

**Validation**:
- New v1 endpoints work correctly
- Legacy endpoints still work (with deprecation warnings)
- Response format consistent
- OpenAPI docs updated

**Rollback**: Disable v1 routers, keep legacy active

---

### Stage 3: Client Migration
**Duration**: 1 day

**Tasks**:
- ✅ Complete Phase 5 (Client Simplification)
- ✅ Update landing_page.py to use v1 endpoints
- ✅ Update api_client.py
- ✅ Monitor for errors

**Validation**:
- UI works with new endpoints
- No format detection needed
- Error handling works
- User experience unchanged

**Rollback**: Revert client changes, use legacy endpoints

---

### Stage 4: Cleanup (Breaking Changes)
**Duration**: 0.5 days

**Tasks**:
- ✅ Disable legacy endpoints (`ENABLE_LEGACY_ENDPOINTS=false`)
- ✅ Remove `apps/api/routers/media.py`
- ✅ Remove compatibility code
- ✅ Update documentation

**Validation**:
- All functionality works without legacy endpoints
- No errors in logs
- Performance metrics stable

**Rollback**: Re-enable legacy endpoints, restore deleted files

---

## Testing Checklist

### Pre-Deployment Testing

**Configuration**:
- [ ] Load config from environment
- [ ] Validate all required fields
- [ ] Check filesystem paths
- [ ] Check port availability
- [ ] Handle missing config gracefully

**API Endpoints**:
- [ ] `GET /api/v1/health` returns 200
- [ ] `GET /api/v1/media/list?split=temp` returns videos
- [ ] `POST /api/v1/promote/stage` stages video correctly
- [ ] `POST /api/v1/promote/sample` samples splits correctly
- [ ] Legacy endpoints redirect correctly

**Service Management**:
- [ ] Service starts automatically on boot
- [ ] Service restarts on failure
- [ ] Health check passes after startup
- [ ] Graceful shutdown works
- [ ] Configuration logged on startup

**Client Integration**:
- [ ] Landing page loads without errors
- [ ] Video list displays correctly
- [ ] Classification submission works
- [ ] Error messages are clear
- [ ] No format detection needed

**Database**:
- [ ] Metadata persists correctly
- [ ] Promotion logs created
- [ ] Transactions commit/rollback properly
- [ ] Connection pooling works

**Filesystem**:
- [ ] Videos move between directories
- [ ] Thumbnails accessible
- [ ] Manifests generated correctly
- [ ] Permissions correct

### Post-Deployment Monitoring

**First Hour**:
- [ ] Check service status every 5 minutes
- [ ] Monitor error logs
- [ ] Check health endpoint
- [ ] Verify database connectivity
- [ ] Test video classification flow

**First Day**:
- [ ] Monitor request latencies
- [ ] Check error rates
- [ ] Verify no legacy endpoint usage
- [ ] Review logs for warnings
- [ ] Test all major workflows

**First Week**:
- [ ] Performance metrics stable
- [ ] No configuration errors
- [ ] No port conflicts
- [ ] User feedback positive
- [ ] Ready for cleanup stage

---

## Success Criteria

### Must Have (Go/No-Go)

- [ ] ✅ All existing functionality works
- [ ] ✅ No port conflicts
- [ ] ✅ Service starts automatically on boot
- [ ] ✅ Configuration in one place (apps/api/app/config.py)
- [ ] ✅ All tests passing (>80% coverage)
- [ ] ✅ Documentation updated
- [ ] ✅ No hardcoded URLs/paths in code
- [ ] ✅ Consistent response format across all endpoints
- [ ] ✅ Health check endpoint working
- [ ] ✅ Rollback plan tested

### Should Have

- [ ] ✅ Response time < 100ms for list endpoints
- [ ] ✅ Response time < 500ms for promote endpoints
- [ ] ✅ Clear error messages with correlation IDs
- [ ] ✅ API documentation (Swagger/OpenAPI)
- [ ] ✅ Monitoring dashboards
- [ ] ✅ Deprecation warnings on legacy endpoints
- [ ] ✅ Request tracing
- [ ] ✅ Automated restart on failure

### Nice to Have

- [ ] ⭐ Async client library (api_client_v2.py)
- [ ] ⭐ Request/response logging
- [ ] ⭐ Performance metrics dashboard
- [ ] ⭐ Load testing results
- [ ] ⭐ Automated deployment pipeline
- [ ] ⭐ Blue-green deployment support

---

## Risk Mitigation

### Risk 1: Service Downtime During Migration
**Probability**: Medium  
**Impact**: High

**Mitigation**:
- Maintain backward compatibility during transition
- Test thoroughly in development environment
- Deploy during low-usage period
- Have rollback plan ready
- Monitor closely after deployment

### Risk 2: Breaking Existing Integrations
**Probability**: Low  
**Impact**: High

**Mitigation**:
- Keep legacy endpoints active during Stage 2-3
- Add deprecation warnings, not errors
- Comprehensive API contract tests
- Clear migration guide for any external clients
- Gradual rollout with feature flags

### Risk 3: Configuration Errors
**Probability**: Medium  
**Impact**: Medium

**Mitigation**:
- Validation on startup
- Clear error messages
- Environment templates with examples
- Comprehensive tests
- Documentation

### Risk 4: Database Migration Issues
**Probability**: Low  
**Impact**: High

**Mitigation**:
- No schema changes required (metadata already correct)
- Test with production-like data
- Backup before deployment
- Rollback procedure documented
- Database connection validation

---

## Rollback Procedures

### If Stage 1 Fails (Configuration)
```bash
# Revert configuration changes
git checkout HEAD -- apps/api/app/config.py apps/web/api_client.py apps/web/landing_page.py

# Restart service with old configuration
sudo systemctl restart fastapi-media.service

# Verify service is running
curl http://localhost:8083/media/health
```

### If Stage 2 Fails (API Migration)
```bash
# Disable v1 routers in main.py
# Set ENABLE_LEGACY_ENDPOINTS=true

# Restart service
sudo systemctl restart fastapi-media.service

# Verify legacy endpoints work
curl http://localhost:8083/api/media/videos/list?split=temp
```

### If Stage 3 Fails (Client Migration)
```bash
# Revert client changes
git checkout HEAD -- apps/web/api_client.py apps/web/landing_page.py

# Restart Streamlit
pkill -f streamlit
streamlit run apps/web/landing_page.py &

# Verify UI works
```

### If Stage 4 Fails (Cleanup)
```bash
# Re-enable legacy endpoints
export ENABLE_LEGACY_ENDPOINTS=true

# Restore deleted files from backup
cp apps/api/routers/media.py.backup apps/api/routers/media.py

# Restart service
sudo systemctl restart fastapi-media.service
```

---

## Documentation Updates Required

### Files to Update

1. **README.md**
   - [ ] Update API endpoint documentation
   - [ ] Add configuration section
   - [ ] Update service management instructions

2. **memory-bank/requirements_08.4.2.md**
   - [ ] Update endpoint specifications
   - [ ] Document new configuration system
   - [ ] Update deployment procedures

3. **QUICK_START_METADATA.md**
   - [ ] Update API URLs to v1 endpoints
   - [ ] Update configuration instructions

4. **METADATA_IMPLEMENTATION_PLAN.md**
   - [ ] Mark Phase 1-6 as complete
   - [ ] Update with new architecture

5. **New Documentation**
   - [ ] Create `docs/API_REFERENCE.md` - Complete API documentation
   - [ ] Create `docs/CONFIGURATION.md` - Configuration guide
   - [ ] Create `docs/SERVICE_MANAGEMENT.md` - Service operations guide
   - [ ] Create `docs/MIGRATION_GUIDE.md` - For any external integrations

---

## Timeline & Milestones

### Week 1: Preparation & Core Refactoring
**Days 1-2**: Phase 1 (Configuration) + Phase 4 (Service Reliability)
- Milestone: Single source of truth for configuration, service auto-starts

**Days 3-4**: Phase 2 (Endpoint Unification) + Phase 3 (Response Schemas)
- Milestone: V1 API working, legacy endpoints still functional

**Day 5**: Phase 6 (Testing Infrastructure)
- Milestone: Comprehensive test suite passing

### Week 2: Client Migration & Cleanup
**Days 1-2**: Phase 5 (Client Simplification)
- Milestone: UI using v1 endpoints, no format hacks

**Day 3**: Integration testing and bug fixes
- Milestone: All workflows tested end-to-end

**Day 4**: Stage 4 rollout (Cleanup)
- Milestone: Legacy endpoints removed, system running clean

**Day 5**: Documentation and handoff
- Milestone: All docs updated, system production-ready

---

## Next Steps - Awaiting Approval

### Immediate Actions Required

1. **Review this action plan** 
   - Confirm scope and approach
   - Adjust timeline if needed
   - Identify any concerns

2. **Approve to proceed**
   - Sign off on phased approach
   - Confirm rollout strategy
   - Allocate time for implementation

3. **Set up tracking**
   - Create GitHub issues for each phase
   - Set up project board
   - Define review checkpoints

### Post-Approval Actions

1. **Create feature branch**
   ```bash
   git checkout -b feature/endpoint-architecture-rewrite
   ```

2. **Begin Phase 1**
   - Create `apps/api/app/config.py`
   - Create environment templates
   - Update existing code
   - Run tests

3. **Daily standup**
   - Report progress
   - Identify blockers
   - Adjust plan as needed

---

## Questions for Stakeholder

1. **Timeline**: Is 1-2 weeks acceptable for this refactoring?

2. **Scope**: Any features to add/remove from this plan?

3. **Risk Tolerance**: Comfortable with phased rollout approach?

4. **Testing**: Need additional test scenarios?

5. **Documentation**: Any specific docs needed?

6. **Deployment**: Preferred deployment window (time/day)?

---

**Status**: AWAITING APPROVAL TO PROCEED

**Prepared by**: Cascade AI Assistant  
**Date**: 2025-11-14  
**Review Required**: Russell Bray (Product Owner)

---

## Approval Sign-Off

- [ ] **Approved** - Proceed with implementation
- [ ] **Approved with changes** - See comments below
- [ ] **Rejected** - Do not proceed

**Comments**:
```
[Space for stakeholder feedback]
```

**Approved by**: ________________  
**Date**: ________________
