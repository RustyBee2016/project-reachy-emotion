# SQLAlchemy config guide_03

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/18/2025 14:13:23  
**Updated:** 10/18/2025 14:15:38  
**Exported:** 10/21/2025 20:13:18  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f3d8c2-1920-8330-a0be-03a8da1d27df](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f3d8c2-1920-8330-a0be-03a8da1d27df)  

## Prompt:
consider the chat titled 'SQLAlchemy configuration guide_02.'
Expound on each explanation and include a line-by-line explanation of the code.
Organize the detailed code explanations into individual sections based on each Python (.py) file.

## Response:
Thought for 18s

Nice—let’s turn your “SQLAlchemy configuration guide\_02” into something you can hand to your future self (or a teammate) and they’ll be productive in minutes.

I’ve organized this by Python file. For each file, you get the full code block first, then a **line-by-line** explanation. This matches a typical FastAPI + SQLAlchemy 2.x setup (sync engine used in background threads via `SessionLocal`; you can swap to fully-async later if needed).

* * *

1) `app/core/config.py` — settings
==================================

```python
# app/core/config.py
from pydantic import BaseSettings, AnyUrl

class Settings(BaseSettings):
    # Core app
    APP_NAME: str = "Reachy Media API"
    DEBUG: bool = False

    # Database
    DATABASE_URL: AnyUrl | str = "postgresql+psycopg://reachy_app:REDACTED@/reachy_local?host=/var/run/postgresql"

    # CORS / Security (tweak for your LAN)
    CORS_ORIGINS: list[str] = ["http://localhost:8501", "http://ubuntu2", "http://10.0.4.140"]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

**Line-by-line**

*   `from pydantic...`: Pydantic settings give you typed env-driven config.
*   `class Settings(BaseSettings)`: Every attribute is sourced from env/.env if present.
*   `APP_NAME/DEBUG`: App toggles used by `main.py`.
*   `DATABASE_URL`: SQLAlchemy URL. Here we default to a **Unix socket** (`host=/var/run/postgresql`) and psycopg v3 driver.
*   `CORS_ORIGINS`: Allow your Streamlit (Ubuntu 2) to call the API.
*   `class Config...`: Tell Pydantic to read `.env` and keep case sensitive.
*   `settings = Settings()`: Singleton you can import anywhere.

* * *

2) `app/db/database.py` — engine, session factory, base
=======================================================

```python
# app/db/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Engine: sync, pooled; use psycopg v3 (psycopg)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,           # recycle dead conns
    pool_size=10,                 # tune for your box
    max_overflow=20,              # burst capacity
    future=True,                  # 2.0 style
)

# Session factory: one per request (FastAPI dependency)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

# Declarative base for ORM models
Base = declarative_base()
```

**Line-by-line**

*   `create_engine(...)`: Makes a pooled connection to Postgres.
*   `pool_pre_ping=True`: Detects broken connections before using them.
*   `pool_size/max_overflow`: Reasonable defaults for a small API.
*   `future=True`: Opt into SQLAlchemy 2.x behaviors.
*   `SessionLocal = sessionmaker(...)`: Produces sessions on demand without autocommit/flush surprises.
*   `Base = declarative_base()`: All ORM models will subclass this.

* * *

3) `app/db/models.py` — ORM tables
==================================

```python
# app/db/models.py
from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, Interval, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.database import Base
import enum

class Split(str, enum.Enum):
    temp = "temp"
    train = "train"
    test = "test"

class Emotion(str, enum.Enum):
    happy = "happy"
    sad = "sad"

class Video(Base):
    __tablename__ = "video"
    id = Column(Integer, primary_key=True, index=True)
    sha256 = Column(String(64), nullable=False, unique=True)          # content hash
    filename = Column(String(255), nullable=False)
    split = Column(Enum(Split, name="split"), nullable=False, default=Split.temp)
    label = Column(Enum(Emotion, name="emotion"), nullable=True)      # NOTE: must be NULL for test
    duration = Column(Interval, nullable=True)
    fps = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    meta = Column(JSONB, nullable=True)                               # freeform metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("filename", name="uq_video_filename"),
    )

class PromotionLog(Base):
    __tablename__ = "promotion_log"
    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, nullable=False, index=True)
    from_split = Column(String(16), nullable=False)
    to_split = Column(String(16), nullable=False)
    intended_emotion = Column(String(16), nullable=True)
    actor = Column(String(64), nullable=False)                        # who/what moved it
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

**Line-by-line**

*   `Split/Emotion`: Enums enforce valid values (`train/test/temp`, `happy/sad`).
*   `Video.id`: Integer PK.
*   `sha256`: Unique content hash to de-dupe.
*   `filename`: Original or canonical filename; also unique.
*   `split`: Where the file lives (`/videos/{temp|train|test}`).
*   `label`: Emotion label. **Business rule:** must be `NULL` for `test`.
*   `duration/fps/width/height`: Useful media properties for UI and gates.
*   `meta`: JSONB for generator name/version, prompts, etc.
*   `created_at`: DB server timestamp.
*   `__table_args__`: Make `filename` unique at the DB level.
*   `PromotionLog`: Immutable audit trail whenever a file moves splits.

* * *

4) `app/db/schemas.py` — Pydantic request/response models
=========================================================

```python
# app/db/schemas.py
from datetime import timedelta, datetime
from pydantic import BaseModel, Field
from typing import Literal, Optional, Any

Split = Literal["temp", "train", "test"]
Emotion = Literal["happy", "sad"]

class VideoBase(BaseModel):
    filename: str = Field(..., max_length=255)
    split: Split
    label: Optional[Emotion] = None
    duration: Optional[timedelta] = None
    fps: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    meta: Optional[dict[str, Any]] = None

class VideoCreate(VideoBase):
    sha256: str = Field(..., min_length=64, max_length=64)

class VideoOut(VideoBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True  # SQLA 2.x: map ORM → Pydantic

class PromoteIn(BaseModel):
    video_id: int
    to_split: Split
    intended_emotion: Optional[Emotion] = None
    note: Optional[str] = None
```

**Line-by-line**

*   `Split/Emotion` as `Literal` to keep API strict.
*   `VideoBase`: Shared fields between create/read.
*   `VideoCreate.sha256`: Required on ingest.
*   `VideoOut.Config.from_attributes`: Pydantic v2 way to serialize ORM.
*   `PromoteIn`: Payload for `/promote` (Labeling/Promotion flow).

* * *

5) `app/db/crud.py` — DB operations
===================================

```python
# app/db/crud.py
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import Optional
from app.db import models
from app.db.schemas import VideoCreate, PromoteIn

def get_video_by_sha(db: Session, sha256: str) -> Optional[models.Video]:
    stmt = select(models.Video).where(models.Video.sha256 == sha256)
    return db.execute(stmt).scalars().first()

def create_video(db: Session, data: VideoCreate) -> models.Video:
    obj = models.Video(
        sha256=data.sha256,
        filename=data.filename,
        split=data.split,
        label=data.label,
        duration=data.duration,
        fps=data.fps,
        width=data.width,
        height=data.height,
        meta=data.meta,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(obj)
    return obj

def log_promotion(db: Session, video_id: int, from_split: str, to_split: str, intended_emotion: Optional[str], actor: str, note: Optional[str]):
    log = models.PromotionLog(
        video_id=video_id,
        from_split=from_split,
        to_split=to_split,
        intended_emotion=intended_emotion,
        actor=actor,
        note=note,
    )
    db.add(log)
    db.commit()

def promote_video(db: Session, data: PromoteIn, actor: str) -> models.Video:
    # Fetch
    video = db.get(models.Video, data.video_id)
    if not video:
        raise ValueError("Video not found")

    # Business rules:
    # 1) test split must NOT have a label
    # 2) train split must have a label
    if data.to_split == "test":
        new_label = None
    else:
        if not data.intended_emotion:
            raise ValueError("Training split requires an intended_emotion")
        new_label = data.intended_emotion

    # Update
    stmt = (
        update(models.Video)
        .where(models.Video.id == video.id)
        .values(split=data.to_split, label=new_label)
        .returning(models.Video)
    )
    res = db.execute(stmt)
    db.commit()
    updated = res.scalars().first()

    # Log
    log_promotion(
        db=db,
        video_id=video.id,
        from_split=video.split.value if hasattr(video.split, "value") else video.split,
        to_split=data.to_split,
        intended_emotion=new_label,
        actor=actor,
        note=data.note,
    )
    return updated
```

**Line-by-line**

*   `select(...)`: 2.x style query building.
*   `get_video_by_sha`: Typical idempotent ingest pattern—avoid dupes by hash.
*   `create_video`: Insert row, commit, `refresh` to pull server timestamps/defaults.
*   `log_promotion`: Append immutable audit entry.
*   `promote_video`: Enforce **project rules**:
    *   Moving to `test` → `label=None`.
    *   Moving to `train` → `label` required.
*   `update(...).returning(...)`: Write + fetch updated row in one round trip.
*   `db.commit()` then return the updated ORM object.

* * *

6) `app/api/deps.py` — FastAPI DB dependency
============================================

```python
# app/api/deps.py
from collections.abc import Iterator
from sqlalchemy.orm import Session
from app.db.database import SessionLocal

def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Line-by-line**

*   `get_db()`: Classic “session per request” pattern.
*   `yield db`: FastAPI will inject this into your endpoint function.
*   `finally: db.close()`: Return connection to pool.

* * *

7) `app/api/routes/video.py` — endpoints using SQLAlchemy
=========================================================

```python
# app/api/routes/video.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.db import crud
from app.db.schemas import VideoCreate, VideoOut, PromoteIn

router = APIRouter(prefix="/videos", tags=["videos"])

@router.post("/ingest", response_model=VideoOut, status_code=status.HTTP_201_CREATED)
def ingest_video(payload: VideoCreate, db: Session = Depends(get_db)):
    existing = crud.get_video_by_sha(db, payload.sha256)
    if existing:
        return existing
    try:
        return crud.create_video(db, payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/promote", response_model=VideoOut)
def promote_video(payload: PromoteIn, db: Session = Depends(get_db)):
    try:
        updated = crud.promote_video(db, payload, actor="api/media")
        if not updated:
            raise HTTPException(status_code=404, detail="Video not found")
        return updated
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
```

**Line-by-line**

*   `router = APIRouter(...)`: Namespaces `/videos` endpoints.
*   `ingest_video`: Idempotent insert by hash; returns existing if duplicate.
*   `response_model=VideoOut`: Clean, typed API response.
*   `promote_video`: Applies **train/test label rules** via `crud.promote_video`; “actor” is recorded for the audit trail.

* * *

8) `app/main.py` — assemble the app
===================================

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import video
from app.db.database import engine
from app.db.database import Base

def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(video.router)

    return app

app = create_app()

# Optional: create tables (prefer Alembic in real deployments)
def _bootstrap_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    _bootstrap_db()
```

**Line-by-line**

*   `create_app()`: Factory enables testability.
*   CORS allows your Streamlit UI to hit the API.
*   `include_router(video.router)`: Registers `/videos/*` endpoints.
*   `_bootstrap_db()`: Handy for dev; in prod you’ll use Alembic migrations.

* * *

9) `alembic/env.py` (excerpt) — migrations wired to your engine
===============================================================

```python
# alembic/env.py (essential bits)
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.db.database import engine
from app.db import models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = models.Base.metadata

def run_migrations_offline():
    context.configure(
        url=str(engine.url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Line-by-line**

*   `target_metadata = models.Base.metadata`: Alembic knows what to diff.
*   Offline/online blocks: standard template, but we **import your app engine** so envs stay consistent.

* * *

10) Guardrails you asked for (baked into schema + CRUD)
=======================================================

*   **No-label test rule**: `crud.promote_video` forces `label=None` when `to_split="test"`.
*   **Must-label train rule**: Throws `ValueError` if you promote to `train` without `intended_emotion`.
*   **Uniqueness**: `sha256` and `filename` are unique; prevents duplicates on ingest.
*   **Auditability**: `PromotionLog` records every move, including intent and actor.

* * *

How this maps to your Media Mover endpoints
-------------------------------------------

*   `POST /videos/ingest` → your `/api/media/ingest` (can alias route path if you prefer).
*   `POST /videos/promote` → your `/api/media/promote` action (enforces train/test rules).
*   You can add:
    *   `GET /videos/{id}` (simple `select` by ID)
    *   `GET /stats` (counts per split and per label; a single grouped query)

If you want, I’ll bolt on those two `GET` endpoints and a thin “stats” SQL (group by `split`, `label`) in the same style.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)