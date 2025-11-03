# SQLAlchemy config guide_01

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/18/2025 12:59:20  
**Updated:** 10/18/2025 14:16:00  
**Exported:** 10/21/2025 20:12:49  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f3c766-4af8-832c-8cf1-62bf468cbd88](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f3c766-4af8-832c-8cf1-62bf468cbd88)  

## Prompt:
consider the chat titled 'Progress Reachy_08.4.2.'
you wrote:
What’s left (ordered, with “definition of done”)
1.	Media Mover API (Ubuntu 1) — FastAPI + SQLAlchemy
o	Endpoints: POST /ingest, POST /label, POST /promote, GET /stats, GET /videos/:id.
o	DoD: Writes records to media.video, generates thumbs, emits promotion_log entries, returns media.v_video_urls hrefs. (Unit tests for triggers, unique‐hash behavior.) 

Focus on the activities required to implement SQLAlchemy in project Reachy_08.4.2.
Explain the purpose of using SQLAlchemy.  
Provide a step-by-step guide to configure SQLAlchemy on Ubuntu 1.

## Response:
Thought for 27s

Got it—let’s lock in SQLAlchemy for Reachy\_08.4.2.

Why SQLAlchemy here (short and sweet)
=====================================

*   **Single source of truth for media metadata.** Your requirements call for Postgres-based tracking and agent workflows that read/write those records. SQLAlchemy gives you a clean, typed model layer the FastAPI service can trust. requirements\_08.4.2
*   **Policy enforcement in the DB, expressed in code.** The project mandates: (a) every promotion updates Postgres, (b) `videos/test` must have **no label**, (c) `videos/train` **must** have a label, and (d) a balanced test set. You’ll encode these as constraints/migrations (Alembic) and simple ORM checks. requirements\_08.4.2 AGENTS\_08.4.2 AGENTS\_08.4.2
*   **Future-proofing + migrations.** SQLAlchemy 2.0 + Alembic 1.13 are explicitly in spec; that’s your stable backbone for evolving tables, views, and indexes as agents mature. requirements\_08.4.2
*   **Easier testing + CI.** Models are importable in isolation, so you can spin a test DB, run unit tests for triggers/uniques, and keep CI green. Dev Environment\_Windsurf\_Claude…

* * *

What you’ll implement (scope)
=============================

**Tables (minimum):**

*   `media.video` — one row per file in `/videos/{temp,train,test}` with `sha256`, `split` (`temp|train|test`), `label` (`happy|sad` or `NULL`), `duration_ms`, `fps`, `width`, `height`, `path_rel`.
*   `media.promotion_log` — append-only trail for `temp→train/test` (who/when/why), including `intended_emotion`.
*   **Constraint:** `label IS NULL` when `split='test'`; `label IS NOT NULL` when `split='train'`. (The “chk\_split\_label” rule the agents depend on.) requirements\_08.4.2 AGENTS\_08.4.2
*   **Indexes:** `UNIQUE(sha256)`, `idx_video_split`, and a small composite on `(split,label)` for balance checks.

**Optional view:** `media.v_video_urls` that returns `href` fields (e.g., `/videos/...` and `/thumbs/...`) from `path_rel`. Your Media Mover GETs can return this directly.

* * *

Step-by-step on Ubuntu 1
========================

0) System prep (once)
---------------------

```bash
sudo apt update
sudo apt install -y python3.11-venv python3.11-dev build-essential libpq-dev
```

1) Create the API venv and install deps
---------------------------------------

Inside your FastAPI project (e.g., `apps/api`):

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip wheel

# Core
pip install "fastapi>=0.110" "uvicorn[standard]>=0.29"
pip install "sqlalchemy>=2.0" "alembic>=1.13"
pip install "psycopg[binary]>=3.1" "pydantic>=2.5" "python-dotenv>=1.0"
# (Optional) async stack later: pip install asyncpg
```

This aligns with the tech stack in the requirements. requirements\_08.4.2

2) Wire up configuration
------------------------

Create `apps/api/app/core/settings.py`:

```python
from pydantic import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_NAME: str = "reachy_local"
    DB_USER: str = "reachy_app"
    DB_PASS: str = "change_me"
    BASE_MEDIA_URL: str = "/videos"
    BASE_THUMBS_URL: str = "/thumbs"

    @property
    def DATABASE_URL(self) -> str:
        return (f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASS}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}")

@lru_cache
def get_settings():
    return Settings()  # loads from env if present
```

3) Engine + session dependency for FastAPI
------------------------------------------

`apps/api/app/db.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .core.settings import get_settings

settings = get_settings()
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

4) Declarative models (constraints baked in)
--------------------------------------------

`apps/api/app/models.py`:

```python
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    CheckConstraint, Column, DateTime, Enum as SQLEnum,
    Integer, String, UniqueConstraint, ForeignKey, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class Split(str, Enum):
    temp = "temp"
    train = "train"
    test  = "test"

class Label(str, Enum):
    happy = "happy"
    sad   = "sad"

class Video(Base):
    __tablename__ = "video"
    __table_args__ = (
        UniqueConstraint("sha256", name="uq_video_sha256"),
        CheckConstraint(
            "(split = 'test' AND label IS NULL) OR (split = 'train' AND label IS NOT NULL) OR (split = 'temp')",
            name="chk_split_label"  # agents rely on this
        ),
        Index("idx_video_split", "split"),
        Index("idx_video_split_label", "split", "label"),
        {"schema": "media"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    split: Mapped[Split] = mapped_column(SQLEnum(Split), nullable=False, default=Split.temp)
    label: Mapped[Label | None] = mapped_column(SQLEnum(Label), nullable=True)
    path_rel: Mapped[str] = mapped_column(String(512), nullable=False)   # e.g. train/abc.mp4
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    fps: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    promotions: Mapped[list["PromotionLog"]] = relationship(back_populates="video", cascade="all, delete-orphan")

class PromotionLog(Base):
    __tablename__ = "promotion_log"
    __table_args__ = ({"schema": "media"},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("media.video.id"), nullable=False)
    from_split: Mapped[Split] = mapped_column(SQLEnum(Split), nullable=False)
    to_split: Mapped[Split] = mapped_column(SQLEnum(Split), nullable=False)
    intended_emotion: Mapped[Label | None] = mapped_column(SQLEnum(Label), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    video: Mapped[Video] = relationship(back_populates="promotions")
```

> That `chk_split_label` check is the heart of your **Labeling / Promotion Agents** policy: label required in `train`, label forbidden in `test`. AGENTS\_08.4.2 AGENTS\_08.4.2

5) Alembic migrations
---------------------

Initialize:

```bash
alembic init -t async alembic   # or just `alembic init alembic` for sync
```

Edit `alembic.ini` to leave `sqlalchemy.url` blank (we’ll inject via env).  
In `alembic/env.py`, import your Base and settings:

```python
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.db import Base
from app.core.settings import get_settings

config = context.config
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", get_settings().DATABASE_URL)

target_metadata = Base.metadata
fileConfig(config.config_file_name)

def run_migrations_offline():
    context.configure(url=config.get_main_option("sqlalchemy.url"),
                      target_metadata=target_metadata,
                      literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section),
                                     prefix='sqlalchemy.',
                                     poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Autogenerate your first migration (schema + indexes + check):

```bash
alembic revision --autogenerate -m "create media.video + promotion_log"
alembic upgrade head
```

6) Endpoint stubs using the ORM
-------------------------------

These align with your Media Mover checklist (`/ingest`, `/label`, `/promote`, `/stats`, `/videos/:id`). requirements\_08.4.2

```python
# apps/api/app/routes/media.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Video, PromotionLog, Split, Label

router = APIRouter(prefix="/media")

@router.post("/ingest")
def ingest_video(payload: dict, db: Session = Depends(get_db)):
    # create Video in split=temp, no label yet
    v = Video(
        sha256=payload["sha256"],
        split=Split.temp,
        path_rel=f"temp/{payload['filename']}",
        duration_ms=payload.get("duration_ms"),
        fps=payload.get("fps"),
        width=payload.get("width"),
        height=payload.get("height"),
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return {"id": v.id}

@router.post("/label")
def set_label(video_id: int, label: Label, db: Session = Depends(get_db)):
    v = db.get(Video, video_id)
    if not v:
        raise HTTPException(404)
    # allow label only if not already in test
    if v.split == Split.test:
        raise HTTPException(400, "test split forbids labels")
    v.label = label
    db.commit()
    return {"ok": True}

@router.post("/promote")
def promote(video_id: int, to_split: Split, db: Session = Depends(get_db)):
    v = db.get(Video, video_id)
    if not v:
        raise HTTPException(404)
    from_split = v.split
    v.split = to_split
    # OPTIONAL: move file on disk here (atomic mv), then update path_rel
    # path_rel rewrite: temp/foo.mp4 -> train/foo.mp4 or test/foo.mp4
    db.add(PromotionLog(video_id=v.id, from_split=from_split, to_split=to_split,
                        intended_emotion=v.label))
    db.commit()  # will fail if chk_split_label is violated
    return {"ok": True}
```

7) URL view (optional but handy)
--------------------------------

Create an Alembic “manual” migration that defines a Postgres view:

```sql
CREATE OR REPLACE VIEW media.v_video_urls AS
SELECT
  id,
  CASE
    WHEN split='train' THEN '/videos/train/'||split_part(path_rel,'/',2)
    WHEN split='test'  THEN '/videos/test/'||split_part(path_rel,'/',2)
    ELSE '/videos/temp/'||split_part(path_rel,'/',2)
  END AS href,
  REPLACE(CASE
    WHEN split='train' THEN '/thumbs/train/'||split_part(path_rel,'/',2)
    WHEN split='test'  THEN '/thumbs/test/'||split_part(path_rel,'/',2)
    ELSE '/thumbs/temp/'||split_part(path_rel,'/',2)
  END, '.mp4', '.jpg') AS thumb_href
FROM media.video;
```

Returning these `href`s matches the “return v\_video\_urls” idea from the DoD you quoted.

8) Tests that prove the rules
-----------------------------

*   **Unique hash:** insert the same `sha256` twice → expect `IntegrityError`.
*   **Label rules:**
    1.  `temp → test` while `label IS NOT NULL` should **fail** (constraint).
    2.  `temp → train` with `label IS NULL` should **fail** (constraint).
    3.  Happy path: `temp + label → train` passes; `temp (no label) → test` passes.

These checks line up with FR-002/FR-003 and the agents’ responsibilities. requirements\_08.4.2 AGENTS\_08.4.2

* * *

Quick acceptance checklist (“definition of done” for SQLAlchemy)
================================================================

*   Models & constraints created (incl. `chk_split_label`, uniques, indexes). AGENTS\_08.4.2
*   Alembic initialized; first migration applied; view created (if desired). requirements\_08.4.2
*   FastAPI endpoints use a scoped session; errors surface cleanly on constraint violations.
*   Unit tests cover: duplicate `sha256`, illegal promotions, legal promotions.
*   `/promote` writes a `promotion_log` row on every move. AGENTS\_08.4.2
*   `/stats` (easy add) queries `(split,label)` counts to support the **50/50 test balance** display gate. requirements\_08.4.2

If you want, I can drop this into your existing repo structure (folders, files, and a first Alembic migration) so you can run `alembic upgrade head` and immediately hit `/media/ingest` to see rows land.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)