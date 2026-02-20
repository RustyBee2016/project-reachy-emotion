# Quick Start: Metadata Persistence System

**Status**: ✅ Configured and Ready to Test  
**Last Updated**: 2025-11-14

---

## What's Been Configured

### ✅ Backend (Port 8083)
- FastAPI service with database-backed promotion
- PostgreSQL metadata storage (`Video.label`, `PromotionLog`)
- Atomic filesystem + database operations
- Emotion label validation

### ✅ Frontend (Streamlit UI)
- "Submit Classification" button integrated
- Calls `stage_to_dataset_all()` API function
- Saves emotion metadata to database
- Shows promotion results

### ✅ Port Configuration
- **8083**: FastAPI backend (database + API)
- **8082**: nginx (static files/thumbnails)
- **5432**: PostgreSQL database

---

## Quick Test (5 minutes)

### 1. Start Services

```bash
# Terminal 1: Start FastAPI backend
cd /home/rusty_admin/projects/reachy_08.4.2
./start_media_api.sh

# Terminal 2: Start Streamlit UI
streamlit run apps/web/landing_page.py
```

### 2. Test API Endpoints

```bash
# Run automated endpoint tests
./tests/test_api_endpoints.sh
```

**Expected Output**: All tests pass ✅

### 3. Classify a Video

1. Open UI: http://localhost:8501
2. Generate video: "happy person smiling"
3. Wait for generation (~1-2 min)
4. Select emotion: "happy"
5. Click "✅ Submit Classification"

**Expected Result**: 
- Success message: "Classified as: happy"
- "Video staged to dataset_all with metadata saved to database"

### 4. Verify Persistence

```bash
# Run validation script
./tests/manual_validation.sh
```

**Expected Output**:
- ✅ FastAPI service running
- ✅ PostgreSQL accessible
- ✅ Video in dataset_all/
- ✅ Database record with label="happy"
- ✅ PromotionLog entry created

---

## Manual Database Check

```bash
# Connect to database
psql -U reachy_app -d reachy_local

# Check recent videos with labels
SELECT 
    video_id::text, 
    split, 
    label, 
    created_at 
FROM video 
WHERE split = 'dataset_all' 
ORDER BY created_at DESC 
LIMIT 5;

# Check promotion logs
SELECT 
    video_id::text,
    from_split,
    to_split,
    intended_label,
    actor,
    created_at
FROM promotion_log
ORDER BY created_at DESC
LIMIT 5;

# Count videos by emotion
SELECT label, COUNT(*) 
FROM video 
WHERE split = 'dataset_all' 
GROUP BY label;
```

---

## Troubleshooting

### Issue: "Unable to resolve video ID"

**Cause**: Video not yet in database  
**Fix**: Wait a moment after generation, then retry

### Issue: "500 Server Error"

**Cause**: FastAPI service not running  
**Fix**: 
```bash
./start_media_api.sh
# Or check service status:
systemctl status fastapi-media.service
```

### Issue: "Connection refused"

**Cause**: Wrong port or service down  
**Fix**: Verify port 8083 is open:
```bash
curl http://localhost:8083/health
```

### Issue: Database connection error

**Cause**: PostgreSQL not running or wrong credentials  
**Fix**:
```bash
# Check PostgreSQL
sudo systemctl status postgresql

# Test connection
psql -U reachy_app -d reachy_local -c "SELECT 1;"
```

---

## Next Steps

See `METADATA_IMPLEMENTATION_PLAN.md` for:
- Phase 1: Integration tests
- Phase 2: UI enhancements (emotion counts, recent videos)
- Phase 3: Search and filtering
- Phase 4: Manifest generation
- Phase 5: Relabeling capability

---

## Files Modified

- ✅ `apps/web/api_client.py` - Added `stage_to_dataset_all()`
- ✅ `apps/web/landing_page.py` - Updated classification button, port config
- ✅ `start_media_api.sh` - Startup script for port 8083

## Files Created

- ✅ `METADATA_IMPLEMENTATION_PLAN.md` - Full implementation roadmap
- ✅ `tests/test_metadata_persistence.py` - Integration tests
- ✅ `tests/manual_validation.sh` - Validation script
- ✅ `tests/test_api_endpoints.sh` - API endpoint tests
- ✅ `QUICK_START_METADATA.md` - This file

---

## Success Criteria

- [x] FastAPI service runs on port 8083
- [x] UI connects to correct port
- [x] "Submit Classification" button works
- [ ] Emotion label persists to database ← **TEST THIS NOW**
- [ ] PromotionLog entry created
- [ ] Video moves to dataset_all/

**Status**: Ready for testing! 🚀
