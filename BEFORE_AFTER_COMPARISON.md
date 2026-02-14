# Endpoint System: Before & After Comparison

**Date**: 2025-11-14  
**Project**: Reachy_Local_08.4.2

---

## Configuration Management

### BEFORE (Current State) ❌

**Configuration scattered across 10+ locations:**

```python
# apps/web/landing_page.py (lines 91-94)
UBUNTU2_HOST = "10.0.4.140"
UBUNTU1_HOST = "10.0.4.130"
GATEWAY_URL = f"http://{UBUNTU2_HOST}:8000"
MEDIA_MOVER_URL = f"http://{UBUNTU1_HOST}:8083"

# apps/web/api_client.py (line 6)
DEFAULT_MEDIA_BASE = "http://localhost:8083/api/media"

# apps/api/routers/media.py (line 21)
VIDEOS_ROOT = Path(os.getenv("MEDIA_VIDEOS_ROOT", "/media/rusty_admin/project_data/reachy_emotion/videos"))

# /etc/systemd/system/fastapi-media.service
ExecStart=... --port 8083

# Plus environment variables: REACHY_API_BASE, MEDIA_VIDEOS_ROOT, N8N_HOST, N8N_PORT...
```

**Problems:**
- 🔴 Change port? Update 5+ files
- 🔴 Wrong path? Hard to find where it's defined
- 🔴 No validation until runtime error
- 🔴 Environment variables override without documentation

### AFTER (Proposed) ✅

**Single source of truth:**

```python
# apps/api/app/config.py
class AppConfig:
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
    GATEWAY_HOST: str = "10.0.4.140"
    GATEWAY_PORT: int = 8000
    
    @classmethod
    def validate(cls):
        """Validate configuration on startup."""
        if not cls.VIDEOS_ROOT.exists():
            raise ConfigError(f"VIDEOS_ROOT does not exist: {cls.VIDEOS_ROOT}")
        if not cls._is_port_available(cls.API_PORT):
            raise ConfigError(f"Port {cls.API_PORT} already in use")
        # ... more validation

# All other files import from config
from apps.api.app.config import AppConfig
```

**Benefits:**
- ✅ Change port? Update 1 file
- ✅ Validated on startup with clear errors
- ✅ Environment overrides documented
- ✅ Type hints and IDE autocomplete

---

## API Endpoints

### BEFORE (Current State) ❌

**Confusing dual architecture:**

```
Legacy Router (apps/api/routers/media.py):
├── POST /api/media/promote          # Stub, doesn't work
├── GET  /api/videos/list            # Filesystem-only
├── GET  /api/media/videos/list      # Compatibility alias
└── GET  /media/health               # Health check

New Router (apps/api/app/routers/promote.py):
├── POST /promote/stage              # Database-backed, WORKS
├── POST /promote/sample             # Database-backed, WORKS
└── POST /promote/reset-manifest     # Database-backed, WORKS
```

**Problems:**
- 🔴 Which endpoint should I use?
- 🔴 `/api/media/promote` doesn't work but exists
- 🔴 Multiple URLs for same operation
- 🔴 No versioning strategy

### AFTER (Proposed) ✅

**Clear, versioned structure:**

```
V1 API (Current):
/api/v1/
├── /media/
│   ├── GET  /list              # List videos
│   ├── GET  /{video_id}        # Get metadata
│   └── GET  /{video_id}/thumb  # Get thumbnail
├── /promote/
│   ├── POST /stage             # Stage to dataset_all
│   ├── POST /sample            # Sample train/test
│   └── POST /reset-manifest    # Reset manifest
├── /health                     # Health check
└── /metrics                    # Prometheus metrics

Legacy (Deprecated, will be removed in v0.09.x):
/api/media/*                    # Redirects to v1 with warning
```

**Benefits:**
- ✅ Clear which endpoints to use
- ✅ Easy to deprecate old versions
- ✅ Consistent URL structure
- ✅ Self-documenting via OpenAPI

---

## Response Formats

### BEFORE (Current State) ❌

**Inconsistent responses:**

```python
# Some endpoints return:
{
    "items": [...],
    "total": 100
}

# Others return:
{
    "videos": [...],
    "count": 100
}

# Client must guess:
videos_key = "items" if "items" in listing else "videos"  # 😱
for item in listing.get(videos_key, []):
    ...
```

**Problems:**
- 🔴 Client code must detect format
- 🔴 No standard error format
- 🔴 Hard to add metadata
- 🔴 Not self-documenting

### AFTER (Proposed) ✅

**Consistent envelope:**

```python
# ALL endpoints return:
{
    "status": "success",
    "data": {
        "items": [...],
        "pagination": {
            "total": 100,
            "limit": 50,
            "offset": 0,
            "has_more": true
        }
    },
    "meta": {
        "correlation_id": "uuid",
        "timestamp": "2025-11-14T14:20:00Z",
        "version": "v1"
    }
}

# Errors:
{
    "status": "error",
    "errors": [
        {
            "code": "VALIDATION_ERROR",
            "message": "Invalid split parameter",
            "field": "split"
        }
    ],
    "meta": { ... }
}
```

**Benefits:**
- ✅ No format detection needed
- ✅ Consistent error handling
- ✅ Request tracing via correlation_id
- ✅ Pydantic validation

---

## Service Management

### BEFORE (Current State) ❌

**Manual intervention required:**

```bash
# Check status
$ systemctl status fastapi-media.service
○ fastapi-media.service - ...
     Active: inactive (dead)
     Loaded: disabled

# Service doesn't start on boot
# Must manually restart after code changes
# No health checks
# No automatic recovery
```

**Problems:**
- 🔴 Service not enabled (won't start on boot)
- 🔴 Manual restarts required
- 🔴 No automatic recovery from crashes
- 🔴 No validation before starting

### AFTER (Proposed) ✅

**Reliable, self-managing:**

```bash
# Check status
$ systemctl status fastapi-media.service
● fastapi-media.service - ...
     Active: active (running)
     Loaded: enabled

# Or use helper script
$ ./scripts/service-status.sh
✅ Service: RUNNING
✅ Health: OK (200)
✅ Database: CONNECTED
✅ Filesystem: ACCESSIBLE
✅ Port 8083: LISTENING
```

**systemd configuration:**
```ini
[Service]
Restart=on-failure
RestartSec=5s
ExecStartPost=/usr/bin/curl -f http://localhost:8083/api/v1/health

[Install]
WantedBy=multi-user.target  # Auto-start on boot
```

**Benefits:**
- ✅ Starts automatically on boot
- ✅ Automatic recovery from crashes
- ✅ Health check validation
- ✅ Configuration validated on startup

---

## Client Code

### BEFORE (Current State) ❌

**Messy, hardcoded:**

```python
# apps/web/landing_page.py
UBUNTU1_HOST = "10.0.4.130"  # Hardcoded
MEDIA_MOVER_URL = f"http://{UBUNTU1_HOST}:8083"

def _refresh_video_metadata(current: dict) -> Optional[str]:
    try:
        listing = list_videos_api(split="temp", limit=200, offset=0)
    except Exception as exc:
        st.warning(f"Unable to query: {exc}")
        return None
    
    # Format detection hack 😱
    videos_key = "items" if "items" in listing else "videos"
    for item in listing.get(videos_key, []):
        ...
```

**Problems:**
- 🔴 Hardcoded hosts and ports
- 🔴 Format detection hacks
- 🔴 Inconsistent error handling
- 🔴 No type hints

### AFTER (Proposed) ✅

**Clean, maintainable:**

```python
# apps/web/landing_page.py
from apps.web.api_client import APIClient
from apps.api.app.config import AppConfig

# Load from config
api_client = APIClient(base_url=AppConfig.API_BASE_URL)

def _refresh_video_metadata(current: dict) -> Optional[str]:
    """Resolve video_id from backend metadata."""
    try:
        response = api_client.list_videos(split="temp", limit=200, offset=0)
        # No format detection needed - always response.data.items
        for item in response.data.items:
            if item.file_path.name == filename:
                return item.video_id
    except APIError as exc:
        st.error(f"Failed to query videos: {exc.message}")
        logger.error("Video query failed", extra={"correlation_id": exc.correlation_id})
        return None
```

**Benefits:**
- ✅ No hardcoded values
- ✅ No format detection
- ✅ Type hints and validation
- ✅ Consistent error handling
- ✅ Request tracing

---

## Error Handling

### BEFORE (Current State) ❌

**Cryptic errors:**

```
# User sees:
"Unable to resolve video ID"

# Developer sees in logs:
requests.exceptions.HTTPError: 500 Server Error

# Actual problem:
VIDEOS_ROOT path doesn't exist
```

**Problems:**
- 🔴 User doesn't know what went wrong
- 🔴 Developer can't trace the request
- 🔴 No context about the error
- 🔴 Hard to debug

### AFTER (Proposed) ✅

**Clear, actionable errors:**

```
# User sees:
"Unable to list videos. Please contact support with error ID: abc-123-def"

# Developer sees in logs:
{
    "timestamp": "2025-11-14T14:20:00Z",
    "level": "ERROR",
    "correlation_id": "abc-123-def",
    "error": "FileNotFoundError",
    "message": "VIDEOS_ROOT does not exist: /media/rusty_admin/project_data/reachy_emotion/videos",
    "endpoint": "/api/v1/media/list",
    "user_agent": "Streamlit/1.28.0"
}

# Service won't start with clear error:
ConfigError: VIDEOS_ROOT does not exist: /media/rusty_admin/...
Please check configuration in apps/api/app/config.py
```

**Benefits:**
- ✅ User gets actionable message
- ✅ Developer can trace with correlation_id
- ✅ Errors caught at startup
- ✅ Clear error messages

---

## Testing

### BEFORE (Current State) ❌

**Minimal, manual testing:**

```bash
# Manual testing required
$ curl http://localhost:8083/api/media/videos/list?split=temp
# Hope it works 🤞

# Tests exist but incomplete
$ python3 tests/test_video_classification_flow.py
# Some pass, some fail, unclear why
```

**Problems:**
- 🔴 No automated validation
- 🔴 Port conflicts discovered at runtime
- 🔴 Configuration errors discovered by users
- 🔴 Regressions not caught

### AFTER (Proposed) ✅

**Comprehensive test suite:**

```bash
# Configuration validation
$ pytest tests/test_config.py
✅ test_load_config_from_env
✅ test_validate_videos_root_exists
✅ test_validate_port_available
✅ test_handle_missing_config

# API contract tests
$ pytest tests/test_api_contracts.py
✅ test_list_videos_response_schema
✅ test_stage_response_schema
✅ test_error_response_format
✅ test_correlation_id_propagation

# Integration tests
$ pytest tests/test_integration.py
✅ test_end_to_end_classification_flow
✅ test_video_promotion_with_database
✅ test_concurrent_requests

# Service tests
$ pytest tests/test_service.py
✅ test_service_startup_validation
✅ test_health_check_endpoint
✅ test_graceful_shutdown
✅ test_automatic_restart

# All tests pass
======================== 45 passed in 12.3s ========================
```

**Benefits:**
- ✅ Catch errors before deployment
- ✅ Prevent regressions
- ✅ Confidence in refactoring
- ✅ Documentation via tests

---

## Documentation

### BEFORE (Current State) ❌

**Scattered, outdated:**

```
# README mentions port 8081 (wrong)
# Some docs say 8082 (nginx)
# Some say 8083 (correct)
# No API documentation
# Configuration not documented
```

**Problems:**
- 🔴 Conflicting information
- 🔴 No single source of truth
- 🔴 Hard to onboard new developers
- 🔴 Users confused about configuration

### AFTER (Proposed) ✅

**Clear, comprehensive:**

```
docs/
├── API_REFERENCE.md           # Complete API docs (auto-generated from OpenAPI)
├── CONFIGURATION.md           # All config options explained
├── SERVICE_MANAGEMENT.md      # How to start/stop/monitor service
├── MIGRATION_GUIDE.md         # Upgrading from old endpoints
└── TROUBLESHOOTING.md         # Common issues and solutions

# Plus interactive API docs
http://localhost:8083/docs      # Swagger UI
http://localhost:8083/redoc     # ReDoc
```

**Benefits:**
- ✅ Self-documenting API
- ✅ Clear configuration guide
- ✅ Easy onboarding
- ✅ Interactive testing

---

## Real-World Scenarios

### Scenario 1: Changing the API Port

**BEFORE:**
1. Update `api_client.py` line 6
2. Update `landing_page.py` line 93
3. Update `media.py` (if it uses the port)
4. Update systemd service file
5. Update any scripts
6. Update documentation
7. Restart service
8. Hope you didn't miss anything 🤞

**AFTER:**
1. Update `apps/api/app/config.py` (one line)
2. Restart service (validates config automatically)
3. Done ✅

---

### Scenario 2: Debugging "Unable to resolve video ID"

**BEFORE:**
1. Check Streamlit logs (vague error)
2. Check FastAPI logs (500 error, no context)
3. Try curl commands manually
4. Discover list endpoint failing
5. Check filesystem paths
6. Find hardcoded wrong path
7. Update code
8. Restart service
9. Test again
10. Total time: 30-60 minutes 😓

**AFTER:**
1. Check error message (includes correlation_id)
2. Search logs for correlation_id
3. See clear error: "VIDEOS_ROOT does not exist: /path/to/videos"
4. Fix configuration
5. Service validates on startup, fails with clear message
6. Fix and restart
7. Total time: 5 minutes ✅

---

### Scenario 3: Adding a New Endpoint

**BEFORE:**
1. Add to `media.py` or `promote.py`? (unclear)
2. What URL pattern? (inconsistent)
3. What response format? (varies)
4. Update client code with format detection
5. Manual testing
6. Hope it works with existing code 🤞

**AFTER:**
1. Add to appropriate v1 router (clear structure)
2. Use standard URL pattern: `/api/v1/{resource}/{action}`
3. Use standard response envelope (Pydantic schema)
4. Client code automatically handles it (consistent format)
5. Automated tests validate schema
6. OpenAPI docs auto-generated ✅

---

## Summary: Why Rewrite?

### Current State Problems
- 🔴 Configuration scattered across 10+ files
- 🔴 Dual routing architecture (legacy + new)
- 🔴 Inconsistent response formats
- 🔴 Service management issues
- 🔴 Recurring configuration errors
- 🔴 Hard to debug and maintain

### After Rewrite Benefits
- ✅ Single source of truth for configuration
- ✅ Clear, versioned API structure
- ✅ Consistent response formats
- ✅ Reliable service management
- ✅ Comprehensive testing
- ✅ Self-documenting
- ✅ Easy to maintain and extend

### The Choice

**Option A: Keep Current System**
- Continue fixing issues as they arise
- Accept ongoing configuration errors
- Technical debt accumulates
- Harder to maintain over time

**Option B: Focused Refactoring** ✅
- 1-2 weeks of focused work
- Addresses root causes
- Maintainable foundation
- Prevents future issues

---

**Recommendation**: Option B - Focused Refactoring

**Next Step**: Review and approve ENDPOINT_REWRITE_ACTION_PLAN.md

---

**Prepared by**: Cascade AI Assistant  
**Date**: 2025-11-14  
**For**: Russell Bray (Product Owner)
