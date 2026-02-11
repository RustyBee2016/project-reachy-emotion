# Web App Database Connectivity Status

**Date:** 2026-02-09  
**Machine:** Ubuntu 2 (10.0.4.140)  
**Status:** ✅ Partially Functional - Database reads work, writes need configuration

---

## Architecture Overview

The web app (`apps/web/landing_page.py`) uses a **two-service architecture**:

### 1. Gateway API (Ubuntu 2, port 8000)
- **Location:** `apps/gateway/main.py`
- **Status:** ✅ Running and healthy
- **Endpoints used by web app:**
  - `POST /api/media/ingest` - Upload videos
  - `POST /api/privacy/redact/{video_id}` - Reject videos
  - `GET /health` - Health check

### 2. Media Mover API (Ubuntu 1, port 8083)
- **Location:** `apps/api/app/main.py` (runs on Ubuntu 1)
- **Status:** ⚠️ Partially working
- **Endpoints used by web app:**
  - `GET /api/v1/media/list` - ✅ List videos (database reads work)
  - `POST /api/v1/promote/stage` - ❌ Stage to dataset_all (500 error - database writes fail)

---

## Video Request & Storage Workflow

### Scripts Involved

1. **`apps/web/landing_page.py`** - Main Streamlit UI
2. **`apps/web/api_client.py`** - API client with retry logic
3. **`apps/web/luma_client.py`** - Luma AI video generation client

### Complete Workflow

#### Option A: Upload Existing Video
```
User uploads file
    ↓
landing_page.py calls ingest_video()
    ↓
api_client.py → POST {GATEWAY_URL}/api/media/ingest
    ↓
Gateway saves to /media/project_data/reachy_emotion/videos/temp/
    ↓
Video appears in UI for labeling
```

#### Option B: Generate Video with Luma AI
```
User enters prompt
    ↓
landing_page.py calls luma_client.generate_and_download()
    ↓
LumaVideoGenerator:
  1. create_generation() - Submit to Luma API
  2. poll_until_complete() - Wait for generation
  3. download_video() - Save to temp directory
    ↓
send_to_n8n_ingest() - Notify n8n webhook (optional)
    ↓
Video saved to /media/project_data/reachy_emotion/videos/temp/
    ↓
Video appears in UI for labeling
```

#### Labeling & Storage
```
User selects emotion label
    ↓
landing_page.py calls stage_to_dataset_all()
    ↓
api_client.py → POST {MEDIA_MOVER_URL}/api/v1/promote/stage
    ↓
Media Mover (Ubuntu 1):
  1. Validates video exists in temp/
  2. Moves file to dataset_all/
  3. ❌ FAILS HERE - Database write error
  4. Should: Save metadata to PostgreSQL (video_id, label, timestamp)
  5. Should: Log promotion event
    ↓
Should return: promoted_ids, skipped_ids, failed_ids
```

---

## Database Connectivity Test Results

### Test 1: Gateway Health ✅
- Endpoint: `http://10.0.4.140:8000/health`
- Result: Returns "ok"

### Test 2: Media Mover Health ❌
- Endpoint: `http://10.0.4.130:8083/health`
- Result: 404 Not Found
- Note: `/api/v1/media/list` works, so service is running

### Test 3: List Videos (Database Read) ✅
- Endpoint: `http://10.0.4.130:8083/api/v1/media/list?split=temp&limit=5`
- Result: Successfully returned 6 videos from database
- Sample video:
  ```json
  {
    "video_id": "luma_20251129_230602",
    "file_path": "temp/luma_20251129_230602.mp4",
    "size_bytes": 2627315,
    "split": "temp"
  }
  ```

### Test 4: Stage Video (Database Write) ❌
- Endpoint: `http://10.0.4.130:8083/api/v1/promote/stage`
- Payload: `{"video_ids": ["luma_20251129_230602"], "label": "happy", "dry_run": true}`
- Result: **500 Internal Server Error**
- Root Cause: Database connection issue on Ubuntu 1

---

## Issue: Database Write Failure

### Problem
The Media Mover API on Ubuntu 1 can **read** from the database (listing works) but **cannot write** (staging fails with 500 error).

### Root Cause
The database connection string on Ubuntu 1 is likely misconfigured or missing credentials.

**Default configuration** (`apps/api/app/config.py`):
```python
database_url: str = field(
    default_factory=lambda: os.getenv(
        "REACHY_DATABASE_URL",
        "postgresql+asyncpg://reachy_app:reachy_app@localhost:5432/reachy_local"
    )
)
```

**Expected configuration for Ubuntu 1:**
```bash
REACHY_DATABASE_URL=postgresql+asyncpg://reachy_dev:PASSWORD@10.0.4.130:5432/reachy_emotion
```

### Fix Required on Ubuntu 1

1. **Set environment variable** in Media Mover service configuration:
   ```bash
   export REACHY_DATABASE_URL="postgresql+asyncpg://reachy_dev:YOUR_PASSWORD@10.0.4.130:5432/reachy_emotion"
   ```

2. **Restart Media Mover service:**
   ```bash
   sudo systemctl restart media-mover
   # OR if running manually:
   pkill -f "uvicorn apps.api.app.main"
   uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8083
   ```

3. **Verify database connection:**
   ```bash
   psql -h 10.0.4.130 -U reachy_dev -d reachy_emotion -c "SELECT COUNT(*) FROM videos;"
   ```

---

## Web App Access

**Streamlit UI:** http://10.0.4.140:8501 or http://localhost:8501

The web app is currently running and accessible. You can:
- ✅ Upload videos
- ✅ Generate videos with Luma AI (if LUMAAI_API_KEY is configured)
- ✅ View videos in the UI
- ✅ List existing videos from database
- ❌ Label and stage videos to dataset_all (fails due to database write issue)

---

## Configuration Files

### Web App Environment (`apps/web/.env`)
```bash
REACHY_GATEWAY_BASE=http://10.0.4.140:8000
REACHY_API_BASE=http://10.0.4.130:8083
LUMAAI_API_KEY=<your_key>
N8N_HOST=10.0.4.130
N8N_PORT=5678
N8N_INGEST_TOKEN=<your_token>
```

### Media Mover Environment (Ubuntu 1, `apps/api/.env`)
```bash
REACHY_DATABASE_URL=postgresql+asyncpg://reachy_dev:PASSWORD@10.0.4.130:5432/reachy_emotion
REACHY_VIDEOS_ROOT=/media/rusty_admin/project_data/reachy_emotion/videos
REACHY_API_PORT=8083
```

---

## Next Steps

1. **Fix database connection on Ubuntu 1:**
   - SSH to Ubuntu 1: `ssh rusty_admin@10.0.4.130`
   - Set `REACHY_DATABASE_URL` environment variable
   - Restart Media Mover service
   - Test staging endpoint again

2. **Verify full workflow:**
   - Run `python3 test_web_app_db.py` again
   - All 4 tests should pass

3. **Test in web app:**
   - Open http://localhost:8501
   - Upload or generate a video
   - Label it with an emotion
   - Click "Submit Classification"
   - Should see success message and video moved to dataset_all

---

## Summary

**Database Connectivity:** ✅ Reads work, ❌ Writes fail  
**Web App Status:** ⚠️ Functional for viewing, broken for labeling  
**Action Required:** Configure database connection on Ubuntu 1  
**Test Script:** `test_web_app_db.py` created for validation
