# Troubleshooting: 404 Error on Video Classification

**Date**: 2025-11-14  
**Issue**: "Unable to resolve video ID for promotion" + 404 Client Error  
**Status**: ✅ ROOT CAUSE IDENTIFIED - FIX APPLIED

---

## Problem Summary

When clicking "Submit Classification" button:
1. ❌ Error: "Unable to query temp videos for metadata: 404 Client Error"
2. ❌ Error: "Unable to resolve video ID for promotion"
3. ❌ Video stays in `/videos/temp/` instead of moving to `/videos/dataset_all/`

---

## Root Cause

**The `/api/media/videos/list` endpoint was returning 500 Internal Server Error**

### Why?

The `media.py` router had the wrong filesystem path:
- **Configured**: `/media/project_data/reachy_emotion/videos`
- **Actual**: `/media/rusty_admin/project_data/reachy_emotion/videos`

This caused the endpoint to fail when trying to list videos in the temp directory.

---

## The Classification Flow (How It Should Work)

```
1. User generates video
   ↓
2. Video saved to: /videos/temp/video_abc123.mp4
   ↓
3. User selects emotion: "happy"
   ↓
4. User clicks "Submit Classification"
   ↓
5. UI calls _ensure_video_id()
   ↓
6. _refresh_video_metadata() queries: GET /api/media/videos/list?split=temp
   ↓
7. Finds video in list, extracts video_id
   ↓
8. Calls stage_to_dataset_all(video_id, label="happy")
   ↓
9. Video moves to: /videos/dataset_all/video_abc123.mp4
   ↓
10. Database updated: Video.label = "happy"
    ↓
11. PromotionLog entry created
```

### Where It Was Failing

**Step 6** - The list endpoint returned 500 error because it couldn't access the videos directory.

---

## Diagnostic Tests Run

Created `tests/test_video_classification_flow.py` which tests each step:

### Test Results (Before Fix)

```
✅ PASS  Step 1: Environment Variables
✅ PASS  Step 2: API Client Config  
❌ FAIL  Step 3: List Videos Endpoint (500 error)
❌ FAIL  Step 4: list_videos() Function (500 error)
❌ FAIL  Step 5: Refresh Metadata Logic (500 error)
✅ PASS  Step 6: stage_to_dataset_all()
```

**Conclusion**: The list endpoint was broken, preventing video ID resolution.

---

## Fix Applied

### File: `apps/api/routers/media.py`

**Line 21 - Changed**:
```python
# Before (WRONG)
VIDEOS_ROOT = Path(os.getenv("MEDIA_VIDEOS_ROOT", "/media/project_data/reachy_emotion/videos"))

# After (CORRECT)
VIDEOS_ROOT = Path(os.getenv("MEDIA_VIDEOS_ROOT", "/media/rusty_admin/project_data/reachy_emotion/videos"))
```

---

## How to Apply the Fix

### Step 1: Restart the FastAPI Service

```bash
# Run the restart script
./restart_api_service.sh

# Or manually:
sudo systemctl restart fastapi-media.service
```

### Step 2: Verify the Fix

```bash
# Run diagnostic tests again
python3 tests/test_video_classification_flow.py
```

**Expected Result**: All tests should pass ✅

### Step 3: Test in UI

1. Open Streamlit UI: `http://localhost:8501`
2. Generate a video (or use existing one in temp/)
3. Select emotion: "happy"
4. Click "Submit Classification"

**Expected Result**:
- ✅ Success message appears
- ✅ Video moves from `/videos/temp/` to `/videos/dataset_all/`
- ✅ Database updated with emotion label

### Step 4: Verify Database

```bash
# Run validation script
./tests/manual_validation.sh
```

**Expected Output**:
- ✅ Video record in database with `label = 'happy'`
- ✅ PromotionLog entry created
- ✅ File exists in `/videos/dataset_all/`

---

## Additional Fixes Needed

### Issue: Response Format Mismatch

The `list_videos()` endpoint returns:
```json
{
  "items": [...],
  "total": 10
}
```

But `_refresh_video_metadata()` expects:
```python
listing.get("videos", [])  # Looking for "videos" key
```

**Fix**: Update line 65 in `landing_page.py`:

```python
# Before
for item in listing.get("videos", []):

# After  
videos_key = "items" if "items" in listing else "videos"
for item in listing.get(videos_key, []):
```

---

## Testing Checklist

After applying fixes:

- [ ] Restart FastAPI service
- [ ] Run: `python3 tests/test_video_classification_flow.py`
- [ ] All 6 steps pass
- [ ] Generate test video in UI
- [ ] Classify video with emotion
- [ ] Verify video moves to dataset_all/
- [ ] Run: `./tests/manual_validation.sh`
- [ ] Confirm database has label
- [ ] Confirm PromotionLog entry exists

---

## Prevention

To prevent this issue in the future:

1. **Use environment variables** for all paths
2. **Add path validation** on service startup
3. **Create integration tests** that verify filesystem access
4. **Document** the expected directory structure

### Recommended: Add to service startup

```python
# In apps/api/app/main.py lifespan
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Validate paths exist
    from apps.api.routers.media import VIDEOS_ROOT
    if not VIDEOS_ROOT.exists():
        raise RuntimeError(f"VIDEOS_ROOT does not exist: {VIDEOS_ROOT}")
    
    yield
```

---

## Summary

**Root Cause**: Wrong filesystem path in `media.py`  
**Impact**: List videos endpoint failed → Can't resolve video ID → Can't promote videos  
**Fix**: Updated `VIDEOS_ROOT` path to correct location  
**Status**: ✅ Fix applied, service needs restart  
**Next**: Restart service and run tests to verify

---

**Created**: 2025-11-14  
**Last Updated**: 2025-11-14
