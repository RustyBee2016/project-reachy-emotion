# SQLAlchemy config guide_02

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/18/2025 13:54:38  
**Updated:** 10/18/2025 14:15:50  
**Exported:** 10/21/2025 20:13:05  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f3d45a-549c-8320-93d0-767276d314d7](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f3d45a-549c-8320-93d0-767276d314d7)  

## Prompt:
consider the chat titled 'SQLAlchemy configuration guide.'
provide a detailed explanation of the code in each section.
Include each code block and the related explanation in a separate section.

## Response:
Thought for 13s

Got it. I’ll walk you through a clean SQLAlchemy setup for the Media Mover API (FastAPI + Postgres), with each code block in its own section and a plain-English explanation right after. This matches Reachy\_08.4.2’s stack (FastAPI, Postgres, SQLAlchemy 2.x, Alembic).

1) Settings: centralize DB/env config
=====================================

```python
# app/core/settings.py
from pydantic import BaseSettings, Field, PostgresDsn
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    # Core
    ENV: str = Field("dev", description="Environment name")
    DEBUG: bool = False

    # Database (PostgreSQL via SQLAlchemy)
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_USER: str = "reachy_app"
    DB_PASSWORD: str = "change_me"
    DB_NAME: str = "reachy_local"

    SQLALCHEMY_ECHO: bool = False
    SQLALCHEMY_POOL_SIZE: int = 10
    SQLALCHEMY_MAX_OVERFLOW: int = 20
    SQLALCHEMY_POOL_PRE_PING: bool = True

    # Optional: assembled DSN (if you prefer a single var in .env)
    DATABASE_URL: Optional[PostgresDsn] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def sqlalchemy_url(self) -> str:
        if self.DATABASE_URL:
            return str(self.DATABASE_URL)
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

**Explanation**

*   `BaseSettings` pulls values from `.env` and environment variables, so you can keep secrets out of code.
*   `sqlalchemy_url` builds a proper SQLAlchemy DSN for psycopg (v3).
*   Pooling toggles (`POOL_SIZE`, `MAX_OVERFLOW`, `PRE_PING`) avoid stale connections and help under load.
*   `lru_cache` turns settings into a singleton without global state.

2) Engine & Session: one place, one pattern
===========================================

```python
# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.settings import get_settings

settings = get_settings()

engine = create_engine(
    settings.sqlalchemy_url,
    echo=settings.SQLALCHEMY_ECHO,
    pool_size=settings.SQLALCHEMY_POOL_SIZE,
    max_overflow=settings.SQLALCHEMY_MAX_OVERFLOW,
    pool_pre_ping=settings.SQLALCHEMY_POOL_PRE_PING,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)
```

**Explanation**

*   `create_engine` is the Postgres connection factory. `future=True` opts into SQLAlchemy 2.x behavior.
*   `SessionLocal` gives you short-lived, request-scoped sessions (no autocommit/autoflush surprises).
*   Use one engine per process. Sessions are cheap; create one per request and close it.

3) Declarative base & common mixins
===================================

```python
# app/db/base.py
from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column
from sqlalchemy import text
from datetime import datetime

class Base(DeclarativeBase):
    # Default naming for __tablename__
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"),
        onupdate=text("now()"),
        nullable=False,
    )
```

**Explanation**

*   `DeclarativeBase` is the 2.x way to define a base class for all models.
*   `TimestampMixin` keeps your `created_at/updated_at` uniform and DB-driven (`now()` in Postgres).

4) Models: tables you’ll actually use
=====================================

```python
# app/db/models.py
from __future__ import annotations
from typing import Optional, Literal
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, Enum, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import TEXT
from app.db.base import Base, TimestampMixin

SplitT = Literal["temp", "train", "test"]
LabelT = Literal["happy", "sad"]

class Video(Base, TimestampMixin):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(TEXT, nullable=False)
    rel_dir: Mapped[str] = mapped_column(TEXT, nullable=False)   # e.g., "videos/train"
    duration_sec: Mapped[float] = mapped_column(nullable=True)
    fps: Mapped[float] = mapped_column(nullable=True)
    width: Mapped[int] = mapped_column(nullable=True)
    height: Mapped[int] = mapped_column(nullable=True)

    # Dataset bookkeeping
    split: Mapped[SplitT] = mapped_column(Enum("temp", "train", "test", name="split_t"), nullable=False, default="temp")
    label: Mapped[Optional[LabelT]] = mapped_column(Enum("happy", "sad", name="label_t"), nullable=True)

    # Example uniqueness: same sha256 cannot exist twice in same split
    __table_args__ = (
        UniqueConstraint("sha256", "split", name="uq_video_sha256_split"),
    )

class PromotionLog(Base, TimestampMixin):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("video.id", ondelete="CASCADE"), nullable=False)
    from_split: Mapped[SplitT] = mapped_column(Enum("temp", "train", "test", name="split_t"), nullable=False)
    to_split: Mapped[SplitT] = mapped_column(Enum("temp", "train", "test", name="split_t"), nullable=False)
    intended_emotion: Mapped[Optional[LabelT]] = mapped_column(Enum("happy", "sad", name="label_t"), nullable=True)
    actor: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
```

**Explanation**

*   `Video` holds all metadata you care about plus `split` and optional `label`.
*   The **rule you described** is enforced at the service layer:
    *   `train` items must have a label (`happy`/`sad`).
    *   `test` items must have **no** label.
*   `PromotionLog` is your immutable audit trail for moves (`temp → train/test`) with who/what/when.

5) Pydantic schemas: API contracts
==================================

```python
# app/schemas/video.py
from pydantic import BaseModel, Field
from typing import Optional, Literal

SplitT = Literal["temp", "train", "test"]
LabelT = Literal["happy", "sad"]

class VideoCreate(BaseModel):
    sha256: str = Field(..., min_length=64, max_length=64)
    filename: str
    rel_dir: str = "videos/temp"
    duration_sec: Optional[float] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None

class VideoOut(BaseModel):
    id: int
    sha256: str
    filename: str
    rel_dir: str
    split: SplitT
    label: Optional[LabelT]

    class Config:
        from_attributes = True

class PromoteRequest(BaseModel):
    to_split: SplitT
    intended_emotion: Optional[LabelT] = None
```

**Explanation**

*   `VideoCreate` is the inbound payload when you first register a file (goes to `temp`).
*   `VideoOut` is what you return to clients (safe fields only).
*   `PromoteRequest` models a move (and carries `intended_emotion` when promoting to `train`).

6) DB dependency for FastAPI
============================

```python
# app/api/deps.py
from typing import Generator
from app.db.session import SessionLocal

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Explanation**

*   Classic “session-per-request” dependency. Keeps connections short and predictable.

7) Repository helpers (CRUD + rules)
====================================

```python
# app/repositories/video_repo.py
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from app.db.models import Video, PromotionLog
from app.schemas.video import PromoteRequest

class VideoRepo:
    @staticmethod
    def create(db: Session, **fields) -> Video:
        obj = Video(**fields)
        db.add(obj)
        db.flush()  # get obj.id
        return obj

    @staticmethod
    def get(db: Session, video_id: int) -> Video | None:
        return db.get(Video, video_id)

    @staticmethod
    def by_sha(db: Session, sha256: str) -> Video | None:
        return db.scalar(select(Video).where(Video.sha256 == sha256))

    @staticmethod
    def promote(db: Session, video: Video, req: PromoteRequest, actor: str = "system") -> Video:
        # Enforce label rules at the service layer
        if req.to_split == "train" and not req.intended_emotion:
            raise ValueError("Promoting to 'train' requires intended_emotion (happy|sad)")
        if req.to_split == "test" and req.intended_emotion:
            raise ValueError("Promoting to 'test' must not include intended_emotion")

        from_split = video.split
        video.split = req.to_split
        video.label = req.intended_emotion if req.to_split == "train" else None

        log = PromotionLog(
            video_id=video.id,
            from_split=from_split,
            to_split=req.to_split,
            intended_emotion=req.intended_emotion,
            actor=actor,
        )
        db.add(log)
        db.flush()  # persist both changes

        return video
```

**Explanation**

*   Encapsulates DB logic and the **business rules** around promotion.
*   `flush()` ensures IDs exist before you link logs.
*   If later you add Postgres CHECK constraints or triggers, this still reads cleanly.

8) FastAPI routes (subset of your endpoints)
============================================

```python
# app/api/routes/media.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.video import VideoCreate, VideoOut, PromoteRequest
from app.repositories.video_repo import VideoRepo

router = APIRouter(prefix="/media", tags=["media"])

@router.post("/ingest", response_model=VideoOut, status_code=201)
def ingest_video(payload: VideoCreate, db: Session = Depends(get_db)):
    # Dedup by sha256 within 'temp' is optional; uniqueness by sha+split is at DB level
    existing = VideoRepo.by_sha(db, payload.sha256)
    if existing and existing.split == "temp":
        return existing

    video = VideoRepo.create(
        db,
        sha256=payload.sha256,
        filename=payload.filename,
        rel_dir=payload.rel_dir,
        duration_sec=payload.duration_sec,
        fps=payload.fps,
        width=payload.width,
        height=payload.height,
        split="temp",
    )
    db.commit()
    db.refresh(video)
    return video

@router.post("/promote/{video_id}", response_model=VideoOut)
def promote_video(video_id: int, req: PromoteRequest, db: Session = Depends(get_db)):
    video = VideoRepo.get(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    try:
        VideoRepo.promote(db, video, req, actor="api")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db.commit()
    db.refresh(video)
    return video

@router.get("/videos/{video_id}", response_model=VideoOut)
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = VideoRepo.get(db, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video
```

**Explanation**

*   Thin HTTP layer. Business logic stays in the repo.
*   `ingest` registers a video in `temp`.
*   `promote` enforces the “train requires label / test requires no label” rule and logs it.
*   `get_video` is your lookup endpoint.

9) Alembic setup (env & first migration)
========================================

```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.core.settings import get_settings
from app.db.base import Base  # import models before run_migrations_online
from app.db import models  # noqa: F401 (ensure models are imported)

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.sqlalchemy_url)

def run_migrations_offline():
    context.configure(
        url=settings.sqlalchemy_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        {"sqlalchemy.url": settings.sqlalchemy_url},
        prefix="",
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Explanation**

*   Wires Alembic to your app’s URL and metadata.
*   `compare_type=True` lets Alembic detect enum/column type changes.
*   Importing `models` ensures tables are in `Base.metadata` when migrations run.

```python
# alembic/versions/2025_10_18_0001_init.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    split_t = sa.Enum("temp", "train", "test", name="split_t")
    label_t = sa.Enum("happy", "sad", name="label_t")
    split_t.create(op.get_bind(), checkfirst=True)
    label_t.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "video",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("filename", sa.Text, nullable=False),
        sa.Column("rel_dir", sa.Text, nullable=False),
        sa.Column("duration_sec", sa.Float, nullable=True),
        sa.Column("fps", sa.Float, nullable=True),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("height", sa.Integer, nullable=True),
        sa.Column("split", split_t, nullable=False, server_default="temp"),
        sa.Column("label", label_t, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=False), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("sha256", "split", name="uq_video_sha256_split"),
    )
    op.create_index("ix_video_sha256", "video", ["sha256"])

    op.create_table(
        "promotionlog",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("video_id", sa.Integer, sa.ForeignKey("video.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_split", split_t, nullable=False),
        sa.Column("to_split", split_t, nullable=False),
        sa.Column("intended_emotion", label_t, nullable=True),
        sa.Column("actor", sa.String(64), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=False), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=False), server_default=sa.text("now()"), nullable=False),
    )

def downgrade():
    op.drop_table("promotionlog")
    op.drop_index("ix_video_sha256", table_name="video")
    op.drop_table("video")
    sa.Enum(name="label_t").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="split_t").drop(op.get_bind(), checkfirst=True)
```

**Explanation**

*   First migration creates your enums and tables, plus the uniqueness constraint and index.
*   `checkfirst=True` keeps it idempotent if re-run.
*   Timestamps default to `now()` server-side, so you don’t need to pass them from Python.

10) App wiring
==============

```python
# app/main.py
from fastapi import FastAPI
from app.api.routes.media import router as media_router

app = FastAPI(title="Reachy Media API", version="0.1.0")

app.include_router(media_router, prefix="/api")
```

**Explanation**

*   Keeps `main.py` tiny. All the heavy lifting lives in `app/api/routes/...`
*   `prefix="/api"` yields paths like `/api/media/ingest` etc.

11) A couple of service-level checks (balance/test rules)
=========================================================

```python
# app/services/dataset_rules.py
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from app.db.models import Video

def test_is_balanced(db: Session, tol: float = 0.05) -> bool:
    total = db.scalar(select(func.count()).select_from(Video).where(Video.split == "test")) or 0
    if total == 0:
        return False
    happy = db.scalar(select(func.count()).where(Video.split == "test", Video.label.is_(None)))  # test has no labels
    # For test, we *don’t* use labels; this function can be adapted to count by intended class
    # if you store a side-table or derive class elsewhere. Placeholder to show pattern.
    # Replace with your chosen balance computation strategy.
    return True  # stub; implement your 50/50 accounting where appropriate
```

**Explanation**

*   Shows how you’d hang balance checks off SQL (counts/ratios).
*   Your actual 50/50 test policy is “no labels in test,” so balance usually tracked at _promotion time_ via counters and the `PromotionLog`.

12) Tests: fast, isolated sessions
==================================

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.models import *  # ensure models registered

@pytest.fixture(scope="function")
def db_session():
    # Use a dedicated test database or transact against a temp schema
    engine = create_engine("postgresql+psycopg://reachy_owner:change_me@127.0.0.1:5432/reachy_test", future=True)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(engine)
    try:
        session = TestingSessionLocal()
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
```

**Explanation**

*   For Postgres-specific features (enums, JSONB, etc.), test **against Postgres**, not SQLite.
*   Create/drop tables per test function keeps tests hermetic.
*   For bigger suites, use a transaction+rollback pattern instead of create/drop.

13) Optional: map a SQL view (URLs from Nginx base)
===================================================

```python
# app/db/views.py
from sqlalchemy import text
from sqlalchemy.orm import registry, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import TEXT

mapper_registry = registry()

@mapper_registry.mapped
class V_VideoUrls:
    __tablename__ = "v_video_urls"
    __table__ = text("v_video_urls")  # map to an existing DB view

    id: Mapped[int]
    video_url: Mapped[str] = mapped_column(TEXT)
    thumb_url: Mapped[str] = mapped_column(TEXT)
```

**Explanation**

*   If your bootstrap SQL creates a DB **view** that joins filesystem paths with Nginx prefixes (e.g., `/videos/...`, `/thumbs/...`), you can map it read-only for quick lookups.
*   Views are perfect for “serve-ready” hrefs without rebuilding strings in Python.

* * *

What to do next (quick hits)
----------------------------

*   Drop these into `apps/api/` in your monorepo and run `alembic init` → add the env + migration above → `alembic upgrade head`.
*   Wire `.env` on Ubuntu 1 with your real DB creds.
*   Point Nginx at `/videos` and `/thumbs`; keep the service enforcing “label must be set for train, unset for test.”
*   Add the remaining endpoints (`/label`, `/stats`) using the same repo+service pattern.

If you want, I can tailor the `/stats` endpoint to return: total per split, per-class (train), and whether the test split is balanced to within your tolerance—all in one SQL roundtrip.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)