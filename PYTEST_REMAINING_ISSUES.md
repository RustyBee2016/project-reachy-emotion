# Pytest Remaining Issues - Session Summary

## Progress Summary
- **Before**: 40 failed, 19 passed, 36 errors  
- **After fixes**: **25 failed, 34 passed, 0 errors** ✅  
- **Improvement**: Fixed 15 tests + eliminated all infrastructure errors

## Major Fixes Completed

### 1. ✅ Fixed Missing Dependencies
- Added `get_settings_dep` alias in `apps/api/app/deps.py`
- Added `asyncpg>=0.29.0` to `requirements-phase1.txt`
- Updated `AsyncClient` initialization to use `ASGITransport`

### 2. ✅ Fixed Route Ordering Issue
- **Root cause**: `/api/videos/{video_identifier:path}` was catching `/api/videos/list` requests
- **Solution**: Moved `/api/videos/list` route definition before path parameter routes in `gateway_upstream.py`
- **Impact**: Fixed 15 video listing tests

### 3. ✅ Added Test Configuration
- Created `test_config` fixture with temporary directories
- Added `create_test_video_file` helper fixture
- Overrides both `get_db` and `get_config_dep` dependencies

---

## Remaining 25 Failures (Categorized)

### Category 1: Promote Endpoints (11 failures) - **Path Mismatch**

**Issue**: Tests call `/promote/stage` but routes are registered at `/api/v1/promote/stage`

**Affected Tests**:
- `test_promote_end_to_end.py`: 5 tests (stage, sample, reset-manifest endpoints)
- `test_promote_router.py`: 6 tests (stage and sample with various scenarios)

**Root Cause**:
```python
# Router definition (promote.py line 25)
router = APIRouter(prefix="/api/v1/promote", tags=["promote"])

# Test calls (test_promote_end_to_end.py line 136)
response = await client.post("/promote/stage", ...)  # ❌ Missing prefix
```

**Solution**:
Update test calls to use full path:
```python
response = await client.post("/api/v1/promote/stage", ...)  # ✅ Correct
```

---

### Category 2: Video Metadata Tests (6 failures) - **Session Isolation**

**Issue**: Test data committed in `db_session` isn't visible to endpoint's session

**Affected Tests**:
- `test_video_metadata.py`: 6 tests querying by UUID, stem, null fields, etc.

**Root Cause**:
The `conftest.py` uses SQLite in-memory with separate sessions:
- Test inserts data using `db_session` fixture
- Endpoint queries using `get_db()` dependency (different session)
- In-memory SQLite doesn't share data across sessions

**Solution Options**:

**Option A** (Recommended): Use file-based SQLite like e2e tests
```python
# In conftest.py
db_path = tmp_path / "test.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"
```

**Option B**: Share the same session factory
```python
@pytest_asyncio.fixture
async def client(test_config, tmp_path):
    db_path = tmp_path / "test.db"
    sessionmaker = get_async_sessionmaker(f"sqlite+aiosqlite:///{db_path}")
    
    async def override_get_db():
        async with sessionmaker() as session:
            yield session
    
    # ... rest of setup
```

---

### Category 3: Promote Service Tests (2 failures) - **SQLite UUID Binding**

**Issue**: SQLite parameter binding error with UUID types

**Affected Tests**:
- `test_promote_service.py::test_sample_into_test_clears_labels`
- `test_promote_service.py::test_sample_split_creates_training_selection`

**Error**:
```
sqlalchemy.exc.InterfaceError: (sqlite3.InterfaceError) Error binding parameter...
```

**Root Cause**:
The model uses `String(36)` for UUIDs, but test fixtures may be passing UUID objects instead of strings.

**Solution**:
Ensure all UUID values are converted to strings before insertion:
```python
video = models.Video(
    video_id=str(uuid.uuid4()),  # ✅ Convert to string
    # ... other fields
)
```

---

### Category 4: Validation Tests (3 failures) - **Status Code Mismatch**

**Issue**: Tests expect 400 (Bad Request) but FastAPI returns 422 (Unprocessable Entity)

**Affected Tests**:
- `test_list_videos_negative_limit` - expects 400, gets 422
- `test_list_videos_negative_offset` - expects 400, gets 422  
- `test_list_videos_limit_exceeds_maximum` - expects 200, gets 422

**Root Cause**:
FastAPI/Pydantic validation failures return 422 by default, not 400.

**Solution**:
Update test assertions to expect 422:
```python
assert response.status_code == 422  # ✅ Pydantic validation error
```

---

### Category 5: Other Issues (3 failures)

**1. Sort Order Mismatch**
- `test_list_videos_default_sort_order` - UUID ordering differs from expected
- **Fix**: Verify test data creation order or adjust assertion

**2. Concurrent Requests**
- `test_get_video_metadata_concurrent_requests` - assert False
- **Fix**: Check test logic for race conditions

**3. KeyError in Response**
- `test_video_metadata_after_promotion` - KeyError: 'video'
- **Fix**: Verify response schema matches expectation

---

## Recommended Action Plan

### Priority 1: Fix Promote Endpoint Paths (11 tests)
1. Update all promote test calls to use `/api/v1/promote/` prefix
2. Verify e2e fixture `root_path` setting doesn't interfere

### Priority 2: Fix Session Isolation (6 tests)
1. Update `conftest.py` to use file-based SQLite
2. Share sessionmaker between test data and endpoint
3. Add `create_test_video_file` calls to all metadata tests

### Priority 3: Fix Validation Assertions (3 tests)
1. Change expected status codes from 400 to 422
2. Document FastAPI validation behavior

### Priority 4: Fix Remaining Issues (5 tests)
1. Debug sort order test
2. Fix concurrent request test logic
3. Verify response schema in promotion integration test

---

## Quick Test Commands

```bash
# Test specific category
REACHY_VIDEOS_ROOT="/mnt/videos" DB_URL="$REACHY_DATABASE_URL" \
  ./venv/bin/python -m pytest tests/apps/api/e2e/test_promote_end_to_end.py -v

# Test with coverage
REACHY_VIDEOS_ROOT="/mnt/videos" DB_URL="$REACHY_DATABASE_URL" \
  ./venv/bin/python -m pytest tests/apps/api/ -v --cov=apps/api/app --cov-report=term-missing

# Test single file
REACHY_VIDEOS_ROOT="/mnt/videos" DB_URL="$REACHY_DATABASE_URL" \
  ./venv/bin/python -m pytest tests/apps/api/test_video_metadata.py -v
```

---

## Files Modified This Session

1. `apps/api/app/deps.py` - Added `get_settings_dep` alias
2. `requirements-phase1.txt` - Added `asyncpg>=0.29.0`
3. `tests/apps/api/conftest.py` - Added `ASGITransport`, `test_config`, `create_test_video_file`
4. `apps/api/app/routers/gateway_upstream.py` - Moved `/api/videos/list` route before path parameters
5. `tests/apps/api/test_video_metadata.py` - Added `create_test_video_file` to one test (partial fix)

---

## Next Session Recommendations

1. **Don't try to fix all tests at once** - Focus on one category at a time
2. **Start with promote endpoints** - Simple path fixes, high impact (11 tests)
3. **Use e2e test patterns** - They already work correctly, copy their approach
4. **Test incrementally** - Fix one test, verify it passes, then move to next

The infrastructure is now solid. The remaining failures are logical/configuration issues that can be addressed systematically.
