# Database Integration — Implementation Recommendations

**Project**: Reachy_Local_08.4.2  
**Date**: 2025-11-25  
**Priority**: High  
**Estimated Effort**: 2-3 days

---

## Quick Start

This document provides actionable recommendations for implementing the database integration plan. Follow these steps in order, testing after each phase.

Current workflow alignment:
- Promote labeled videos directly from `temp` to `train/<label>`
- Prepare run-specific training frames in `train/epoch_XX/<label>` with manifests/hash metadata

---

## Phase 1: Enhanced Video Metadata Endpoint

### 1.1 Create Video Query Service

**File**: `apps/api/app/services/video_query_service.py`

```python
"""Service for querying video metadata from database and filesystem."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import models
from ..config import AppConfig


class VideoQueryService:
    """Handles video metadata queries with DB-first, filesystem-fallback strategy."""

    def __init__(self, session: AsyncSession, config: AppConfig):
        self._session = session
        self._config = config

    async def get_video_by_identifier(
        self, identifier: str
    ) -> tuple[models.Video | None, str]:
        """
        Get video by UUID or filename.
        
        Returns:
            Tuple of (video_model, lookup_method)
            lookup_method is one of: "uuid", "file_path", "not_found"
        """
        # Try as UUID first
        if self._is_valid_uuid(identifier):
            video = await self._get_by_uuid(identifier)
            if video:
                return video, "uuid"
        
        # Try as file path (exact match)
        video = await self._get_by_file_path(identifier)
        if video:
            return video, "file_path"
        
        # Try with common variations
        video = await self._get_by_file_path_variations(identifier)
        if video:
            return video, "file_path"
        
        return None, "not_found"

    async def _get_by_uuid(self, video_id: str) -> models.Video | None:
        """Get video by UUID."""
        stmt = select(models.Video).where(models.Video.video_id == video_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_by_file_path(self, file_path: str) -> models.Video | None:
        """Get video by exact file path match."""
        stmt = select(models.Video).where(models.Video.file_path == file_path)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_by_file_path_variations(self, identifier: str) -> models.Video | None:
        """Try common file path variations."""
        # Try with different split prefixes
        for split in ["temp", "train", "test", "dataset_all"]:  # dataset_all = legacy compatibility
            # Try as-is
            path = f"{split}/{identifier}"
            video = await self._get_by_file_path(path)
            if video:
                return video
            
            # Try with .mp4 extension if not present
            if not identifier.endswith(".mp4"):
                path_with_ext = f"{split}/{identifier}.mp4"
                video = await self._get_by_file_path(path_with_ext)
                if video:
                    return video
        
        return None

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        """Check if string is a valid UUID."""
        try:
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            return False
```

**Key Features**:
- ✅ Tries UUID lookup first (fastest)
- ✅ Falls back to file path matching
- ✅ Handles filename variations (.mp4 extension, split prefixes)
- ✅ Returns lookup method for logging/metrics

---

### 1.2 Update Gateway Upstream Router

**File**: `apps/api/app/routers/gateway_upstream.py`

**Changes**:

1. **Add new response schema** (after line 52):

```python
class EnhancedVideoMetadataPayload(BaseModel):
    """Enhanced video metadata with database fields."""
    schema_version: str = Field(default="v1")
    video_id: str  # UUID from database
    file_name: str
    file_path: str
    split: str
    label: Optional[str] = None
    size_bytes: int
    duration_sec: Optional[float] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    sha256: Optional[str] = None
    mtime: float
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    lookup_method: str = Field(default="filesystem", description="How video was found: uuid, file_path, or filesystem")
```

2. **Update `get_video_metadata` function** (replace lines 118-136):

```python
@router.get("/api/videos/{video_identifier:path}")
async def get_video_metadata(
    video_identifier: str,
    config: AppConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """Return metadata for the requested video file.
    
    Accepts either UUID or filename. Returns canonical UUID from database.
    """
    
    # Try database first
    query_service = VideoQueryService(session, config)
    video_model, lookup_method = await query_service.get_video_by_identifier(video_identifier)
    
    if video_model:
        # Found in database - return full metadata
        video_path = config.videos_root / video_model.file_path
        
        # Verify file still exists
        if not video_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "file_missing",
                    "message": f"Video record exists but file not found: {video_model.file_path}",
                    "video_id": video_model.video_id,
                },
            )
        
        stat_info = video_path.stat()
        payload = EnhancedVideoMetadataPayload(
            video_id=video_model.video_id,
            file_name=video_path.name,
            file_path=video_model.file_path,
            split=video_model.split.value if hasattr(video_model.split, 'value') else str(video_model.split),
            label=video_model.label.value if video_model.label and hasattr(video_model.label, 'value') else video_model.label,
            size_bytes=video_model.size_bytes,
            duration_sec=video_model.duration_sec,
            fps=video_model.fps,
            width=video_model.width,
            height=video_model.height,
            sha256=video_model.sha256,
            mtime=stat_info.st_mtime,
            created_at=video_model.created_at.isoformat() if video_model.created_at else None,
            updated_at=video_model.updated_at.isoformat() if video_model.updated_at else None,
            lookup_method=lookup_method,
        )
        return {"status": "ok", "video": payload.dict()}
    
    # Fallback to filesystem-only lookup (legacy support)
    try:
        video_path, split = _find_video_file(video_identifier, config)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"Video not found in database or filesystem: {video_identifier}",
            },
        )
    
    # Return filesystem-only metadata with warning
    stat_info = video_path.stat()
    relative_path = video_path.relative_to(config.videos_root)
    payload = VideoMetadataPayload(
        video_id=Path(video_path).stem,  # Filename stem (not UUID)
        file_name=video_path.name,
        split=split,
        file_path=str(relative_path),
        size_bytes=stat_info.st_size,
        mtime=stat_info.st_mtime,
    )
    
    return {
        "status": "ok",
        "video": payload.dict(),
        "warning": "Video found in filesystem but not in database. UUID is filename stem, not canonical ID.",
    }
```

**Key Improvements**:
- ✅ Database-first lookup
- ✅ Returns canonical UUID
- ✅ Includes all metadata fields
- ✅ Backward compatible with filesystem fallback
- ✅ Clear error messages

---

## Phase 2: Video Listing Endpoints

### 2.1 Add Listing Schemas

**File**: `apps/api/app/schemas/video.py` (NEW)

```python
"""Pydantic schemas for video API responses."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class VideoSummary(BaseModel):
    """Summary of video metadata for list responses."""
    
    video_id: str
    file_name: str
    file_path: str
    split: str
    label: Optional[str] = None
    size_bytes: int
    duration_sec: Optional[float] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    sha256: str
    created_at: str
    updated_at: Optional[str] = None


class PaginationInfo(BaseModel):
    """Pagination metadata."""
    
    limit: int
    offset: int
    total: int
    has_more: bool


class VideoListResponse(BaseModel):
    """Response for video listing endpoint."""
    
    status: str = "ok"
    videos: list[VideoSummary]
    pagination: PaginationInfo
```

### 2.2 Add Listing Endpoint

**File**: `apps/api/app/routers/gateway_upstream.py`

**Add after the `get_video_metadata` function**:

```python
@router.get("/api/videos/list")
async def list_videos(
    split: Optional[str] = None,
    label: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    order_by: str = Query(default="created_at", regex="^(created_at|updated_at|size_bytes)$"),
    order: str = Query(default="desc", regex="^(asc|desc)$"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """List videos with filtering and pagination.
    
    Query Parameters:
        split: Filter by split (temp, train, test; dataset_all for legacy compatibility)
        label: Filter by emotion label
        limit: Number of results (1-500, default 50)
        offset: Pagination offset (default 0)
        order_by: Sort field (created_at, updated_at, size_bytes)
        order: Sort direction (asc, desc)
    """
    from sqlalchemy import func, desc, asc
    
    # Validate split
    if split and split not in ("temp", "train", "test", "dataset_all"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_split", "message": f"Invalid split: {split}"},
        )
    
    # Validate label
    if label and label not in VALID_EMOTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_label", "message": f"Invalid label: {label}"},
        )
    
    # Build query
    stmt = select(models.Video)
    
    if split:
        stmt = stmt.where(models.Video.split == split)
    if label:
        stmt = stmt.where(models.Video.label == label)
    
    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await session.scalar(count_stmt) or 0
    
    # Apply sorting
    order_col = getattr(models.Video, order_by)
    if order == "desc":
        stmt = stmt.order_by(desc(order_col))
    else:
        stmt = stmt.order_by(asc(order_col))
    
    # Apply pagination
    stmt = stmt.limit(limit).offset(offset)
    
    # Execute query
    result = await session.execute(stmt)
    videos = result.scalars().all()
    
    # Build response
    video_summaries = []
    for video in videos:
        video_summaries.append({
            "video_id": video.video_id,
            "file_name": Path(video.file_path).name,
            "file_path": video.file_path,
            "split": video.split.value if hasattr(video.split, 'value') else str(video.split),
            "label": video.label.value if video.label and hasattr(video.label, 'value') else video.label,
            "size_bytes": video.size_bytes,
            "duration_sec": video.duration_sec,
            "fps": video.fps,
            "width": video.width,
            "height": video.height,
            "sha256": video.sha256,
            "created_at": video.created_at.isoformat() if video.created_at else None,
            "updated_at": video.updated_at.isoformat() if video.updated_at else None,
        })
    
    has_more = (offset + limit) < total
    
    return {
        "status": "ok",
        "videos": video_summaries,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": has_more,
        },
    }
```

---

## Phase 3: Video URL Endpoints

### 3.1 Add URL Generation Endpoint

**File**: `apps/api/app/routers/gateway_upstream.py`

```python
@router.get("/api/videos/{video_identifier:path}/url")
async def get_video_url(
    video_identifier: str,
    config: AppConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """Generate streaming URL for video.
    
    Returns URLs for video streaming and thumbnail.
    """
    # Get video from database
    query_service = VideoQueryService(session, config)
    video_model, lookup_method = await query_service.get_video_by_identifier(video_identifier)
    
    if not video_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Video not found: {video_identifier}"},
        )
    
    # Generate URLs
    stream_url = f"/videos/{video_model.file_path}"
    thumbnail_url = f"/thumbs/{Path(video_model.file_path).stem}.jpg"
    
    return {
        "status": "ok",
        "video_id": video_model.video_id,
        "stream_url": stream_url,
        "thumbnail_url": thumbnail_url,
        "expires_at": None,  # No expiration for now
    }
```

### 3.2 Enhance Thumbnail Endpoint

**File**: `apps/api/app/routers/gateway_upstream.py`

**Replace the existing `get_video_thumbnail` function** (lines 139-154):

```python
@router.get("/api/videos/{video_identifier:path}/thumb")
async def get_video_thumbnail(
    video_identifier: str,
    config: AppConfig = Depends(get_config),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Return the thumbnail image for a given video.
    
    Checks database for video existence before serving thumbnail.
    """
    # Verify video exists in database
    query_service = VideoQueryService(session, config)
    video_model, _ = await query_service.get_video_by_identifier(video_identifier)
    
    if not video_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Video not found: {video_identifier}"},
        )
    
    # Get thumbnail path
    video_stem = Path(video_model.file_path).stem
    thumb_path = config.thumbs_path / f"{video_stem}.jpg"
    
    if not thumb_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "thumbnail_not_found",
                "message": f"Thumbnail not found for video: {video_model.video_id}",
                "video_id": video_model.video_id,
            },
        )
    
    return FileResponse(thumb_path, media_type="image/jpeg")
```

---

## Phase 4: Testing Setup

### 4.1 Create Test Fixtures

**File**: `tests/apps/api/conftest.py`

```python
"""Pytest fixtures for API tests."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from apps.api.app.main import app
from apps.api.app.db.base import Base
from apps.api.app.deps import get_db


# Test database URL (use in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create test database session."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """Create test HTTP client with database override."""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()
```

### 4.2 Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/apps/api/ -v

# Run specific test file
pytest tests/apps/api/test_video_metadata.py -v

# Run with coverage
pytest tests/apps/api/ --cov=apps/api/app --cov-report=html
```

---

## Implementation Order

### Day 1: Phase 1 - Enhanced Metadata
1. ✅ Create `VideoQueryService`
2. ✅ Update `get_video_metadata` endpoint
3. ✅ Add `EnhancedVideoMetadataPayload` schema
4. ✅ Write and run unit tests
5. ✅ Test manually with curl/Postman

### Day 2: Phase 2 - Listing Endpoints
1. ✅ Create video schemas (`VideoSummary`, `PaginationInfo`)
2. ✅ Implement `list_videos` endpoint
3. ✅ Write and run unit tests
4. ✅ Test pagination with large datasets
5. ✅ Test filtering combinations

### Day 3: Phase 3 - URL Endpoints & Polish
1. ✅ Implement `get_video_url` endpoint
2. ✅ Enhance `get_video_thumbnail` endpoint
3. ✅ Write and run integration tests
4. ✅ Performance testing
5. ✅ Documentation updates

---

## Testing Checklist

### Unit Tests
- [ ] Video metadata by UUID
- [ ] Video metadata by filename
- [ ] Video metadata not found
- [ ] Video listing empty database
- [ ] Video listing with pagination
- [ ] Video listing with filters (split, label)
- [ ] Video listing with sorting
- [ ] Video URL generation
- [ ] Thumbnail with DB check

### Integration Tests
- [ ] End-to-end video workflow
- [ ] Backward compatibility with existing clients
- [ ] Performance under load (100 req/s)
- [ ] Database connection failures
- [ ] Filesystem/DB inconsistencies

### Manual Tests
- [ ] Test with real video files
- [ ] Test with production-like data volume
- [ ] Test with various video formats
- [ ] Test error scenarios
- [ ] Test with concurrent requests

---

## Rollback Plan

If issues arise during deployment:

1. **Immediate**: Revert to previous version
2. **Database**: No schema changes, safe to rollback
3. **API**: Backward compatible, old clients still work
4. **Monitoring**: Check error rates, latency metrics

---

## Success Metrics

### Functional
- ✅ All endpoints return UUIDs from database
- ✅ Backward compatibility maintained
- ✅ All tests passing (>85% coverage)

### Performance
- ✅ Metadata endpoint p95 < 50ms
- ✅ List endpoint p95 < 100ms
- ✅ No database connection pool exhaustion

### Quality
- ✅ Zero production errors in first 24 hours
- ✅ No client complaints about breaking changes
- ✅ Monitoring dashboards show healthy metrics

---

## Next Steps After Implementation

1. **Monitor production** for 48 hours
2. **Gather feedback** from API consumers
3. **Optimize queries** if performance issues
4. **Add caching** for frequently accessed videos
5. **Implement Phase 4** (stats, search) if needed

---

**Ready to implement!** Start with Phase 1 and test thoroughly before proceeding.
