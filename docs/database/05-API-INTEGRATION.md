# API Integration with Database

This document describes how the FastAPI applications interact with the PostgreSQL database.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          API LAYER                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐         ┌──────────────────┐                 │
│  │ Gateway API      │         │ Media Mover API  │                 │
│  │ (Ubuntu 2)       │────────▶│ (Ubuntu 1)       │                 │
│  │ Port 8080        │ proxy   │ Port 8081        │                 │
│  └──────────────────┘         └──────────────────┘                 │
│          │                            │                             │
│          │ validates                  │ connects                    │
│          ▼                            ▼                             │
│  ┌──────────────────┐         ┌──────────────────┐                 │
│  │ JSON Schema      │         │ PostgreSQL       │                 │
│  │ Validation       │         │ (localhost:5432) │                 │
│  └──────────────────┘         └──────────────────┘                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## File Locations

| Component | Path | Description |
|-----------|------|-------------|
| Main App | `apps/api/app/main.py` | FastAPI application factory |
| Settings | `apps/api/app/settings.py` | Database URL configuration |
| Dependencies | `apps/api/app/deps.py` | Dependency injection |
| Promote Router | `apps/api/app/routers/promote.py` | Promotion endpoints |
| Promote Service | `apps/api/app/services/promote_service.py` | Business logic |
| Video Repository | `apps/api/app/repositories/video_repository.py` | Database operations |
| Gateway Router | `apps/api/routers/gateway.py` | API gateway (Ubuntu 2) |

---

## Configuration

### Database URL

**Source**: `apps/api/app/settings.py:31-35`

```python
@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "MEDIA_MOVER_DATABASE_URL",
            "postgresql+psycopg2://reachy_app:reachy_app@localhost:5432/reachy_local",
        )
    )
```

**Environment Variable**: `MEDIA_MOVER_DATABASE_URL`

**Connection String Format**:
```
postgresql+asyncpg://username:password@host:port/database

Examples:
postgresql+asyncpg://reachy_app:secret@localhost:5432/reachy_local
postgresql+asyncpg://reachy_app:secret@10.0.4.130:5432/reachy_emotion
```

---

## Dependency Injection

**Source**: `apps/api/app/deps.py`

The application uses FastAPI's dependency injection to provide database sessions:

```python
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db(
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session tied to the application engine."""
    session_factory = get_async_sessionmaker(settings.database_url)
    async with session_factory() as session:
        yield session
```

Services are assembled with all their dependencies:

```python
def get_promote_service(
    session: AsyncSession = Depends(get_db),
    file_mover: FileMover = Depends(get_file_mover),
    manifest_backend: ManifestBackend = Depends(get_manifest_backend),
) -> PromoteService:
    """Assemble a PromoteService with shared infrastructure dependencies."""
    return PromoteService(
        session,
        file_mover=file_mover,
        manifest_backend=manifest_backend,
    )
```

---

## API Endpoints

### Media Mover API (Ubuntu 1, Port 8081)

The Media Mover API handles direct database operations.

#### POST /promote/stage

**Purpose**: Stage videos from `temp` to `dataset_all` with a label.

**Source**: `apps/api/app/routers/promote.py:41-86`

```python
@router.post("/stage", status_code=status.HTTP_202_ACCEPTED)
async def stage_videos(
    payload: StageRequest,
    service: PromoteService = Depends(get_promote_service),
):
    """Stage clips from temp into dataset_all."""
    result = await service.stage_to_dataset_all(
        [str(video_id) for video_id in payload.video_ids],
        label=payload.label,
        dry_run=payload.dry_run,
    )
    if not payload.dry_run:
        await service.commit()
    return StageResponse.from_result(status="accepted", result=result)
```

**Request Schema** (`apps/api/app/schemas/promote.py:24-43`):
```json
{
    "video_ids": ["uuid-1", "uuid-2"],
    "label": "happy",
    "dry_run": false
}
```

**Response Schema**:
```json
{
    "status": "accepted",
    "promoted_ids": ["uuid-1", "uuid-2"],
    "skipped_ids": [],
    "failed_ids": [],
    "dry_run": false
}
```

**Database Operations**:
1. Queries `video` table to find requested videos
2. Validates videos are in `temp` split
3. Updates `video.split` and `video.label`
4. Inserts records into `promotion_log`

#### POST /promote/sample

**Purpose**: Sample videos from `dataset_all` into train/test splits.

**Source**: `apps/api/app/routers/promote.py:111-159`

```python
@router.post("/sample", status_code=status.HTTP_202_ACCEPTED)
async def sample_split(
    payload: SampleRequest,
    service: PromoteService = Depends(get_promote_service),
):
    """Sample clips from dataset_all into train/test splits."""
    result = await service.sample_split(
        run_id=str(payload.run_id),
        target_split=payload.target_split,
        sample_fraction=float(payload.sample_fraction),
        strategy=payload.strategy,
        seed=payload.seed,
        dry_run=payload.dry_run,
    )
    return SampleResponse.from_result(status="accepted", result=result)
```

**Request Schema**:
```json
{
    "run_id": "uuid-of-training-run",
    "target_split": "train",
    "sample_fraction": 0.7,
    "strategy": "balanced_random",
    "seed": 42,
    "dry_run": false
}
```

**Database Operations**:
1. Creates or updates `training_run` record
2. Queries `video` table for `dataset_all` candidates
3. Applies balanced random sampling
4. Updates `video.split` for selected videos
5. Creates `training_selection` records
6. Creates `promotion_log` entries

#### POST /promote/reset-manifest

**Purpose**: Reset manifest state for training orchestrators.

**Source**: `apps/api/app/routers/promote.py:89-108`

---

### Gateway API (Ubuntu 2, Port 8080)

The Gateway API proxies requests and handles validation.

**Source**: `apps/api/routers/gateway.py`

#### POST /api/events/emotion

**Purpose**: Receive real-time emotion events from Jetson devices.

```python
@router.post("/api/events/emotion")
async def post_emotion_event(
    request: Request,
    x_api_version: str | None = Header(default=None, alias="X-API-Version"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    """Process emotion detection events."""
    body = await request.json()
    # Validates against JSON schema
    errors = sorted(emotion_validator.iter_errors(body), key=lambda e: e.path)
    if errors:
        return JSONResponse(status_code=400, content=error_payload(...))

    # Currently just logs - would insert into emotion_event table
    logger.info("emotion_event_received", extra={...})
    return Response(status_code=202)
```

**Request Schema**:
```json
{
    "schema_version": "v1",
    "device_id": "jetson-001",
    "ts": "2025-01-05T14:30:00Z",
    "emotion": "happy",
    "confidence": 0.95,
    "inference_ms": 45.3,
    "window": {"fps": 30, "size_s": 1.0, "hop_s": 0.5},
    "meta": {},
    "correlation_id": "uuid"
}
```

**Note**: This endpoint currently only logs events. The `emotion_event` table insert is not yet implemented.

#### Proxy Endpoints

The Gateway proxies several endpoints to the Media Mover:

```python
MEDIA_MOVER_URL = "http://10.0.4.130:8081"

@router.get("/api/videos/{video_id}")
async def get_video(video_id: str):
    url = f"{MEDIA_MOVER_URL}/api/videos/{video_id}"
    response = await client.get(url)
    return JSONResponse(content=response.json(), status_code=response.status_code)

@router.post("/api/promote")
async def post_promotion(request: Request):
    # Proxy to Media Mover with idempotency key
    ...

@router.post("/api/relabel")
async def relabel_video(request: Request):
    # Proxy to Media Mover
    ...
```

---

## Service Layer

### PromoteService

**Source**: `apps/api/app/services/promote_service.py`

The `PromoteService` orchestrates database and filesystem operations:

```python
class PromoteService:
    """Core promotion orchestration between filesystem and database."""

    def __init__(
        self,
        session: AsyncSession,
        repository: VideoRepository | None = None,
        file_mover: FileMover | None = None,
        ...
    ):
        self._session = session
        self._repository = repository or VideoRepository(session)
        ...

    async def stage_to_dataset_all(
        self,
        video_ids: Iterable[str],
        label: str | None,
        dry_run: bool = False,
    ) -> StageResult:
        """Validate and move labelled clips from temp to dataset_all."""

        # 1. Fetch videos from database
        records = await self._repository.fetch_videos_for_stage(parsed_ids)

        # 2. Validate business rules
        for record in records:
            if record.split != "temp":
                skipped_ids.append(record.video_id)
                continue
            # Build mutations list

        # 3. Move files on filesystem
        for mutation in mutations:
            transition = self._file_mover.stage_to_dataset_all(...)

        # 4. Persist to database
        await self._repository.persist_stage_results(mutations)

        return StageResult(...)
```

**Key Methods**:
| Method | Purpose | Database Tables |
|--------|---------|-----------------|
| `stage_to_dataset_all()` | Promote temp → dataset_all | video, promotion_log |
| `sample_split()` | Sample dataset_all → train/test | video, training_run, training_selection, promotion_log |
| `commit()` | Commit transaction | - |
| `rollback()` | Rollback on error | - |

---

## Repository Layer

### VideoRepository

**Source**: `apps/api/app/repositories/video_repository.py`

```python
class VideoRepository:
    """Async persistence helpers for promotion operations."""

    async def fetch_videos_for_stage(
        self, video_ids: Sequence[uuid.UUID]
    ) -> list[VideoRecord]:
        """Return video metadata for ids targeted for staging."""
        stmt = sa.select(models.Video).where(models.Video.video_id.in_(video_ids))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_record(row) for row in rows]

    async def fetch_dataset_all_for_sampling(
        self, exclude_ids: Collection[uuid.UUID] | None = None
    ) -> list[VideoRecord]:
        """Return candidates from dataset_all."""
        stmt = sa.select(models.Video).where(models.Video.split == "dataset_all")
        if exclude_ids:
            stmt = stmt.where(sa.not_(models.Video.video_id.in_(exclude_ids)))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_record(row) for row in rows]

    async def persist_stage_results(
        self, mutations: Sequence[StageMutation]
    ) -> None:
        """Apply split/label updates and log promotions."""
        for mutation in mutations:
            await self._session.execute(
                sa.update(models.Video)
                .where(models.Video.video_id == mutation.video_id)
                .values(split=mutation.to_split, label=mutation.intended_label)
            )
            logs.append(models.PromotionLog(...))
        self._session.add_all(logs)
        await self._session.flush()
```

---

## Request Flow Diagram

```
┌───────────────────────────────────────────────────────────────────────┐
│                    POST /promote/stage Request Flow                    │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  1. HTTP Request                                                       │
│     │                                                                  │
│     ▼                                                                  │
│  ┌────────────────────┐                                               │
│  │ FastAPI Router     │  apps/api/app/routers/promote.py:46           │
│  │ stage_videos()     │                                               │
│  └────────────────────┘                                               │
│     │                                                                  │
│     │ Depends(get_promote_service)                                    │
│     ▼                                                                  │
│  ┌────────────────────┐                                               │
│  │ PromoteService     │  apps/api/app/services/promote_service.py     │
│  │ stage_to_dataset   │                                               │
│  │ _all()             │                                               │
│  └────────────────────┘                                               │
│     │                                                                  │
│     │ self._repository.fetch_videos_for_stage()                       │
│     ▼                                                                  │
│  ┌────────────────────┐                                               │
│  │ VideoRepository    │  apps/api/app/repositories/video_repository   │
│  │ fetch_videos_      │                                               │
│  │ for_stage()        │                                               │
│  └────────────────────┘                                               │
│     │                                                                  │
│     │ SELECT FROM video WHERE video_id IN (...)                       │
│     ▼                                                                  │
│  ┌────────────────────┐                                               │
│  │ PostgreSQL         │                                               │
│  │ video table        │                                               │
│  └────────────────────┘                                               │
│     │                                                                  │
│     │ results                                                          │
│     ▼                                                                  │
│  ┌────────────────────┐                                               │
│  │ VideoRepository    │                                               │
│  │ persist_stage_     │  UPDATE video SET split=..., label=...        │
│  │ results()          │  INSERT INTO promotion_log (...)              │
│  └────────────────────┘                                               │
│     │                                                                  │
│     │ await session.commit()                                          │
│     ▼                                                                  │
│  ┌────────────────────┐                                               │
│  │ HTTP Response      │  {"status": "accepted", "promoted_ids": [...]}│
│  └────────────────────┘                                               │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Error Handling

The API uses custom exception classes:

```python
# apps/api/app/services/promote_service.py:29-38
class PromotionError(RuntimeError):
    """Raised when promotion or sampling cannot be completed."""

class PromotionValidationError(PromotionError):
    """Raised when user-provided inputs fail validation."""

class PromotionConflictError(PromotionError):
    """Raised when the requested operation violates current state."""
```

Router maps exceptions to HTTP status codes:

```python
# apps/api/app/routers/promote.py
except PromotionValidationError as exc:
    await service.rollback()
    raise HTTPException(status_code=422, detail=str(exc))

except PromotionConflictError as exc:
    await service.rollback()
    raise HTTPException(status_code=409, detail=str(exc))
```

---

## Prometheus Metrics

**Source**: `apps/api/app/services/promote_service.py:21-25`

```python
from ..metrics import (
    PROMOTION_FILESYSTEM_FAILURES,
    PROMOTION_OPERATION_COUNTER,
    PROMOTION_OPERATION_DURATION,
)
```

The service tracks:
- Operation counts by action and outcome
- Operation duration histograms
- Filesystem failure counts

Metrics endpoint: `GET /metrics`

---

## Correlation IDs

All requests support correlation IDs for tracing:

```python
# apps/api/app/routers/promote.py:27-34
CORRELATION_ID_HEADER = "X-Correlation-ID"

def _resolve_correlation_id(request: Request) -> str:
    header_value = request.headers.get(CORRELATION_ID_HEADER)
    if header_value:
        return header_value.strip()
    return str(uuid4())
```

The correlation ID is:
1. Read from request header (if present)
2. Generated automatically (if not present)
3. Passed to service for logging
4. Returned in response header

---

## Testing

### Unit Tests

**Source**: `tests/apps/api/services/test_promote_service.py`

```python
@pytest.mark.asyncio
async def test_stage_to_dataset_all():
    # Mock dependencies
    mock_session = AsyncMock()
    mock_repository = Mock()
    mock_repository.fetch_videos_for_stage = AsyncMock(return_value=[...])

    service = PromoteService(mock_session, repository=mock_repository)
    result = await service.stage_to_dataset_all(["video-1"], label="happy")

    assert len(result.promoted_ids) == 1
```

### Integration Tests

**Source**: `tests/apps/api/e2e/test_promote_end_to_end.py`

```python
@pytest.mark.asyncio
async def test_promote_end_to_end(test_client, test_db):
    # Insert test video
    await test_db.execute(...)

    # Call API
    response = await test_client.post("/promote/stage", json={
        "video_ids": ["test-video-id"],
        "label": "happy"
    })

    assert response.status_code == 202
    # Verify database state
    ...
```

---

## Next Steps

- See [06-MIGRATIONS.md](06-MIGRATIONS.md) for schema migration process
- See [07-KNOWN-ISSUES.md](07-KNOWN-ISSUES.md) for API-related issues
- See [08-SETUP-GUIDE.md](08-SETUP-GUIDE.md) for running the API locally
