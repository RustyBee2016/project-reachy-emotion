# Module 6: API Integration

**Duration**: 4 hours
**Prerequisites**: Modules 1-5
**Goal**: Build FastAPI endpoints that interact with the database

---

## Learning Objectives

By the end of this module, you will be able to:
1. Structure FastAPI applications with database access
2. Use dependency injection for database sessions
3. Implement the service layer pattern
4. Handle errors and transactions properly
5. Validate request/response data with Pydantic

---

## Lesson 6.1: FastAPI Application Structure (30 minutes)

### Project Layout

The Reachy API follows a layered architecture:

```
apps/api/app/
├── main.py                 # FastAPI application entry point
├── config.py               # Configuration settings
├── deps.py                 # Dependency injection
├── db/
│   ├── base.py             # SQLAlchemy Base class
│   ├── models.py           # ORM models
│   ├── enums.py            # Enum definitions
│   └── session.py          # Session factory
├── schemas/
│   └── promote.py          # Pydantic schemas
├── routers/
│   ├── promote.py          # Promotion endpoints
│   └── metrics.py          # Metrics endpoints
├── services/
│   └── promote_service.py  # Business logic
└── repositories/
    └── video_repository.py # Data access layer
```

### The Main Application

**Source**: `apps/api/app/main.py` (lines 1-51)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import promote, metrics
from .config import settings

app = FastAPI(
    title="Reachy Emotion API",
    description="API for managing emotion recognition video metadata",
    version="1.0.0",
)

# CORS middleware for web UI access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(promote.router, prefix="/api/v1", tags=["promote"])
app.include_router(metrics.router, prefix="/api/v1", tags=["metrics"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### Configuration

**Source**: `apps/api/app/config.py` (lines 150-200)

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    REACHY_DATABASE_URL: str = "postgresql+asyncpg://reachy_app:password@localhost:5432/reachy_local"

    # Video storage
    REACHY_VIDEOS_ROOT: str = "/mnt/videos"

    # API settings
    REACHY_API_PORT: int = 8083
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

---

## Lesson 6.2: Dependency Injection (45 minutes)

### What is Dependency Injection?

**Dependency Injection (DI)** provides objects that a function needs, instead of the function creating them:

```python
# Without DI - function creates its own dependencies
async def get_video(video_id: str):
    db = create_database_connection()  # Hard to test!
    video = db.query(Video).get(video_id)
    db.close()
    return video

# With DI - dependencies are injected
async def get_video(video_id: str, db: AsyncSession = Depends(get_db)):
    video = await db.get(Video, video_id)
    return video
```

### Database Session Dependency

**Source**: `apps/api/app/deps.py` (lines 1-80)

```python
from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .db.session import get_async_sessionmaker
from .config import settings

# Create session factory once
_session_factory = None

def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = get_async_sessionmaker(settings.REACHY_DATABASE_URL)
    return _session_factory

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Using Dependencies in Routes

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_db
from ..db.models import Video
from sqlalchemy import select

router = APIRouter()

@router.get("/videos/{video_id}")
async def get_video(
    video_id: str,
    db: AsyncSession = Depends(get_db)  # Injected!
):
    result = await db.execute(
        select(Video).where(Video.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video
```

### Repository Dependencies

```python
from ..repositories.video_repository import VideoRepository

def get_video_repository(
    db: AsyncSession = Depends(get_db)
) -> VideoRepository:
    """Dependency that provides VideoRepository."""
    return VideoRepository(db)

@router.get("/videos")
async def list_videos(
    split: str = "temp",
    limit: int = 100,
    repo: VideoRepository = Depends(get_video_repository)
):
    return await repo.list_by_split(split, limit=limit)
```

### Dependency Chain

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DEPENDENCY CHAIN                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Request arrives at endpoint                                       │
│           │                                                          │
│           ▼                                                          │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  @router.get("/videos")                                      │   │
│   │  async def list_videos(                                      │   │
│   │      repo: VideoRepository = Depends(get_video_repository)  │   │
│   │  ):                                                          │   │
│   └──────────────────────────┬──────────────────────────────────┘   │
│                              │ Depends on                           │
│                              ▼                                       │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  def get_video_repository(                                   │   │
│   │      db: AsyncSession = Depends(get_db)                     │   │
│   │  ):                                                          │   │
│   │      return VideoRepository(db)                              │   │
│   └──────────────────────────┬──────────────────────────────────┘   │
│                              │ Depends on                           │
│                              ▼                                       │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  async def get_db():                                         │   │
│   │      async with session_factory() as session:               │   │
│   │          yield session                                       │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Lesson 6.3: Pydantic Schemas (45 minutes)

### Request and Response Validation

**Pydantic** schemas validate API request/response data:

**Source**: `apps/api/app/schemas/promote.py` (lines 1-186)

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum

class SplitType(str, Enum):
    temp = "temp"
    train = "train"
    test = "test"
    purged = "purged"
    dataset_all = "dataset_all"  # legacy compatibility

class EmotionType(str, Enum):
    neutral = "neutral"
    happy = "happy"
    sad = "sad"
    angry = "angry"
    surprise = "surprise"
    fearful = "fearful"

# Request schema
class PromoteRequest(BaseModel):
    video_id: str = Field(..., description="UUID of video to promote")
    dest_split: SplitType = Field(..., description="Target split")
    label: Optional[EmotionType] = Field(None, description="Emotion label")
    user_id: Optional[str] = Field(None, description="User performing action")
    idempotency_key: Optional[str] = Field(None, max_length=64)
    dry_run: bool = Field(False, description="Preview without executing")

    @field_validator("label")
    @classmethod
    def validate_label_for_split(cls, v, info):
        dest_split = info.data.get("dest_split")
        if dest_split == "train" and v is None:
            raise ValueError(f"Label required for {dest_split}")
        if dest_split in ("temp", "test", "purged") and v is not None:
            raise ValueError(f"Label not allowed for {dest_split}")
        return v

# Response schema
class PromoteResponse(BaseModel):
    success: bool
    video_id: str
    from_split: SplitType
    to_split: SplitType
    label: Optional[EmotionType]
    message: str

    class Config:
        from_attributes = True  # Allow from ORM objects

# Video schema
class VideoResponse(BaseModel):
    video_id: str
    file_path: str
    split: SplitType
    label: Optional[EmotionType]
    size_bytes: int
    duration_sec: Optional[float]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# List response with pagination
class VideoListResponse(BaseModel):
    items: list[VideoResponse]
    total: int
    limit: int
    offset: int
```

### Using Schemas in Routes

```python
from fastapi import APIRouter, Depends
from ..schemas.promote import PromoteRequest, PromoteResponse, VideoListResponse

router = APIRouter()

@router.post("/promote", response_model=PromoteResponse)
async def promote_video(
    request: PromoteRequest,  # Validated automatically!
    service: PromoteService = Depends(get_promote_service)
):
    return await service.promote(
        video_id=request.video_id,
        dest_split=request.dest_split,
        label=request.label,
        user_id=request.user_id,
        idempotency_key=request.idempotency_key,
        dry_run=request.dry_run
    )

@router.get("/videos", response_model=VideoListResponse)
async def list_videos(
    split: str = "temp",
    limit: int = 100,
    offset: int = 0,
    repo: VideoRepository = Depends(get_video_repository)
):
    videos = await repo.list_by_split(split, limit=limit, offset=offset)
    total = await repo.count_by_split(split)
    return VideoListResponse(
        items=videos,
        total=total,
        limit=limit,
        offset=offset
    )
```

---

## Lesson 6.4: The Service Layer (45 minutes)

### Why a Service Layer?

The service layer contains **business logic** separate from:
- HTTP handling (routers)
- Data access (repositories)

```
┌─────────────────────────────────────────────────────────────────────┐
│                   RESPONSIBILITIES                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ROUTER                    SERVICE                   REPOSITORY     │
│   ─────────────             ───────────────           ──────────     │
│   • Parse HTTP request      • Business rules         • SQL queries   │
│   • Validate input          • Orchestrate steps      • ORM operations│
│   • Return HTTP response    • Transaction logic      • Data mapping  │
│   • Handle HTTP errors      • Call repositories      • Connection    │
│                             • Logging                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### PromoteService

**Source**: `apps/api/app/services/promote_service.py` (lines 1-492)

```python
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import logging

from ..db.models import Video, PromotionLog
from ..repositories.video_repository import VideoRepository

logger = logging.getLogger(__name__)

class PromoteService:
    """Service for video promotion operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.video_repo = VideoRepository(db)

    async def promote(
        self,
        video_id: str,
        dest_split: str,
        label: Optional[str] = None,
        user_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        dry_run: bool = False
    ) -> dict:
        """
        Promote a video to a new split.

        This method:
        1. Checks idempotency (if key provided)
        2. Validates the video exists
        3. Validates business rules
        4. Executes the promotion (unless dry_run)
        5. Logs the action

        Args:
            video_id: UUID of video to promote
            dest_split: Target split (temp, train, test, purged; dataset_all for legacy compatibility)
            label: Emotion label (required for train; legacy compatibility for dataset_all)
            user_id: User performing the action
            idempotency_key: Key to prevent duplicate processing
            dry_run: If True, validate without executing

        Returns:
            dict with success, from_split, to_split, label, message
        """

        # 1. Check idempotency
        if idempotency_key:
            existing = await self._check_idempotency(idempotency_key)
            if existing:
                logger.info(f"Duplicate request with key {idempotency_key}")
                return existing

        # 2. Get video
        video = await self.video_repo.get_by_id(video_id)
        if not video:
            return await self._log_and_return_failure(
                video_id=video_id,
                from_split="unknown",
                to_split=dest_split,
                label=label,
                user_id=user_id,
                idempotency_key=idempotency_key,
                message="Video not found",
                dry_run=dry_run
            )

        # 3. Validate business rules
        validation_error = self._validate_promotion(video, dest_split, label)
        if validation_error:
            return await self._log_and_return_failure(
                video_id=video_id,
                from_split=video.split,
                to_split=dest_split,
                label=label,
                user_id=user_id,
                idempotency_key=idempotency_key,
                message=validation_error,
                dry_run=dry_run
            )

        # 4. Dry run check
        if dry_run:
            return await self._log_and_return_success(
                video_id=video_id,
                from_split=video.split,
                to_split=dest_split,
                label=label,
                user_id=user_id,
                idempotency_key=idempotency_key,
                message=f"Dry run: would promote from {video.split} to {dest_split}",
                dry_run=True
            )

        # 5. Execute promotion
        old_split = video.split
        video.split = dest_split
        video.label = label
        await self.db.flush()

        # 6. Log success
        return await self._log_and_return_success(
            video_id=video_id,
            from_split=old_split,
            to_split=dest_split,
            label=label,
            user_id=user_id,
            idempotency_key=idempotency_key,
            message="Video promoted successfully",
            dry_run=False
        )

    def _validate_promotion(
        self,
        video: Video,
        dest_split: str,
        label: Optional[str]
    ) -> Optional[str]:
        """Validate business rules for promotion."""

        # Label required for train (and dataset_all only for legacy compatibility)
        if dest_split in ("train", "dataset_all") and not label:
            return f"Label required for {dest_split}"

        # Label not allowed for temp, test, purged
        if dest_split in ("temp", "test", "purged") and label:
            return f"Label not allowed for {dest_split}"

        # Can't promote to same split
        if video.split == dest_split:
            return f"Video already in {dest_split}"

        return None

    async def _check_idempotency(self, key: str) -> Optional[dict]:
        """Check if this idempotency key was already processed."""
        result = await self.db.execute(
            select(PromotionLog)
            .where(PromotionLog.idempotency_key == key)
        )
        log = result.scalar_one_or_none()
        if log:
            return {
                "success": log.success,
                "video_id": str(log.video_id),
                "from_split": log.from_split,
                "to_split": log.to_split,
                "label": log.label,
                "message": "Duplicate request: already processed"
            }
        return None

    async def _log_and_return_success(self, **kwargs) -> dict:
        """Log successful promotion and return result."""
        log = PromotionLog(
            video_id=kwargs["video_id"],
            from_split=kwargs["from_split"],
            to_split=kwargs["to_split"],
            label=kwargs["label"],
            user_id=kwargs["user_id"],
            idempotency_key=kwargs["idempotency_key"],
            dry_run=kwargs["dry_run"],
            success=True
        )
        self.db.add(log)
        await self.db.flush()

        return {
            "success": True,
            "video_id": kwargs["video_id"],
            "from_split": kwargs["from_split"],
            "to_split": kwargs["to_split"],
            "label": kwargs["label"],
            "message": kwargs["message"]
        }

    async def _log_and_return_failure(self, **kwargs) -> dict:
        """Log failed promotion and return result."""
        log = PromotionLog(
            video_id=kwargs["video_id"],
            from_split=kwargs["from_split"],
            to_split=kwargs["to_split"],
            label=kwargs["label"],
            user_id=kwargs["user_id"],
            idempotency_key=kwargs["idempotency_key"],
            dry_run=kwargs["dry_run"],
            success=False,
            error_message=kwargs["message"]
        )
        self.db.add(log)
        await self.db.flush()

        return {
            "success": False,
            "video_id": kwargs["video_id"],
            "from_split": kwargs["from_split"],
            "to_split": kwargs["to_split"],
            "label": kwargs["label"],
            "message": kwargs["message"]
        }
```

---

## Lesson 6.5: The Promotion Router (30 minutes)

### Complete Router Example

**Source**: `apps/api/app/routers/promote.py` (lines 1-165)

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..deps import get_db
from ..schemas.promote import (
    PromoteRequest,
    PromoteResponse,
    VideoListResponse,
    VideoResponse
)
from ..services.promote_service import PromoteService
from ..repositories.video_repository import VideoRepository

router = APIRouter()

# Dependency providers
def get_promote_service(db: AsyncSession = Depends(get_db)) -> PromoteService:
    return PromoteService(db)

def get_video_repository(db: AsyncSession = Depends(get_db)) -> VideoRepository:
    return VideoRepository(db)


@router.post("/promote", response_model=PromoteResponse)
async def promote_video(
    request: PromoteRequest,
    service: PromoteService = Depends(get_promote_service)
):
    """
    Promote a video to a new split.

    - **video_id**: UUID of the video to promote
    - **dest_split**: Target split (temp, train, test, purged; dataset_all for legacy compatibility)
    - **label**: Emotion label (required for train; legacy compatibility for dataset_all)
    - **user_id**: User performing the action (optional)
    - **idempotency_key**: Key to prevent duplicate processing (optional)
    - **dry_run**: If true, validate without executing (default: false)
    """
    result = await service.promote(
        video_id=request.video_id,
        dest_split=request.dest_split.value,
        label=request.label.value if request.label else None,
        user_id=request.user_id,
        idempotency_key=request.idempotency_key,
        dry_run=request.dry_run
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return PromoteResponse(**result)


@router.get("/videos", response_model=VideoListResponse)
async def list_videos(
    split: str = Query("temp", description="Filter by split"),
    label: Optional[str] = Query(None, description="Filter by label"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Skip first N results"),
    repo: VideoRepository = Depends(get_video_repository)
):
    """List videos with optional filtering."""
    videos = await repo.list_by_split(split, limit=limit, offset=offset)
    total = await repo.count_by_split(split)

    return VideoListResponse(
        items=[VideoResponse.model_validate(v) for v in videos],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/videos/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    repo: VideoRepository = Depends(get_video_repository)
):
    """Get a video by ID."""
    video = await repo.get_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return VideoResponse.model_validate(video)


@router.get("/stats/distribution")
async def get_distribution(
    split: str = Query("train", description="Split to analyze"),
    repo: VideoRepository = Depends(get_video_repository)
):
    """Get class distribution for a split."""
    distribution = await repo.get_class_distribution(split)
    total = sum(distribution.values())
    return {
        "split": split,
        "distribution": distribution,
        "total": total,
        "percentages": {
            label: round(count / total * 100, 2) if total > 0 else 0
            for label, count in distribution.items()
        }
    }
```

---

## Lesson 6.6: Error Handling (30 minutes)

### HTTP Exception Handling

```python
from fastapi import HTTPException, status

# 404 Not Found
if not video:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Video not found"
    )

# 400 Bad Request
if not request.label and request.dest_split in ("train", "dataset_all"):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Label required for this split"
    )

# 409 Conflict
if existing_video:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Video with this hash already exists"
    )

# 500 Internal Server Error
try:
    await service.promote(...)
except Exception as e:
    logger.exception("Promotion failed")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Internal server error"
    )
```

### Global Exception Handler

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

app = FastAPI()

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database constraint violations."""
    return JSONResponse(
        status_code=409,
        content={
            "detail": "Database constraint violation",
            "type": "integrity_error"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": "server_error"
        }
    )
```

---

## Knowledge Check

1. What is the purpose of the `Depends()` function in FastAPI?

2. Why do we use `yield` instead of `return` in the `get_db()` dependency?

3. What is the difference between a Pydantic schema and a SQLAlchemy model?

4. Why should business logic be in a Service class instead of the Router?

5. What HTTP status code should you return when a resource is not found?

<details>
<summary>Click to see answers</summary>

1. `Depends()` declares dependencies that FastAPI automatically injects into endpoint functions. It enables dependency injection.

2. `yield` allows cleanup after the request. After `yield`, we can commit or rollback the transaction and close the session.

3. Pydantic schemas define API request/response structure and validation. SQLAlchemy models define database table structure. They serve different layers of the application.

4. Separation of concerns: Routers handle HTTP, Services handle business logic. This makes code reusable (same service from different routes) and testable (test service without HTTP).

5. HTTP 404 Not Found.

</details>

---

## Hands-On Exercise 6

### Task 1: Create a Simple API

Create a file `test_api.py`:

```python
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Setup
DATABASE_URL = "postgresql+asyncpg://reachy_app:password@localhost/reachy_local"
engine = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app = FastAPI()

# Schema
class VideoOut(BaseModel):
    video_id: str
    file_path: str
    split: str
    label: Optional[str]

    class Config:
        from_attributes = True

# Dependency
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except:
            await session.rollback()
            raise

# Import your Video model
from apps.api.app.db.models import Video

# Endpoints
@app.get("/videos/{video_id}", response_model=VideoOut)
async def get_video(video_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Video).where(Video.video_id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "Not found")
    return video

@app.get("/videos", response_model=list[VideoOut])
async def list_videos(split: str = "temp", db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Video).where(Video.split == split).limit(10)
    )
    return result.scalars().all()

# Run with: uvicorn test_api:app --reload
```

### Task 2: Test the API

```bash
# Start the server
uvicorn test_api:app --reload --port 8000

# In another terminal:

# List videos
curl http://localhost:8000/videos?split=temp

# Get specific video (use an actual video_id)
curl http://localhost:8000/videos/YOUR_VIDEO_ID

# Test 404
curl http://localhost:8000/videos/nonexistent-id
```

### Task 3: Add a Create Endpoint

Add to your API:

```python
class VideoCreate(BaseModel):
    file_path: str
    size_bytes: int

@app.post("/videos", response_model=VideoOut)
async def create_video(
    video: VideoCreate,
    db: AsyncSession = Depends(get_db)
):
    # Create video object
    new_video = Video(
        file_path=video.file_path,
        size_bytes=video.size_bytes,
        split="temp"
    )
    db.add(new_video)
    await db.flush()
    await db.refresh(new_video)
    return new_video
```

Test it:
```bash
curl -X POST http://localhost:8000/videos \
  -H "Content-Type: application/json" \
  -d '{"file_path": "videos/api_test/new.mp4", "size_bytes": 1024}'
```

---

## Summary

In this module, you learned:

- ✅ FastAPI project structure for database applications
- ✅ Dependency injection with `Depends()`
- ✅ Pydantic schemas for request/response validation
- ✅ The service layer pattern for business logic
- ✅ Error handling with HTTPException
- ✅ Building complete CRUD endpoints

**Next**: [Module 7: Migrations & DevOps](./07-MODULE-MIGRATIONS-DEVOPS.md)
