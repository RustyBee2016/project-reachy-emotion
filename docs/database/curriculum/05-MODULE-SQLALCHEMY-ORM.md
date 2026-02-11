# Module 5: Python ORM with SQLAlchemy

**Duration**: 4 hours
**Prerequisites**: Modules 1-4, Basic Python knowledge
**Goal**: Use SQLAlchemy to interact with the database from Python

---

## Learning Objectives

By the end of this module, you will be able to:
1. Explain what an ORM is and its benefits
2. Define SQLAlchemy models that map to database tables
3. Perform CRUD operations using the ORM
4. Write async database code for FastAPI
5. Use the repository pattern for data access

---

## Lesson 5.1: What is an ORM? (30 minutes)

### The Problem Without an ORM

```python
# Raw SQL approach - error-prone, verbose
import psycopg2

conn = psycopg2.connect("postgresql://user:pass@localhost/db")
cursor = conn.cursor()

# Insert - manual SQL string construction
cursor.execute("""
    INSERT INTO video (file_path, split, size_bytes)
    VALUES (%s, %s, %s)
""", ('videos/001.mp4', 'temp', 1024000))

# Query - returns tuples, must remember column order
cursor.execute("SELECT video_id, file_path, label FROM video WHERE split = 'train'")
rows = cursor.fetchall()
for row in rows:
    print(row[1])  # What's at index 1? Hard to remember!

conn.commit()
conn.close()
```

### The ORM Solution

**ORM** = Object-Relational Mapping

It maps database tables to Python classes:

```python
# With SQLAlchemy ORM - clean, type-safe
from sqlalchemy import select
from models import Video

async with session.begin():
    # Insert - using Python objects
    video = Video(
        file_path='videos/001.mp4',
        split='temp',
        size_bytes=1024000
    )
    session.add(video)

    # Query - returns objects with attributes
    result = await session.execute(
        select(Video).where(Video.split == 'train')
    )
    videos = result.scalars().all()
    for video in videos:
        print(video.file_path)  # Clear attribute access!
```

### ORM Benefits

| Benefit | Explanation |
|---------|-------------|
| **Type Safety** | IDE can autocomplete and check types |
| **Readability** | `video.file_path` vs `row[1]` |
| **SQL Injection Prevention** | Parameterized queries automatic |
| **Database Abstraction** | Same code works with PostgreSQL, SQLite, etc. |
| **Relationships** | Navigate between related objects naturally |

### SQLAlchemy 2.0

Reachy uses **SQLAlchemy 2.0** with the new syntax:
- `Mapped[]` type hints
- `mapped_column()` function
- Async support via `asyncpg`

**Source Files:**
- `apps/api/app/db/models.py` - Model definitions
- `apps/api/app/db/enums.py` - Enum definitions
- `apps/api/app/db/base.py` - Base class
- `apps/api/app/db/session.py` - Session factory

---

## Lesson 5.2: Defining Models (45 minutes)

### The Base Class and TimestampMixin

**Source**: `apps/api/app/db/base.py`

```python
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime

class Base(DeclarativeBase):
    """Declarative base for Media Mover models."""

class TimestampMixin:
    """Adds created/updated timestamp columns with server defaults."""

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

All models inherit from `Base`. Models that need timestamps also inherit from `TimestampMixin`
(e.g., `class Video(TimestampMixin, Base)`). The mixin uses `server_default=func.now()` so
PostgreSQL generates the timestamps, not Python.

### Defining Enums

**Source**: `apps/api/app/db/enums.py` (lines 1-44)

```python
from sqlalchemy import Enum

# Enum type names in PostgreSQL
VIDEO_SPLIT_ENUM_NAME = "video_split_enum"
EMOTION_ENUM_NAME = "emotion_enum"

# Define SQLAlchemy enums
SplitEnum = Enum(
    "temp",
    "dataset_all",
    "train",
    "test",
    "purged",
    name=VIDEO_SPLIT_ENUM_NAME,
    native_enum=False  # Uses CHECK constraint instead of native PostgreSQL ENUM
)

EmotionEnum = Enum(
    "neutral",
    "happy",
    "sad",
    "angry",
    "surprise",
    "fearful",
    name=EMOTION_ENUM_NAME,
    create_constraint=True,
    native_enum=False,
    validate_strings=True,
)
```

> ✅ **Resolved**: Issue #1 (Missing 'fearful') has been fixed. `enums.py` now includes all 6 values.
> See `docs/database/07-KNOWN-ISSUES.md` for the full resolution history.

**Why `native_enum=False`?**
- Creates CHECK constraints instead of PostgreSQL ENUM types
- Works with SQLite (used for testing)
- Easier to add/remove values

### The Video Model

**Source**: `apps/api/app/db/models.py` (lines 34-85)

```python
from sqlalchemy import (
    String, BigInteger, Float, JSON, DateTime,
    CheckConstraint, UniqueConstraint, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, List
import uuid

from .base import Base, TimestampMixin
from .enums import SplitEnum, EmotionEnum

class Video(TimestampMixin, Base):
    __tablename__ = "video"

    # Primary Key — String(36) for cross-DB compatibility (SQLite in tests)
    video_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Required fields
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    split: Mapped[str] = mapped_column(SplitEnum, nullable=False, default="temp")
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    # Optional fields
    label: Mapped[Optional[str]] = mapped_column(EmotionEnum, nullable=True)
    duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(nullable=True)
    height: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Flexible metadata (mapped to column name "metadata" in DB)
    extra_data: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSON, default=dict, nullable=True
    )

    # Soft delete support (GDPR compliance)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    promotions: Mapped[List["PromotionLog"]] = relationship(
        back_populates="video", cascade="all, delete-orphan",
    )
    selections: Mapped[List["TrainingSelection"]] = relationship(
        back_populates="video", cascade="all, delete-orphan",
    )
    label_events: Mapped[List["LabelEvent"]] = relationship(
        back_populates="video", cascade="all, delete-orphan",
    )

    # Timestamps inherited from TimestampMixin: created_at, updated_at

    # Table-level constraints
    __table_args__ = (
        UniqueConstraint("sha256", "size_bytes", name="uq_video_sha256_size"),
        CheckConstraint(
            """
            (
                split IN ('temp', 'test', 'purged') AND label IS NULL
            ) OR (
                split IN ('dataset_all', 'train') AND label IS NOT NULL
            )
            """,
            name="chk_video_split_label_policy",
        ),
        Index("ix_video_split", "split"),
        Index("ix_video_label", "label"),
    )
```

> ✅ **Resolved**: Issue #6 (Video Model Missing Columns) has been fixed. The model now
> includes `extra_data` (mapped to `metadata` column) and `deleted_at` for soft deletes.
> See `docs/database/07-KNOWN-ISSUES.md` for the full resolution history.

---

### Breaking Down the Model

```python
# Type hint with Mapped[]
video_id: Mapped[str] = mapped_column(...)
#         ↑             ↑
#   Python type    Column definition

# Optional fields use Optional[]
label: Mapped[Optional[str]] = mapped_column(..., nullable=True)
#             ↑
#     Can be None in Python, NULL in DB

# Default values
split: Mapped[str] = mapped_column(..., default="temp")
created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
#                                                    ↑
#                                         Function called on insert

# Auto-update on modification
updated_at: Mapped[datetime] = mapped_column(
    default=datetime.utcnow,
    onupdate=datetime.utcnow  # Called on UPDATE
)
```

### The TrainingRun Model

**Source**: `apps/api/app/db/models.py` (lines 88-136)

```python
class TrainingRun(TimestampMixin, Base):
    __tablename__ = "training_run"

    run_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    strategy: Mapped[str] = mapped_column(String(100), nullable=False)
    train_fraction: Mapped[float] = mapped_column(Float, nullable=False)
    test_fraction: Mapped[float] = mapped_column(Float, nullable=False)
    seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    dataset_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    mlflow_run_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    engine_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    selections: Mapped[List["TrainingSelection"]] = relationship(
        back_populates="training_run", cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "train_fraction + test_fraction <= 1.0",
            name="chk_training_run_fractions",
        ),
    )
```

> ✅ **Resolved**: Issue #7 (TrainingRun Model Incomplete) has been fixed. The model now
> includes all 15+ columns: `dataset_hash`, `mlflow_run_id`, `model_path`, `engine_path`,
> `metrics`, `config`, `error_message`, `started_at`, `completed_at`, etc.

---

### Legacy-Only Tables (Not in ORM)

Three tables from the original SQL schema do **not** have ORM models:
`user_session`, `generation_request`, `emotion_event`.

This is an **intentional architectural decision** — these tables supported features that
are not yet implemented in the current app runtime. They exist only in the legacy SQL path
(`001_phase1_schema.sql`). If needed in the future, they should be added to `models.py`
and a new Alembic migration generated.

> ✅ **Resolved (by design)**: Issue #5 (Missing SQLAlchemy Models) — the 9 tables in
> `models.py` represent the complete operational schema.

---

### Additional Models in models.py

Beyond `Video` and `TrainingRun`, `models.py` also defines:

- **`TrainingSelection`** — Maps videos to training runs with a composite PK `(run_id, video_id, target_split)`
- **`PromotionLog`** — Audit trail for video promotions, includes `idempotency_key` and `correlation_id`
- **`LabelEvent`** — Tracks labeling actions (label, relabel, discard)
- **`DeploymentLog`** — Records model deployments to Jetson
- **`AuditLog`** — Privacy-sensitive operations (purge, access, export)
- **`ObsSample`** — Time-series observability metrics
- **`ReconcileReport`** — Filesystem/database consistency checks

> ✅ **Resolved**: Issue #10 (PromotionLog Missing Columns) — `idempotency_key` and
> `correlation_id` are now present in the `PromotionLog` model.

---

## Lesson 5.3: Database Sessions (30 minutes)

### What is a Session?

A **session** represents a conversation with the database:
- Tracks pending changes
- Manages transactions
- Provides a workspace for objects

```
┌─────────────────────────────────────────────────────────────────────┐
│                      SESSION WORKFLOW                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Python                                   Database                  │
│   ┌────────────────┐                      ┌────────────────┐        │
│   │ Session        │                      │ PostgreSQL     │        │
│   │ ──────────────── │                      │                │        │
│   │ pending: [obj1]│                      │                │        │
│   │ dirty: [obj2]  │ ───── COMMIT ──────▶ │ INSERT obj1    │        │
│   │ deleted: [obj3]│                      │ UPDATE obj2    │        │
│   │                │                      │ DELETE obj3    │        │
│   └────────────────┘                      └────────────────┘        │
│                                                                      │
│   session.add(obj1)     → Marked as pending (new)                   │
│   obj2.label = 'happy'  → Marked as dirty (modified)                │
│   session.delete(obj3)  → Marked for deletion                       │
│   session.commit()      → Flush all to database                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Sync vs Async Sessions

**Synchronous** (blocking):
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

engine = create_engine("postgresql://user:pass@localhost/db")
with Session(engine) as session:
    session.add(video)
    session.commit()
```

**Asynchronous** (non-blocking, for FastAPI):
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
async with AsyncSession(engine) as session:
    session.add(video)
    await session.commit()
```

### The Session Factory

**Source**: `apps/api/app/db/session.py` (lines 1-38)

```python
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from contextlib import asynccontextmanager

def get_async_sessionmaker(database_url: str) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory."""
    engine = create_async_engine(
        database_url,
        echo=False,  # Set True to log SQL
        pool_pre_ping=True,  # Verify connections before use
    )

    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Keep objects usable after commit
    )

@asynccontextmanager
async def get_session(factory: async_sessionmaker[AsyncSession]):
    """Context manager for database sessions."""
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### Using Sessions in FastAPI

```python
# In your endpoint
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncSession:
    async with session_factory() as session:
        yield session

@router.get("/videos/{video_id}")
async def get_video(video_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Video).where(Video.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "Video not found")
    return video
```

---

## Lesson 5.4: CRUD Operations (45 minutes)

### Create (INSERT)

```python
from sqlalchemy.ext.asyncio import AsyncSession
from models import Video

async def create_video(db: AsyncSession, file_path: str, size_bytes: int) -> Video:
    video = Video(
        file_path=file_path,
        split="temp",
        size_bytes=size_bytes
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)  # Load auto-generated values
    return video

# Usage
video = await create_video(db, "videos/new.mp4", 1024000)
print(video.video_id)  # Auto-generated UUID
print(video.created_at)  # Auto-generated timestamp
```

### Read (SELECT)

```python
from sqlalchemy import select

# Get one by ID
async def get_video_by_id(db: AsyncSession, video_id: str) -> Video | None:
    result = await db.execute(
        select(Video).where(Video.video_id == video_id)
    )
    return result.scalar_one_or_none()

# Get all with filter
async def get_videos_by_split(db: AsyncSession, split: str) -> list[Video]:
    result = await db.execute(
        select(Video).where(Video.split == split)
    )
    return result.scalars().all()

# Get with multiple conditions
async def get_happy_training_videos(db: AsyncSession) -> list[Video]:
    result = await db.execute(
        select(Video)
        .where(Video.split == "train")
        .where(Video.label == "happy")
        .order_by(Video.created_at.desc())
        .limit(100)
    )
    return result.scalars().all()
```

### Update

```python
# Update single object
async def update_video_label(db: AsyncSession, video_id: str, label: str) -> Video:
    result = await db.execute(
        select(Video).where(Video.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    if video:
        video.label = label
        video.split = "dataset_all"
        await db.commit()
        await db.refresh(video)
    return video

# Bulk update
from sqlalchemy import update

async def promote_all_temp_videos(db: AsyncSession, label: str):
    await db.execute(
        update(Video)
        .where(Video.split == "temp")
        .values(split="dataset_all", label=label)
    )
    await db.commit()
```

### Delete

```python
from sqlalchemy import delete

# Delete single object
async def delete_video(db: AsyncSession, video_id: str):
    result = await db.execute(
        select(Video).where(Video.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    if video:
        await db.delete(video)
        await db.commit()

# Bulk delete
async def delete_old_temp_videos(db: AsyncSession, days: int):
    cutoff = datetime.utcnow() - timedelta(days=days)
    await db.execute(
        delete(Video)
        .where(Video.split == "temp")
        .where(Video.created_at < cutoff)
    )
    await db.commit()
```

### The Result Object

SQLAlchemy queries return `Result` objects with several methods:

```python
result = await db.execute(select(Video).where(...))

# Single row
video = result.scalar_one()          # Raises if not exactly 1
video = result.scalar_one_or_none()  # Returns None if 0, raises if >1
video = result.scalar()              # Returns first column of first row
video = result.first()               # Returns first row as tuple

# Multiple rows
videos = result.scalars().all()      # List of Video objects
videos = result.all()                # List of Row tuples

# Iteration
for video in result.scalars():
    print(video.file_path)
```

---

## Lesson 5.5: Relationships (30 minutes)

### Defining Relationships

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped

class TrainingSelection(Base):
    __tablename__ = "training_selection"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("training_run.run_id"))
    video_id: Mapped[str] = mapped_column(ForeignKey("video.video_id"))
    target_split: Mapped[str] = mapped_column(SplitEnum)

    # Relationships (not in current code - would need to add)
    run: Mapped["TrainingRun"] = relationship(back_populates="selections")
    video: Mapped["Video"] = relationship(back_populates="selections")


class TrainingRun(Base):
    __tablename__ = "training_run"
    # ... other columns ...

    # One-to-many relationship
    selections: Mapped[list["TrainingSelection"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan"
    )


class Video(Base):
    __tablename__ = "video"
    # ... other columns ...

    # Many-to-many through TrainingSelection
    selections: Mapped[list["TrainingSelection"]] = relationship(
        back_populates="video"
    )
```

### Using Relationships

```python
# Navigate from run to videos
run = await get_training_run(db, run_id)
for selection in run.selections:
    print(f"{selection.video.file_path} -> {selection.target_split}")

# Navigate from video to runs
video = await get_video(db, video_id)
for selection in video.selections:
    print(f"Used in run {selection.run.run_id}")
```

### Lazy Loading Pitfall (Async)

**Warning**: In async code, lazy loading doesn't work!

```python
# This FAILS in async
run = await db.execute(select(TrainingRun))
run = run.scalar_one()
for sel in run.selections:  # ERROR: Cannot load lazily in async
    ...

# Solution: Eager loading
from sqlalchemy.orm import selectinload

result = await db.execute(
    select(TrainingRun)
    .options(selectinload(TrainingRun.selections))
)
run = result.scalar_one()
for sel in run.selections:  # Works!
    ...
```

---

## Lesson 5.6: The Repository Pattern (45 minutes)

### What is the Repository Pattern?

A **repository** is a class that encapsulates all data access logic for a specific entity.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ARCHITECTURE LAYERS                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌────────────────────────────────────────────────────────────────┐ │
│   │                    API ROUTER                                   │ │
│   │  @router.get("/videos")                                        │ │
│   └──────────────────────────────┬─────────────────────────────────┘ │
│                                  │                                   │
│                                  ▼                                   │
│   ┌────────────────────────────────────────────────────────────────┐ │
│   │                    SERVICE                                      │ │
│   │  Business logic, validation                                    │ │
│   └──────────────────────────────┬─────────────────────────────────┘ │
│                                  │                                   │
│                                  ▼                                   │
│   ┌────────────────────────────────────────────────────────────────┐ │
│   │                   REPOSITORY                                   │ │
│   │  VideoRepository.get_by_id()                                   │ │
│   │  VideoRepository.list_by_split()                               │ │
│   └──────────────────────────────┬─────────────────────────────────┘ │
│                                  │                                   │
│                                  ▼                                   │
│   ┌────────────────────────────────────────────────────────────────┐ │
│   │                    DATABASE                                     │ │
│   │  PostgreSQL                                                     │ │
│   └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Benefits

1. **Single Responsibility**: All data access in one place
2. **Testability**: Easy to mock for unit tests
3. **Abstraction**: Service layer doesn't know about SQL
4. **Reusability**: Same queries used across multiple services

### VideoRepository

**Source**: `apps/api/app/repositories/video_repository.py` (lines 1-226)

```python
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from ..db.models import Video

class VideoRepository:
    """Repository for Video data access."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, video_id: str) -> Optional[Video]:
        """Get a video by its ID."""
        result = await self.db.execute(
            select(Video).where(Video.video_id == video_id)
        )
        return result.scalar_one_or_none()

    async def get_by_sha256(self, sha256: str) -> Optional[Video]:
        """Get a video by its SHA256 hash."""
        result = await self.db.execute(
            select(Video).where(Video.sha256 == sha256)
        )
        return result.scalar_one_or_none()

    async def list_by_split(
        self,
        split: str,
        limit: int = 100,
        offset: int = 0
    ) -> list[Video]:
        """List videos in a specific split."""
        result = await self.db.execute(
            select(Video)
            .where(Video.split == split)
            .order_by(Video.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def count_by_split(self, split: str) -> int:
        """Count videos in a specific split."""
        result = await self.db.execute(
            select(func.count(Video.video_id))
            .where(Video.split == split)
        )
        return result.scalar() or 0

    async def create(
        self,
        file_path: str,
        size_bytes: int,
        sha256: Optional[str] = None,
        duration_sec: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None,
    ) -> Video:
        """Create a new video record."""
        video = Video(
            file_path=file_path,
            split="temp",
            size_bytes=size_bytes,
            sha256=sha256,
            duration_sec=duration_sec,
            width=width,
            height=height,
            fps=fps,
        )
        self.db.add(video)
        await self.db.flush()  # Get auto-generated values
        await self.db.refresh(video)
        return video

    async def update_split_and_label(
        self,
        video_id: str,
        split: str,
        label: Optional[str] = None
    ) -> Optional[Video]:
        """Update video's split and label."""
        video = await self.get_by_id(video_id)
        if video:
            video.split = split
            video.label = label
            await self.db.flush()
            await self.db.refresh(video)
        return video

    async def get_class_distribution(self, split: str) -> dict[str, int]:
        """Get count of videos per label in a split."""
        result = await self.db.execute(
            select(Video.label, func.count(Video.video_id))
            .where(Video.split == split)
            .where(Video.label.isnot(None))
            .group_by(Video.label)
        )
        return {row[0]: row[1] for row in result.all()}
```

### Using the Repository

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_video_repo(db: AsyncSession = Depends(get_db)) -> VideoRepository:
    return VideoRepository(db)

@router.get("/videos/{video_id}")
async def get_video(
    video_id: str,
    repo: VideoRepository = Depends(get_video_repo)
):
    video = await repo.get_by_id(video_id)
    if not video:
        raise HTTPException(404, "Video not found")
    return video

@router.get("/videos")
async def list_videos(
    split: str = "temp",
    limit: int = 100,
    repo: VideoRepository = Depends(get_video_repo)
):
    return await repo.list_by_split(split, limit=limit)
```

---

## Knowledge Check

1. What is the difference between `mapped_column(nullable=True)` and `Mapped[Optional[str]]`?

2. Why do we use `async with session:` instead of just `session`?

3. What's the difference between `result.scalar_one()` and `result.scalar_one_or_none()`?

4. Why can't you use lazy loading in async SQLAlchemy?

5. What is the benefit of using a Repository class?

<details>
<summary>Click to see answers</summary>

1. `nullable=True` affects the database schema (allows NULL). `Mapped[Optional[str]]` affects Python type hints (can be None). Both should match!

2. The context manager ensures the session is properly closed and transactions are handled (commit on success, rollback on exception).

3. `scalar_one()` raises an error if there isn't exactly one result. `scalar_one_or_none()` returns None if there are zero results, but still raises if there are multiple.

4. Lazy loading requires synchronous database calls. In async code, you can't make sync calls in an async context. Use `selectinload()` for eager loading instead.

5. Separates data access logic from business logic, makes code testable (easy to mock), provides a single place for all queries related to an entity.

</details>

---

## Hands-On Exercise 5

### Setup

```python
# test_orm.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Import models (adjust path as needed)
import sys
sys.path.append('/home/user/project-reachy-emotion/apps/api/app')
from db.models import Video, TrainingRun, Base
from db.enums import SplitEnum, EmotionEnum

DATABASE_URL = "postgresql+asyncpg://reachy_app:password@localhost/reachy_local"

async def main():
    engine = create_async_engine(DATABASE_URL, echo=True)

    # Create tables (for testing)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        # Your code here...
        pass

if __name__ == "__main__":
    asyncio.run(main())
```

### Task 1: Create Videos

```python
async with Session() as session:
    # Create 3 videos
    videos = [
        Video(file_path="videos/orm_test/001.mp4", size_bytes=1000000),
        Video(file_path="videos/orm_test/002.mp4", size_bytes=2000000),
        Video(file_path="videos/orm_test/003.mp4", size_bytes=3000000),
    ]
    session.add_all(videos)
    await session.commit()

    # Print auto-generated IDs
    for v in videos:
        print(f"Created: {v.video_id}")
```

### Task 2: Query Videos

```python
async with Session() as session:
    # Get all temp videos
    result = await session.execute(
        select(Video).where(Video.split == "temp")
    )
    videos = result.scalars().all()
    print(f"Found {len(videos)} temp videos")

    # Get with limit and order
    result = await session.execute(
        select(Video)
        .where(Video.split == "temp")
        .order_by(Video.size_bytes.desc())
        .limit(2)
    )
    top_videos = result.scalars().all()
    for v in top_videos:
        print(f"{v.file_path}: {v.size_bytes} bytes")
```

### Task 3: Update Videos

```python
async with Session() as session:
    # Get a video and update it
    result = await session.execute(
        select(Video).where(Video.file_path == "videos/orm_test/001.mp4")
    )
    video = result.scalar_one_or_none()

    if video:
        video.split = "dataset_all"
        video.label = "happy"
        await session.commit()
        print(f"Updated {video.video_id}: split={video.split}, label={video.label}")
```

### Task 4: Create a Repository Class

```python
class SimpleVideoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, video_id: str) -> Video | None:
        # Implement this
        pass

    async def count_by_label(self, label: str) -> int:
        # Implement this
        pass

    async def promote(self, video_id: str, label: str) -> Video | None:
        # Implement this
        pass

# Test your repository
async with Session() as session:
    repo = SimpleVideoRepository(session)
    count = await repo.count_by_label("happy")
    print(f"Happy videos: {count}")
```

### Task 5: Clean Up

```python
async with Session() as session:
    # Delete test videos
    await session.execute(
        delete(Video).where(Video.file_path.like("videos/orm_test/%"))
    )
    await session.commit()
    print("Cleaned up test videos")
```

---

## Summary

In this module, you learned:

- ✅ What an ORM is and why we use SQLAlchemy
- ✅ How to define models with Mapped[] and mapped_column()
- ✅ Managing sessions in async code
- ✅ CRUD operations: Create, Read, Update, Delete
- ✅ Defining relationships between models
- ✅ The Repository pattern for clean data access

**Next**: [Module 6: API Integration](./06-MODULE-API-INTEGRATION.md)
