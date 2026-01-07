# Python ORM Models Reference

This document describes the SQLAlchemy ORM models that provide Python access to the database.

## What is an ORM?

**ORM** (Object-Relational Mapping) lets you work with database rows as Python objects:

```python
# Without ORM (raw SQL)
cursor.execute("SELECT video_id, file_path, label FROM video WHERE split = 'train'")
rows = cursor.fetchall()
for row in rows:
    print(row[1])  # Access by index - error-prone

# With ORM (SQLAlchemy)
videos = session.execute(select(Video).where(Video.split == "train")).scalars().all()
for video in videos:
    print(video.file_path)  # Access by attribute - type-safe
```

## File Locations

| File | Path | Purpose |
|------|------|---------|
| Models | `apps/api/app/db/models.py` | Table definitions as Python classes |
| Enums | `apps/api/app/db/enums.py` | Enum type definitions |
| Session | `apps/api/app/db/session.py` | Database connection management |
| Base | `apps/api/app/db/base.py` | SQLAlchemy base class |

## Enum Definitions

**Source**: `apps/api/app/db/enums.py`

```python
from sqlalchemy import Enum

# Split lifecycle stages
VIDEO_SPLIT_ENUM_NAME = "video_split_enum"
SplitEnum = Enum(
    "temp",
    "dataset_all",
    "train",
    "test",
    "purged",
    name=VIDEO_SPLIT_ENUM_NAME,
)

# Emotion labels
EMOTION_ENUM_NAME = "emotion_enum"
EmotionEnum = Enum(
    "neutral",
    "happy",
    "sad",
    "angry",
    "surprise",
    # NOTE: 'fearful' is MISSING here but exists in SQL schema!
    name=EMOTION_ENUM_NAME,
)

# Training selection targets
SELECTION_TARGET_ENUM_NAME = "training_selection_target_enum"
SelectionTargetEnum = Enum(
    "train",
    "test",
    name=SELECTION_TARGET_ENUM_NAME,
)
```

**Important**: The Python enums use `native_enum=False`, which means SQLAlchemy creates CHECK constraints instead of PostgreSQL ENUM types. This provides better compatibility with SQLite for testing.

---

## Model Classes

### Video

**Source**: `apps/api/app/db/models.py:40-90`

```python
class Video(Base):
    """Video metadata model."""

    __tablename__ = "video"

    video_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    split: Mapped[str] = mapped_column(
        SplitEnum, nullable=False, default="temp"
    )
    label: Mapped[str | None] = mapped_column(EmotionEnum, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_sec: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fps: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    promotions: Mapped[list["PromotionLog"]] = relationship(back_populates="video")
    selections: Mapped[list["TrainingSelection"]] = relationship(back_populates="video")

    __table_args__ = (
        CheckConstraint(
            """
            (split IN ('temp', 'test', 'purged') AND label IS NULL)
            OR
            (split IN ('dataset_all', 'train') AND label IS NOT NULL)
            """,
            name="chk_video_split_label_policy",
        ),
        Index("idx_video_split", "split"),
        Index("idx_video_label", "label"),
        Index("idx_video_created", created_at.desc()),
    )
```

**Usage**:
```python
from apps.api.app.db.models import Video

# Create a new video
video = Video(
    file_path="videos/temp/new_clip.mp4",
    split="temp",
    size_bytes=1024000,
    sha256="a" * 64,
)
session.add(video)
await session.commit()

# Query videos
from sqlalchemy import select

stmt = select(Video).where(Video.split == "dataset_all")
videos = (await session.execute(stmt)).scalars().all()

for v in videos:
    print(f"{v.video_id}: {v.file_path} - {v.label}")
```

---

### TrainingRun

**Source**: `apps/api/app/db/models.py:93-130`

```python
class TrainingRun(Base):
    """Training run metadata model."""

    __tablename__ = "training_run"

    run_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    strategy: Mapped[str] = mapped_column(String(100), nullable=False)
    train_fraction: Mapped[float] = mapped_column(
        Numeric(3, 2), nullable=False, default=0.7
    )
    test_fraction: Mapped[float] = mapped_column(
        Numeric(3, 2), nullable=False, default=0.3
    )
    seed: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    selections: Mapped[list["TrainingSelection"]] = relationship(back_populates="run")

    __table_args__ = (
        CheckConstraint("train_fraction >= 0 AND train_fraction <= 1", name="chk_train_fraction"),
        CheckConstraint("test_fraction >= 0 AND test_fraction <= 1", name="chk_test_fraction"),
        CheckConstraint("train_fraction + test_fraction <= 1.0", name="chk_total_fraction"),
    )
```

**Note**: This model is INCOMPLETE compared to the SQL schema. Missing columns:
- `dataset_hash`, `mlflow_run_id`, `model_path`, `engine_path`
- `metrics`, `config`, `error_message`
- `started_at`, `completed_at`

See [07-KNOWN-ISSUES.md](07-KNOWN-ISSUES.md) for details.

**Usage**:
```python
from apps.api.app.db.models import TrainingRun

# Create a training run
run = TrainingRun(
    strategy="balanced_random",
    train_fraction=0.7,
    test_fraction=0.3,
    seed=42,
)
session.add(run)
await session.commit()

print(f"Created run: {run.run_id}")
```

---

### TrainingSelection

**Source**: `apps/api/app/db/models.py:133-165`

```python
class TrainingSelection(Base):
    """Links videos to training runs."""

    __tablename__ = "training_selection"

    # Composite primary key
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("training_run.run_id"), primary_key=True
    )
    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("video.video_id"), primary_key=True
    )
    target_split: Mapped[str] = mapped_column(
        SelectionTargetEnum, primary_key=True
    )

    # Relationships
    run: Mapped["TrainingRun"] = relationship(back_populates="selections")
    video: Mapped["Video"] = relationship(back_populates="selections")
```

**Note**: The SQL schema uses `BIGSERIAL id` as primary key, but the Python model uses a composite key. This is a schema mismatch.

**Usage**:
```python
from apps.api.app.db.models import TrainingSelection

# Add a video to a training run
selection = TrainingSelection(
    run_id=run.run_id,
    video_id=video.video_id,
    target_split="train",
)
session.add(selection)
await session.commit()
```

---

### PromotionLog

**Source**: `apps/api/app/db/models.py:168-200`

```python
class PromotionLog(Base):
    """Audit log for video promotions."""

    __tablename__ = "promotion_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("video.video_id"), nullable=False
    )
    from_split: Mapped[str] = mapped_column(SplitEnum, nullable=False)
    to_split: Mapped[str] = mapped_column(SplitEnum, nullable=False)
    intended_label: Mapped[str | None] = mapped_column(EmotionEnum, nullable=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    promoted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationship
    video: Mapped["Video"] = relationship(back_populates="promotions")
```

**Note**: Missing columns compared to SQL: `correlation_id`, `idempotency_key`, `dry_run`

**Usage**:
```python
# Usually created by VideoRepository, not directly
log = PromotionLog(
    video_id=video.video_id,
    from_split="temp",
    to_split="dataset_all",
    intended_label="happy",
    actor="alice@example.com",
    success=True,
)
session.add(log)
```

---

### Additional Models

The following models are defined in `models.py` for Phase 3 agent support:

#### LabelEvent
```python
class LabelEvent(Base):
    """Labeling action audit."""
    __tablename__ = "label_event"
    # ... similar structure to PromotionLog
```

#### DeploymentLog
```python
class DeploymentLog(Base):
    """Model deployment tracking."""
    __tablename__ = "deployment_log"
    # ... tracks engine deployments to Jetson
```

#### AuditLog
```python
class AuditLog(Base):
    """Privacy/GDPR audit."""
    __tablename__ = "audit_log"
    # ... tracks data access/deletion
```

#### ObsSample
```python
class ObsSample(Base):
    """Observability metrics."""
    __tablename__ = "obs_samples"
    # ... time-series metrics
```

#### ReconcileReport
```python
class ReconcileReport(Base):
    """Filesystem consistency."""
    __tablename__ = "reconcile_report"
    # ... tracks orphan files, missing records
```

---

## Missing Models

The following tables exist in SQL but have NO corresponding Python models:

| SQL Table | Status | Impact |
|-----------|--------|--------|
| `user_session` | Missing | Cannot query user sessions via ORM |
| `generation_request` | Missing | Cannot track synthetic video generation |
| `emotion_event` | Missing | Cannot query real-time detections |

To work with these tables, you must use raw SQL:
```python
from sqlalchemy import text

result = await session.execute(
    text("SELECT * FROM user_session WHERE user_id = :uid"),
    {"uid": "alice@example.com"}
)
sessions = result.fetchall()
```

---

## Database Session Management

**Source**: `apps/api/app/db/session.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

def get_async_engine(url: str):
    """Create async SQLAlchemy engine."""
    return create_async_engine(url, echo=False)

def get_async_sessionmaker(url: str) -> async_sessionmaker[AsyncSession]:
    """Create async session factory."""
    engine = get_async_engine(url)
    return async_sessionmaker(engine, expire_on_commit=False)
```

**Usage in FastAPI**:
```python
# apps/api/app/deps.py
async def get_db(settings: Settings = Depends(get_settings)) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session."""
    session_factory = get_async_sessionmaker(settings.database_url)
    async with session_factory() as session:
        yield session

# In a router
@router.post("/videos")
async def create_video(
    payload: VideoCreate,
    session: AsyncSession = Depends(get_db)
):
    video = Video(**payload.dict())
    session.add(video)
    await session.commit()
    return {"video_id": video.video_id}
```

---

## Repository Pattern

The codebase uses the Repository pattern to encapsulate database operations.

**Source**: `apps/api/app/repositories/video_repository.py`

```python
class VideoRepository:
    """Async persistence helpers for promotion operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def fetch_videos_for_stage(
        self, video_ids: Sequence[uuid.UUID]
    ) -> list[VideoRecord]:
        """Return video metadata for staging candidates."""
        stmt = select(models.Video).where(models.Video.video_id.in_(video_ids))
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
                .values(
                    split=mutation.to_split,
                    label=mutation.intended_label,
                    file_path=mutation.new_file_path,
                )
            )
            # ... create PromotionLog entries
        await self._session.flush()
```

**Benefits**:
- Separates database logic from business logic
- Easier to test (mock the repository)
- Consistent patterns across codebase

---

## Common Query Patterns

### Get All Videos in a Split
```python
stmt = select(Video).where(Video.split == "dataset_all")
videos = (await session.execute(stmt)).scalars().all()
```

### Count by Label
```python
from sqlalchemy import func

stmt = (
    select(Video.label, func.count(Video.video_id).label("count"))
    .where(Video.split == "dataset_all")
    .group_by(Video.label)
)
results = (await session.execute(stmt)).all()
for label, count in results:
    print(f"{label}: {count}")
```

### Update a Video
```python
stmt = (
    update(Video)
    .where(Video.video_id == target_id)
    .values(split="dataset_all", label="happy")
)
await session.execute(stmt)
await session.commit()
```

### Join Videos with Selections
```python
stmt = (
    select(Video, TrainingSelection)
    .join(TrainingSelection, Video.video_id == TrainingSelection.video_id)
    .where(TrainingSelection.run_id == run_id)
)
results = (await session.execute(stmt)).all()
for video, selection in results:
    print(f"{video.file_path} -> {selection.target_split}")
```

---

## Testing with SQLite

The test suite uses SQLite instead of PostgreSQL for speed:

```python
# tests/apps/api/db/test_models_async_roundtrip.py
@pytest.mark.asyncio
async def test_async_roundtrip(tmp_path: Path) -> None:
    db_path = tmp_path / "async.db"
    async_url = f"sqlite+aiosqlite:///{db_path}"
    sessionmaker = get_async_sessionmaker(async_url)

    async with sessionmaker() as session:
        video = Video(
            file_path="dataset_all/clip.mp4",
            split="dataset_all",
            label="angry",
            size_bytes=8192,
            sha256="e" * 64,
        )
        session.add(video)
        await session.commit()
```

This works because:
1. `native_enum=False` uses CHECK constraints instead of PostgreSQL ENUMs
2. SQLAlchemy abstracts database differences

---

## Next Steps

- See [05-API-INTEGRATION.md](05-API-INTEGRATION.md) for how APIs use these models
- See [07-KNOWN-ISSUES.md](07-KNOWN-ISSUES.md) for model-schema mismatches
