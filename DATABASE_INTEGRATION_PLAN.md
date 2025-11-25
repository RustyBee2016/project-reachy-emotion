# Database Integration Plan — Postgres Wiring for Video Metadata & URLs

**Project**: Reachy_Local_08.4.2  
**Version**: 1.0  
**Date**: 2025-11-25  
**Status**: Ready for Implementation

---

## Executive Summary

This plan addresses the current limitation where the `GET /api/videos/{video_identifier}` endpoint returns filename stems (e.g., `"video_id": "luma_1"`) instead of canonical UUIDs from the Postgres database. The goal is to fully wire up the database for all required functionalities including metadata retrieval, URL generation, video listing, and proper UUID-based identification.

---

## Current State Analysis

### What Works
- ✅ Database schema is complete (`001_phase1_schema.sql`)
- ✅ SQLAlchemy models are defined (`models.py`)
- ✅ Stored procedures exist for business logic (`002_stored_procedures.sql`)
- ✅ Repository pattern implemented (`VideoRepository`)
- ✅ Promotion/staging workflows use DB correctly
- ✅ File-based video discovery works (`_find_video_file`)

### What's Missing
- ❌ `GET /api/videos/{video_identifier}` returns filename stem, not UUID
- ❌ No endpoint to list videos from database with pagination
- ❌ No endpoint to get video by UUID
- ❌ No endpoint to generate streaming URLs
- ❌ Metadata fields (duration, fps, width, height) not returned
- ❌ No way to query videos by split or label
- ❌ Thumbnail endpoint doesn't check DB for existence

---

## Architecture Overview

### Data Flow
```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ GET /api/videos/{uuid}
       ▼
┌─────────────────────┐
│  FastAPI Gateway    │
│  (gateway_upstream) │
└──────┬──────────────┘
       │
       ├─────────────┐
       │             │
       ▼             ▼
┌──────────┐   ┌─────────┐
│ Postgres │   │ FileSystem│
│ (metadata)│   │ (videos) │
└──────────┘   └─────────┘
```

### Key Principles
1. **Database is source of truth** for video_id (UUID), metadata, labels, splits
2. **Filesystem stores actual video files** at paths recorded in DB
3. **Endpoints accept both UUIDs and filenames** for backward compatibility
4. **All responses include canonical UUID** from database

---

## Implementation Phases

### Phase 1: Enhanced Video Metadata Endpoint ✓

**Goal**: Make `GET /api/videos/{video_identifier}` return DB metadata including UUID

**Changes**:
- Accept both UUID and filename as `video_identifier`
- Query database first by UUID, then by file_path
- Return full metadata: UUID, duration, fps, dimensions, label, split
- Fallback to filesystem-only mode if DB record not found (with warning)

**New Response Schema**:
```json
{
  "status": "ok",
  "video": {
    "schema_version": "v1",
    "video_id": "550e8400-e29b-41d4-a716-446655440000",  // UUID from DB
    "file_name": "luma_1.mp4",
    "file_path": "temp/luma_1.mp4",
    "split": "temp",
    "label": "happy",
    "size_bytes": 1048576,
    "duration_sec": 5.2,
    "fps": 30.0,
    "width": 1920,
    "height": 1080,
    "sha256": "abc123...",
    "mtime": 1700000000.0,
    "created_at": "2025-11-25T12:00:00Z",
    "updated_at": "2025-11-25T12:00:00Z"
  }
}
```

---

### Phase 2: Video Listing Endpoints ✓

**Goal**: Enable querying videos from database with filters and pagination

**New Endpoints**:

#### 2.1 List Videos
```
GET /api/videos/list?split={split}&label={label}&limit={n}&offset={m}
```

**Query Parameters**:
- `split` (optional): Filter by split (temp, dataset_all, train, test)
- `label` (optional): Filter by emotion label
- `limit` (default: 50, max: 500): Number of results
- `offset` (default: 0): Pagination offset
- `order_by` (optional): created_at, updated_at, size_bytes (default: created_at desc)

**Response**:
```json
{
  "status": "ok",
  "videos": [
    {
      "video_id": "uuid-1",
      "file_name": "video1.mp4",
      "file_path": "temp/video1.mp4",
      "split": "temp",
      "label": null,
      "size_bytes": 1048576,
      "duration_sec": 5.0,
      "created_at": "2025-11-25T12:00:00Z"
    }
  ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "total": 150,
    "has_more": true
  }
}
```

#### 2.2 Get Video by UUID
```
GET /api/videos/by-uuid/{uuid}
```

**Response**: Same as enhanced metadata endpoint

---

### Phase 3: Video URL & Streaming Endpoints ✓

**Goal**: Generate proper URLs for video playback and downloads

**New Endpoints**:

#### 3.1 Get Video Stream URL
```
GET /api/videos/{video_identifier}/url
```

**Response**:
```json
{
  "status": "ok",
  "video_id": "uuid",
  "stream_url": "/videos/temp/luma_1.mp4",
  "thumbnail_url": "/thumbs/luma_1.jpg",
  "expires_at": null
}
```

#### 3.2 Enhanced Thumbnail Endpoint
```
GET /api/videos/{video_identifier}/thumb
```

**Changes**:
- Check DB for video existence first
- Return 404 if video not in DB (even if thumbnail file exists)
- Log access for analytics

---

### Phase 4: Additional Utility Endpoints ✓

#### 4.1 Video Statistics
```
GET /api/videos/stats
```

**Response**:
```json
{
  "status": "ok",
  "stats": {
    "total_videos": 1500,
    "by_split": {
      "temp": 50,
      "dataset_all": 1200,
      "train": 150,
      "test": 100
    },
    "by_label": {
      "happy": 300,
      "sad": 250,
      "neutral": 400
    },
    "total_size_bytes": 15728640000,
    "total_duration_sec": 7500.0
  }
}
```

#### 4.2 Video Search
```
GET /api/videos/search?q={query}&field={file_path|sha256}
```

**Response**: List of matching videos

---

## Database Query Patterns

### Pattern 1: Get Video by UUID
```python
async def get_video_by_uuid(session: AsyncSession, video_id: str) -> models.Video | None:
    stmt = select(models.Video).where(models.Video.video_id == video_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

### Pattern 2: Get Video by File Path
```python
async def get_video_by_path(session: AsyncSession, file_path: str) -> models.Video | None:
    stmt = select(models.Video).where(models.Video.file_path == file_path)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

### Pattern 3: List Videos with Filters
```python
async def list_videos(
    session: AsyncSession,
    split: str | None = None,
    label: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[models.Video], int]:
    stmt = select(models.Video)
    
    if split:
        stmt = stmt.where(models.Video.split == split)
    if label:
        stmt = stmt.where(models.Video.label == label)
    
    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await session.scalar(count_stmt)
    
    # Get paginated results
    stmt = stmt.order_by(models.Video.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    videos = result.scalars().all()
    
    return videos, total
```

---

## Testing Strategy

### Unit Tests

#### Test 1: Video Metadata Endpoint
```python
async def test_get_video_metadata_by_uuid(client, db_session):
    """Test getting video metadata using UUID."""
    # Setup: Create video in DB
    video = models.Video(
        video_id="550e8400-e29b-41d4-a716-446655440000",
        file_path="temp/test_video.mp4",
        split="temp",
        size_bytes=1048576,
        sha256="abc123",
    )
    db_session.add(video)
    await db_session.commit()
    
    # Test: Get by UUID
    response = await client.get("/api/videos/550e8400-e29b-41d4-a716-446655440000")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["video"]["video_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert data["video"]["file_name"] == "test_video.mp4"
```

#### Test 2: Video Metadata by Filename (Backward Compatibility)
```python
async def test_get_video_metadata_by_filename(client, db_session):
    """Test getting video metadata using filename (legacy)."""
    # Setup
    video = models.Video(
        video_id="550e8400-e29b-41d4-a716-446655440000",
        file_path="temp/luma_1.mp4",
        split="temp",
        size_bytes=1048576,
        sha256="abc123",
    )
    db_session.add(video)
    await db_session.commit()
    
    # Test: Get by filename
    response = await client.get("/api/videos/luma_1.mp4")
    
    # Assert: Should return UUID from DB
    assert response.status_code == 200
    data = response.json()
    assert data["video"]["video_id"] == "550e8400-e29b-41d4-a716-446655440000"
```

#### Test 3: List Videos with Pagination
```python
async def test_list_videos_pagination(client, db_session):
    """Test video listing with pagination."""
    # Setup: Create 100 videos
    for i in range(100):
        video = models.Video(
            file_path=f"temp/video_{i}.mp4",
            split="temp",
            size_bytes=1048576,
            sha256=f"sha{i}",
        )
        db_session.add(video)
    await db_session.commit()
    
    # Test: Get first page
    response = await client.get("/api/videos/list?limit=20&offset=0")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 20
    assert data["pagination"]["total"] == 100
    assert data["pagination"]["has_more"] is True
```

#### Test 4: Filter Videos by Split
```python
async def test_list_videos_filter_by_split(client, db_session):
    """Test filtering videos by split."""
    # Setup: Create videos in different splits
    for split in ["temp", "dataset_all", "train"]:
        for i in range(10):
            video = models.Video(
                file_path=f"{split}/video_{i}.mp4",
                split=split,
                label="happy" if split != "temp" else None,
                size_bytes=1048576,
                sha256=f"{split}_sha{i}",
            )
            db_session.add(video)
    await db_session.commit()
    
    # Test: Filter by dataset_all
    response = await client.get("/api/videos/list?split=dataset_all")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 10
    assert all(v["split"] == "dataset_all" for v in data["videos"])
```

#### Test 5: Video Not Found
```python
async def test_get_video_not_found(client):
    """Test 404 when video doesn't exist."""
    response = await client.get("/api/videos/nonexistent-uuid")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]["message"].lower()
```

#### Test 6: Video URL Generation
```python
async def test_get_video_url(client, db_session):
    """Test video URL generation."""
    # Setup
    video = models.Video(
        video_id="550e8400-e29b-41d4-a716-446655440000",
        file_path="temp/test_video.mp4",
        split="temp",
        size_bytes=1048576,
        sha256="abc123",
    )
    db_session.add(video)
    await db_session.commit()
    
    # Test
    response = await client.get("/api/videos/550e8400-e29b-41d4-a716-446655440000/url")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "stream_url" in data
    assert "thumbnail_url" in data
    assert data["video_id"] == "550e8400-e29b-41d4-a716-446655440000"
```

### Integration Tests

#### Test 7: End-to-End Video Workflow
```python
async def test_video_workflow_end_to_end(client, db_session, tmp_path):
    """Test complete video workflow: ingest → query → promote."""
    # 1. Simulate video ingest (create DB record)
    video = models.Video(
        file_path="temp/workflow_test.mp4",
        split="temp",
        size_bytes=1048576,
        sha256="workflow_sha",
        duration_sec=5.0,
        fps=30.0,
        width=1920,
        height=1080,
    )
    db_session.add(video)
    await db_session.commit()
    video_id = video.video_id
    
    # 2. Query by UUID
    response = await client.get(f"/api/videos/{video_id}")
    assert response.status_code == 200
    assert response.json()["video"]["video_id"] == video_id
    
    # 3. List videos in temp
    response = await client.get("/api/videos/list?split=temp")
    assert response.status_code == 200
    assert any(v["video_id"] == video_id for v in response.json()["videos"])
    
    # 4. Get video URL
    response = await client.get(f"/api/videos/{video_id}/url")
    assert response.status_code == 200
    assert "stream_url" in response.json()
```

---

## Implementation Checklist

### Phase 1: Enhanced Metadata Endpoint
- [ ] Create `VideoQueryService` in `app/services/video_query_service.py`
- [ ] Add `get_video_by_identifier()` method (tries UUID, then file_path)
- [ ] Update `get_video_metadata()` in `gateway_upstream.py`
- [ ] Add enhanced `VideoMetadataResponse` schema
- [ ] Write unit tests for UUID lookup
- [ ] Write unit tests for filename lookup
- [ ] Write unit tests for not found cases

### Phase 2: Video Listing
- [ ] Create `list_videos()` endpoint in `gateway_upstream.py`
- [ ] Add `VideoListResponse` and `PaginationInfo` schemas
- [ ] Implement filtering by split and label
- [ ] Implement pagination with limit/offset
- [ ] Add sorting options
- [ ] Write unit tests for pagination
- [ ] Write unit tests for filtering
- [ ] Write unit tests for edge cases (empty results, invalid params)

### Phase 3: Video URLs
- [ ] Create `get_video_url()` endpoint
- [ ] Add `VideoUrlResponse` schema
- [ ] Implement URL generation logic
- [ ] Update thumbnail endpoint to check DB
- [ ] Write unit tests for URL generation
- [ ] Write integration tests for streaming

### Phase 4: Statistics & Search
- [ ] Create `get_video_stats()` endpoint
- [ ] Create `search_videos()` endpoint
- [ ] Add caching for stats (optional)
- [ ] Write unit tests for stats aggregation
- [ ] Write unit tests for search

### Phase 5: Testing & Documentation
- [ ] Run all unit tests
- [ ] Run integration tests
- [ ] Test backward compatibility with existing clients
- [ ] Update API documentation
- [ ] Update memory-bank with decisions
- [ ] Create runbook for troubleshooting

---

## Backward Compatibility

### Guarantees
1. **Existing filename-based calls still work**: `GET /api/videos/luma_1.mp4` returns data
2. **Response includes both UUID and filename**: Clients can migrate gradually
3. **Filesystem fallback**: If DB record missing, returns filesystem-only metadata with warning
4. **Existing promotion endpoints unchanged**: No breaking changes to promotion workflow

### Migration Path for Clients
```python
# Old way (still works)
response = requests.get("/api/videos/luma_1.mp4")
video_id = response.json()["video"]["video_id"]  # Now returns UUID!

# New way (recommended)
response = requests.get("/api/videos/550e8400-e29b-41d4-a716-446655440000")
video_id = response.json()["video"]["video_id"]  # UUID
```

---

## Performance Considerations

### Database Indexes
Already in place:
- `ix_video_split` on `split` column
- `ix_video_label` on `label` column
- `uq_video_sha256_size` on `(sha256, size_bytes)`

### Query Optimization
- Use `select_from()` for count queries to avoid full table scans
- Limit default page size to 50, max 500
- Add `created_at` index if sorting by date is slow
- Consider materialized view for stats if dataset > 100k videos

### Caching Strategy (Future)
- Cache video stats for 5 minutes
- Cache video metadata for 1 minute
- Invalidate on promotion/relabel events

---

## Error Handling

### Error Codes
- `404`: Video not found (neither in DB nor filesystem)
- `400`: Invalid UUID format or query parameters
- `500`: Database connection error
- `503`: Database unavailable

### Error Response Format
```json
{
  "error": "not_found",
  "message": "Video not found: 550e8400-e29b-41d4-a716-446655440000",
  "video_id": "550e8400-e29b-41d4-a716-446655440000",
  "checked_locations": ["database", "filesystem"]
}
```

---

## Monitoring & Observability

### Metrics to Track
- `video_metadata_requests_total{source="uuid|filename|filesystem"}`
- `video_list_requests_total{split="temp|dataset_all|train|test"}`
- `video_db_query_duration_seconds`
- `video_not_found_total{reason="db|filesystem|both"}`

### Logging
```python
logger.info(
    "video_metadata_request",
    extra={
        "video_identifier": video_identifier,
        "lookup_method": "uuid",
        "found_in_db": True,
        "duration_ms": 15.2,
    }
)
```

---

## Security Considerations

### Input Validation
- Validate UUID format before DB query
- Sanitize file paths to prevent directory traversal
- Limit pagination offset to prevent resource exhaustion
- Rate limit listing endpoints

### Authorization (Future)
- Add JWT validation for sensitive endpoints
- Implement per-user video access controls
- Audit log for video access

---

## Rollout Plan

### Step 1: Deploy Enhanced Metadata Endpoint
- Deploy Phase 1 changes
- Monitor error rates and latency
- Verify UUID responses in production

### Step 2: Deploy Listing Endpoints
- Deploy Phase 2 changes
- Test pagination with production data
- Monitor query performance

### Step 3: Deploy URL & Utility Endpoints
- Deploy Phase 3 & 4 changes
- Update client applications to use UUIDs
- Monitor adoption metrics

### Step 4: Deprecate Filesystem-Only Mode
- Add deprecation warnings for filename-based lookups
- Migrate remaining clients to UUID-based calls
- Remove filesystem fallback (optional, after 6 months)

---

## Success Criteria

### Functional
- ✅ All endpoints return canonical UUIDs from database
- ✅ Backward compatibility maintained for filename-based lookups
- ✅ Pagination works correctly for large datasets
- ✅ Filtering by split and label returns accurate results
- ✅ Video URLs are correctly generated

### Performance
- ✅ Metadata endpoint p95 latency < 50ms
- ✅ List endpoint p95 latency < 100ms (for 50 results)
- ✅ Database query time < 20ms for indexed lookups
- ✅ No N+1 query problems

### Testing
- ✅ Unit test coverage > 85%
- ✅ All integration tests pass
- ✅ Manual testing confirms backward compatibility
- ✅ Load testing shows acceptable performance under 100 req/s

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Implement Phase 1** (Enhanced Metadata Endpoint)
3. **Write and run tests** for Phase 1
4. **Deploy Phase 1** to staging
5. **Iterate through remaining phases** with testing after each
6. **Update documentation** and memory-bank
7. **Monitor production** metrics and errors

---

## Appendix: File Structure

```
apps/api/app/
├── routers/
│   └── gateway_upstream.py          # Enhanced with new endpoints
├── services/
│   ├── video_query_service.py       # NEW: Video query logic
│   └── promote_service.py           # Existing
├── repositories/
│   └── video_repository.py          # Enhanced with new queries
├── schemas/
│   ├── video.py                     # NEW: Video response schemas
│   └── responses.py                 # Existing
└── db/
    └── models.py                    # Existing

tests/apps/api/
├── test_video_metadata.py           # NEW: Phase 1 tests
├── test_video_listing.py            # NEW: Phase 2 tests
├── test_video_urls.py               # NEW: Phase 3 tests
└── test_video_integration.py        # NEW: E2E tests
```

---

**End of Plan**
