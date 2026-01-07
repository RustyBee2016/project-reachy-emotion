# Metadata Persistence Implementation Plan
**Created**: 2025-11-14  
**Status**: Active  
**Goal**: Validate and enhance emotion metadata persistence system

---

## Current State ✅

### Completed
- ✅ Database-backed promotion service (`promote_service.py`)
- ✅ PostgreSQL schema with `Video.label` and `PromotionLog` tables
- ✅ API client function `stage_to_dataset_all()` 
- ✅ Landing page integration with "Submit Classification" button
- ✅ Port configuration (FastAPI on 8083, nginx on 8082)

### Architecture
```
User → Streamlit UI → api_client.py → FastAPI (8083) → PostgreSQL
                                    ↓
                                Filesystem (atomic moves)
```

---

## Phase 1: Validate Metadata Persistence 🧪

**Goal**: Ensure emotion labels are correctly saved to database and retrievable

### 1.1 Create Integration Test for Promotion Flow

**File**: `tests/test_metadata_persistence.py`

**Test Cases**:
```python
def test_stage_video_with_emotion_label():
    """Test that emotion label is persisted to database"""
    # 1. Upload a test video to temp/
    # 2. Call stage_to_dataset_all(video_ids=[id], label="happy")
    # 3. Query database: SELECT label FROM video WHERE video_id = ?
    # 4. Assert label == "happy"
    # 5. Assert file moved from temp/ to dataset_all/
    # 6. Assert PromotionLog entry created

def test_stage_multiple_videos_different_labels():
    """Test batch promotion with different labels"""
    # Upload 3 videos, classify as happy, sad, angry
    # Verify all labels persisted correctly

def test_invalid_emotion_label_rejected():
    """Test that invalid labels are rejected"""
    # Try to stage with label="invalid_emotion"
    # Assert 422 Unprocessable Entity error

def test_promotion_audit_log():
    """Test that PromotionLog captures metadata"""
    # Stage a video
    # Query PromotionLog table
    # Verify: video_id, from_split, to_split, intended_label, actor, timestamp
```

**Run Command**:
```bash
pytest tests/test_metadata_persistence.py -v
```

**Expected Outcome**: All tests pass, confirming metadata persistence works

---

### 1.2 Manual Validation Test

**Steps**:
1. Start services:
   ```bash
   # Terminal 1: FastAPI backend
   ./start_media_api.sh
   
   # Terminal 2: Streamlit UI
   streamlit run apps/web/landing_page.py
   ```

2. Generate and classify a video:
   - Enter prompt: "happy person smiling"
   - Generate video
   - Select emotion: "happy"
   - Click "Submit Classification"

3. Verify in database:
   ```sql
   -- Connect to PostgreSQL
   psql -U reachy_app -d reachy_local
   
   -- Check video metadata
   SELECT video_id, file_path, split, label, created_at 
   FROM video 
   WHERE split = 'dataset_all' 
   ORDER BY created_at DESC 
   LIMIT 5;
   
   -- Check promotion log
   SELECT promotion_id, video_id, from_split, to_split, intended_label, actor, created_at
   FROM promotion_log
   ORDER BY created_at DESC
   LIMIT 5;
   ```

4. Verify on filesystem:
   ```bash
   ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/dataset_all/
   ```

**Expected Results**:
- ✅ Video file exists in `dataset_all/`
- ✅ Database record shows `label = 'happy'`
- ✅ PromotionLog entry exists with correct metadata
- ✅ UI shows success message

---

## Phase 2: Enhance Video Listing with Metadata 📋

**Goal**: Display emotion labels in the UI for review

### 2.1 Add Database Query to List Endpoint

**File**: `apps/api/app/routers/media.py` or create new `apps/api/app/routers/videos.py`

**Changes**:
```python
@router.get("/api/videos/list")
async def list_videos_with_metadata(
    split: str = Query(..., pattern="^(temp|dataset_all|train|test)$"),
    label: Optional[str] = Query(None),  # Filter by emotion
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """List videos with metadata from database"""
    # Query Video table with filters
    # Return: video_id, file_path, split, label, size_bytes, created_at
```

**Test**:
```python
def test_list_videos_with_labels():
    """Test listing videos filtered by emotion label"""
    # Create 5 videos: 2 happy, 2 sad, 1 angry
    # Query: GET /api/videos/list?split=dataset_all&label=happy
    # Assert: returns only 2 happy videos
```

---

### 2.2 Update Landing Page to Show Metadata

**File**: `apps/web/landing_page.py`

**Add new section**: "📊 Dataset Overview"

```python
# After video classification section
st.markdown("### 📊 Dataset Overview")

# Query dataset_all videos with labels
try:
    dataset_videos = list_videos_api(split="dataset_all", limit=100)
    
    # Group by emotion
    emotion_counts = {}
    for video in dataset_videos.get("videos", []):
        label = video.get("label", "unlabeled")
        emotion_counts[label] = emotion_counts.get(label, 0) + 1
    
    # Display as metrics
    cols = st.columns(len(emotion_counts))
    for idx, (emotion, count) in enumerate(emotion_counts.items()):
        with cols[idx]:
            st.metric(label=emotion.title(), value=count)
    
    # Show recent videos
    with st.expander("Recent Classifications"):
        for video in dataset_videos.get("videos", [])[:10]:
            st.caption(f"🎬 {video['file_path']} → {video['label']}")
except Exception as e:
    st.warning(f"Unable to load dataset overview: {e}")
```

**Test**: Manually verify UI shows emotion counts and recent videos

---

## Phase 3: Add Metadata Query/Filter Capabilities 🔍

**Goal**: Enable searching and filtering videos by emotion

### 3.1 Create Search Endpoint

**File**: `apps/api/app/routers/videos.py`

```python
@router.get("/api/videos/search")
async def search_videos(
    label: Optional[str] = None,
    split: Optional[str] = None,
    min_date: Optional[datetime] = None,
    max_date: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Search videos by metadata filters"""
    # Build dynamic query with filters
    # Return paginated results
```

**Test**:
```python
def test_search_videos_by_date_range():
    """Test searching videos within date range"""
    # Create videos with different timestamps
    # Search: min_date=yesterday, max_date=today
    # Assert: returns only videos in range
```

---

### 3.2 Add Export Functionality

**File**: `apps/web/landing_page.py`

```python
# Add export button
if st.button("📥 Export Dataset Manifest"):
    try:
        # Call manifest rebuild endpoint
        response = rebuild_manifest()
        manifest_path = response.get("manifest_path")
        st.success(f"Manifest created: {manifest_path}")
        
        # Provide download link
        with open(manifest_path, "r") as f:
            manifest_data = f.read()
        st.download_button(
            label="Download Manifest",
            data=manifest_data,
            file_name="dataset_manifest.jsonl",
            mime="application/jsonl",
        )
    except Exception as e:
        st.error(f"Export failed: {e}")
```

---

## Phase 4: Manifest Generation for Training 🎯

**Goal**: Generate training manifests from labeled dataset

### 4.1 Implement Manifest Builder

**File**: `apps/api/app/manifest.py` (already exists, enhance it)

**Functionality**:
- Read all videos from `dataset_all/` with labels
- Generate JSONL manifest:
  ```jsonl
  {"video_id": "abc123", "file_path": "dataset_all/video1.mp4", "label": "happy", "split": "dataset_all"}
  {"video_id": "def456", "file_path": "dataset_all/video2.mp4", "label": "sad", "split": "dataset_all"}
  ```

**Endpoint**:
```python
@router.post("/api/manifest/rebuild")
async def rebuild_manifest(
    split: str = "dataset_all",
    db: AsyncSession = Depends(get_db),
):
    """Rebuild manifest from database metadata"""
    # Query all videos in split with labels
    # Write to /videos/manifests/{split}_manifest.jsonl
    # Return manifest path and dataset hash
```

**Test**:
```python
def test_manifest_generation():
    """Test manifest file generation"""
    # Create 10 labeled videos
    # Call rebuild_manifest()
    # Assert: manifest file exists
    # Assert: contains 10 entries with correct labels
    # Assert: dataset_hash is computed correctly
```

---

## Phase 5: Add Relabeling Capability 🔄

**Goal**: Allow correcting misclassified videos

### 5.1 Create Relabel Endpoint

**File**: `apps/api/app/routers/videos.py`

```python
@router.post("/api/videos/{video_id}/relabel")
async def relabel_video(
    video_id: str,
    new_label: str,
    reason: Optional[str] = None,
    correlation_id: str = Header(..., alias="X-Correlation-ID"),
    db: AsyncSession = Depends(get_db),
):
    """Update emotion label for a video"""
    # Validate new_label is valid emotion
    # Update Video.label in database
    # Create audit log entry in PromotionLog
    # Return updated video metadata
```

**Test**:
```python
def test_relabel_video():
    """Test changing emotion label"""
    # Create video with label="happy"
    # Relabel to "sad"
    # Assert: database updated
    # Assert: audit log created
    # Assert: file remains in same location
```

---

### 5.2 Add Relabel UI

**File**: `apps/web/landing_page.py`

```python
# In the classification section, add relabel option
st.markdown("### 🔄 Relabel Video")

video_id_input = st.text_input("Video ID to relabel")
new_emotion = st.selectbox("New emotion", emotion_options, key="relabel_emotion")

if st.button("Update Label"):
    try:
        response = relabel_video(video_id_input, new_emotion)
        st.success(f"Video relabeled to: {new_emotion}")
    except Exception as e:
        st.error(f"Relabel failed: {e}")
```

---

## Testing Strategy 🧪

### Unit Tests
```bash
# Test individual components
pytest tests/test_promote_service.py -v
pytest tests/test_video_repository.py -v
```

### Integration Tests
```bash
# Test full flow with database
pytest tests/test_metadata_persistence.py -v --integration
```

### End-to-End Tests
```bash
# Test UI → API → Database flow
pytest tests/test_e2e_classification.py -v --e2e
```

### Manual Testing Checklist
- [ ] Generate video via Luma AI
- [ ] Classify with each emotion type
- [ ] Verify database persistence
- [ ] Check filesystem organization
- [ ] Test relabeling
- [ ] Export manifest
- [ ] Verify audit logs

---

## Success Criteria ✅

### Phase 1 Complete When:
- [ ] All integration tests pass
- [ ] Manual validation confirms metadata in database
- [ ] Promotion logs are created correctly

### Phase 2 Complete When:
- [ ] UI displays emotion counts
- [ ] Recent videos show with labels
- [ ] List endpoint returns metadata

### Phase 3 Complete When:
- [ ] Search by emotion works
- [ ] Date range filtering works
- [ ] Export manifest succeeds

### Phase 4 Complete When:
- [ ] Manifest generation works
- [ ] JSONL format is correct
- [ ] Dataset hash is computed

### Phase 5 Complete When:
- [ ] Relabel endpoint works
- [ ] UI allows relabeling
- [ ] Audit trail is maintained

---

## Rollback Plan 🔙

If issues occur:
1. Stop FastAPI service: `sudo systemctl stop fastapi-media.service`
2. Restore database backup: `pg_restore -U reachy_app -d reachy_local backup.sql`
3. Revert code changes: `git checkout HEAD -- apps/web/landing_page.py apps/web/api_client.py`
4. Restart with old configuration

---

## Next Steps 🚀

**Immediate Actions**:
1. ✅ Update port configuration (DONE)
2. 🧪 Run Phase 1 validation tests
3. 📊 Implement Phase 2 UI enhancements
4. 🔍 Add Phase 3 search capabilities

**Priority**: Start with Phase 1 validation to ensure the foundation is solid before building additional features.
