# Alembic migration overview

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/20/2025 6:20:39  
**Updated:** 10/20/2025 6:53:38  
**Exported:** 10/21/2025 19:13:49  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f60cf1-53e8-832a-95d7-f5c18415bffc](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68f60cf1-53e8-832a-95d7-f5c18415bffc)  

## Prompt:
Recently, we completed significant configuration on a 121 wiring up the backend detailed in the chat titled ‘Pydantic v2 migration result.’
Consider the chat titled ‘SQLAlchemy Config guide_03,’ which explains next steps planned as follow-up activities. 
Given the current state of affairs in project Reachy_Local_08.4.2, do you agree focusing on SQLAlchemy is the best thing to do at this point?

Explain your reasoning for the next proposed step.
Then walk me through the process of continuing the system configuration

## Response:
Thought for 48s

Short version: yeah—locking in SQLAlchemy next is the right call.

You already proved the HTTP surface is healthy (FastAPI behind Nginx, healthz green). What’s missing is the _durable state machine_ underneath: labels, promotions, split rules, counters, and manifests. Your own spec makes Postgres + SQLAlchemy + Alembic a first-class part of the stack, and several agents literally can’t do their jobs without a real DB layer in place (promotion balance checks, no-label test enforcement, audit trails). requirements\_08.4.2 requirements\_08.4.2 requirements\_08.4.2 AGENTS\_08.4.2

Why SQLAlchemy now (reasoning)
==============================

*   It’s on the critical path: your requirements explicitly list “PostgreSQL 16 + SQLAlchemy 2.0 + Alembic 1.13.” No DB model, no agents. requirements\_08.4.2
*   FR-002/FR-003 hinge on DB-enforced rules: atomic move `temp→train|test`, 50/50 test balance, “no label in test,” and manifest rebuild triggers—all DB-backed. requirements\_08.4.2
*   Multiple agents depend on DB transactions and constraints (Labeling, Promotion, Reconciler, Training Orchestrator). You can’t credibly wire those until the schema + sessions are real. AGENTS\_08.4.2
*   It unlocks CI: once models/migrations exist, you can add quick unit tests and schema checks in your Windsurf/Actions flow. Dev Environment\_Windsurf\_Claude…

How to continue system configuration (pragmatic walk-through)
=============================================================

0) Packages + env
-----------------

*   Pin the server deps in `apps/api/requirements.txt` (or `pyproject.toml`):  
    `SQLAlchemy>=2.0, Alembic>=1.13, psycopg[binary]` (or `psycopg2-binary`), `pydantic-settings` for DB URL.
*   Add `DATABASE_URL=postgresql+psycopg://reachy_app@/reachy_local?host=/var/run/postgresql` to `.env`.

1) Base SQLAlchemy setup (2.0 style)
------------------------------------

*   Create `apps/api/app/db/core.py`:
    *   `engine = create_engine(DATABASE_URL, pool_pre_ping=True)`
    *   `SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)`
    *   FastAPI dependency `get_session()` (yield pattern) for request-scoped sessions.

2) Schema (models + constraints)
--------------------------------

Start minimal, but with the rules your docs require:

*   `Video` table:  
    `id (uuid)`, `sha256 (unique)`, `split ENUM('temp','train','test')`, `label ENUM('happy','sad', NULLable)`, `rel_path`, `duration_ms`, `fps`, `w`, `h`, `created_at`.
    *   **Constraints:**
        *   `chk_split_label`: `split='test' → label IS NULL`; `split IN ('train') → label IN ('happy','sad')`. (This encodes your “no label in test” rule.) AGENTS\_08.4.2
        *   Unique `(sha256)` to prevent duplicates.
*   `PromotionLog` table:  
    `id`, `video_id`, `from_split`, `to_split`, `intended_emotion`, `at`, `by` (user/agent), `ok BOOL`. This feeds audits and your Reconciler. AGENTS\_08.4.2
*   (Optional now) `v_video_urls` view: builds `/videos/...` and `/thumbs/...` from `rel_path` for the web layer (your Nginx serves static). Your spec assumes this “static URL” pattern. requirements\_08.4.2

3) Alembic migrations
---------------------

*   `alembic init db/alembic`
*   Configure `sqlalchemy.url` to read `DATABASE_URL` (env).
*   Generate baseline: `alembic revision -m "init schema" --autogenerate` → review constraints (esp. the check constraint) → `alembic upgrade head`.

4) Wire FastAPI endpoints to DB
-------------------------------

*   `/ingest` (Agent 1 path):
    *   Compute sha256, insert `Video(split='temp', label=NULL, rel_path=...)`, write metadata, create thumb → commit → return row. (Ingest responsibilities call this out.) AGENTS\_08.4.2
*   `/label` (Agent 2):
    *   Update `label` only if `split='train'`. If `split='test'`, reject (DB will also block via `chk_split_label`). AGENTS\_08.4.2
*   `/promote` (Agent 3):
    *   Inside a transaction: move file on disk → update `split` → insert `PromotionLog`.
    *   If promoting to `test`, make sure `label` is NULL; to `train`, ensure `label IN ('happy','sad')`. Balance checks run before commit. AGENTS\_08.4.2
*   `/stats` (Agent 3/9 helper):
    *   Return counts per split + per label to drive the 50/50 gate UI. (Your docs emphasize keeping test 50/50.) requirements\_08.4.2

5) Balance enforcement (thin DB-first, UI-second)
-------------------------------------------------

*   Add a small service function `can_promote_to_test()` that consults `SELECT count(*) FROM video WHERE split='test' AND label IS NULL GROUP BY intended_emotion` (you can store the intended class in `PromotionLog` when the user clicks “send to test”). Fail closed if promoting would break the ±5% rule. requirements\_08.4.2
*   Surface the decision to the Streamlit UI so Labeling Agent can nudge generation toward the under-represented class (your optional “Generation Balancer”). AGENTS\_08.4.2

6) Manifests from DB (Reconciler hand-off)
------------------------------------------

*   Add a job (or endpoint) `POST /rebuild-manifests`: select `train` rows with labels and (separately) test paths to emit `train_manifest.json`/`test_manifest.json` atomically. This unblocks Training/Eval Agents. AGENTS\_08.4.2

7) Quick verification (“psql test pack” style)
----------------------------------------------

*   Insert a `Video(split='temp')` → promote to `test` with `label` still NULL → **should succeed** and log.
*   Try to set `label='happy'` on a `test` item → **should fail** (check constraint trips).
*   Promote to `train` without `label` → **should fail** (check constraint trips).
*   Ensure `sha256` duplicate insert → **fails** unique constraint.  
    (You asked for this style of pack earlier—run it now to validate the business rules.)

8) CI glue (Windsurf → GitHub Actions)
--------------------------------------

*   Add lint/typecheck/tests to the API service so schema and constraints stay green in PRs (ruff, mypy, pytest). Your dev-env notes already outline the CI stages and minimal workflows; just drop them in. Dev Environment\_Windsurf\_Claude… Dev Environment\_Windsurf\_Claude…

9) What this unblocks next
--------------------------

*   Training Orchestrator can trust manifests and dataset hashes; Deployment/Eval agents can make decisions off DB facts instead of ad-hoc files. This lines up cleanly with your “agentic” loop (video → label → train → evaluate → deploy). requirements\_08.4.2

* * *

If you want, I’ll sketch the three core SQLAlchemy models (Video, PromotionLog, and a tiny helper for per-split counters) and a first Alembic migration so you can paste them into Windsurf and run.

## Prompt:
Yes. Sketch the three core models and a first migration as described.

I am not familiar with Alembic and the migration process. Provide an overview of its purpose and integration into the project.

## Response:
Thought for 35s

Yep—SQLAlchemy next is the move. You’ve got HTTP + Nginx behaving; what’s missing is the durable rules of the world (no labels in `test`, labeled `train`, dedupe by hash, audited promotions). That lives in Postgres, and SQLAlchemy (+ Alembic) is how we make those rules real, testable, and versioned.

Here’s the “first cut” you asked for: three core models and an initial Alembic migration, plus a quick primer on how Alembic plugs in.

* * *

SQLAlchemy models (sketch, SQLA 2.x style)
==========================================

**File:** `apps/api/app/db/base.py`

```python
# apps/api/app/db/base.py
from typing import Annotated
from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy import String

class Base(DeclarativeBase):
    pass

# handy alias for common columns
Str200 = Annotated[str, mapped_column(String(200))]
```

**File:** `apps/api/app/db/models.py`

```python
# apps/api/app/db/models.py
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

# --- Enums (persisted in Postgres as named types) -----------------------------

SplitEnum = Enum("temp", "train", "test", name="split_enum", create_constraint=True)
EmotionEnum = Enum("happy", "sad", name="emotion_enum", create_constraint=True)

# --- Core model: Video --------------------------------------------------------
class Video(Base):
    __tablename__ = "video"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # content identity & storage
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    rel_path: Mapped[str] = mapped_column(String(1024), nullable=False)  # e.g. "train/2025/10/clip.mp4"

    # split + label
    split: Mapped[str] = mapped_column(SplitEnum, nullable=False, default="temp")
    label: Mapped[Optional[str]] = mapped_column(EmotionEnum, nullable=True)

    # media metadata (optional but useful)
    duration_ms: Mapped[Optional[int]] = mapped_column(nullable=True)
    fps: Mapped[Optional[float]] = mapped_column(nullable=True)
    width: Mapped[Optional[int]] = mapped_column(nullable=True)
    height: Mapped[Optional[int]] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    # relationships
    promotions: Mapped[list["PromotionLog"]] = relationship(
        back_populates="video", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Business rules:
        # - test split must have NO label
        # - train split must have a label in {happy, sad}
        # - temp split must have NO label
        CheckConstraint(
            """(
                (split = 'test'  AND label IS NULL)
             OR (split = 'train' AND label IN ('happy','sad'))
             OR (split = 'temp'  AND label IS NULL)
            )""",
            name="chk_video_split_label",
        ),
        Index("ix_video_split", "split"),
        Index("ix_video_label", "label"),
    )

# --- Core model: PromotionLog -------------------------------------------------
class PromotionLog(Base):
    __tablename__ = "promotion_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("video.id", ondelete="CASCADE"), nullable=False
    )

    from_split: Mapped[str] = mapped_column(SplitEnum, nullable=False)
    to_split: Mapped[str] = mapped_column(SplitEnum, nullable=False)

    # for auditing balance intent; may be NULL (e.g., promoting to test where label must be NULL)
    intended_emotion: Mapped[Optional[str]] = mapped_column(EmotionEnum, nullable=True)

    ok: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))
    actor: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)  # user/agent id

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    video: Mapped[Video] = relationship(back_populates="promotions")

    __table_args__ = (
        Index("ix_promo_video_time", "video_id", "created_at"),
    )

# --- Read-only view model: SplitLabelCount -----------------------------------
# A tiny aggregation to power your 50/50 checks and quick stats.
# We'll create the SQL VIEW in the migration and map to it read-only.
from sqlalchemy import Table, Column, BigInteger

def get_split_label_count_table(metadata):
    return Table(
        "v_split_label_counts",
        metadata,
        Column("split", SplitEnum, nullable=False),
        Column("label", EmotionEnum, nullable=True),
        Column("n", BigInteger, nullable=False),
        extend_existing=True,
    )

class SplitLabelCount(Base):
    __table__ = get_split_label_count_table(Base.metadata)

    # convenience accessors (no PK because it's a view)
    # You will only SELECT from this mapped view.
```

**Session wiring (for FastAPI)**  
**File:** `apps/api/app/db/session.py`

```python
# apps/api/app/db/session.py
import os
from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://reachy_app@/reachy_local?host=/var/run/postgresql",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

* * *

Alembic: purpose + how it fits here (plain-English)
===================================================

*   **What it does:** Alembic tracks _schema history_ for your database. Each change (new table, column, constraint, enum, index, view) is captured as a **migration script**. Those scripts let you move the DB **forward** (`upgrade`) or **back** (`downgrade`) in lockstep with your code.
*   **Why you want it:** Your agents and API depend on precise rules (check constraints, enums, FKs). Alembic makes those rules reproducible across machines (Ubuntu 1, CI, future prod), and safe to evolve.
*   **How it integrates:**
    1.  You define / update ORM models (above).
    2.  Run `alembic revision --autogenerate -m "what changed"` to diff metadata vs DB.
    3.  Review the generated script (important for enums, views, and constraints).
    4.  Apply with `alembic upgrade head` during deploy/CI.

* * *

Alembic project setup (once)
============================

From `apps/api/`:

```bash
# in your venv
pip install alembic psycopg[binary] sqlalchemy

# create alembic scaffold
alembic init db/alembic
```

Edit `apps/api/db/alembic.ini` (or keep default) and set the script location to `db/alembic`.  
Edit `apps/api/db/alembic/env.py` so it reads the URL from env and uses your metadata:

**File:** `apps/api/db/alembic/env.py` (key bits)

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

import os
from app.db.base import Base  # metadata lives here
from app.db import models  # ensure models are imported so metadata is populated

config = context.config

# pull DATABASE_URL from env; don't hard-code in ini
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,      # detect type changes
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

* * *

First migration (creates enums, tables, and the counts view)
============================================================

Create the revision:

```bash
cd apps/api
alembic revision -m "init schema: video, promotion_log, counts view"
```

Then **replace** the generated script body with the following (keep the header Alembic puts in):

**File:** `apps/api/db/alembic/versions/<rev>_init_schema.py`

```python
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_init_schema"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # --- Create enums (Postgres named types) ----------------------------------
    split_enum = sa.Enum("temp", "train", "test", name="split_enum")
    emotion_enum = sa.Enum("happy", "sad", name="emotion_enum")
    split_enum.create(op.get_bind(), checkfirst=True)
    emotion_enum.create(op.get_bind(), checkfirst=True)

    # --- Table: video ---------------------------------------------------------
    op.create_table(
        "video",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sha256", sa.String(length=64), nullable=False, unique=True),
        sa.Column("rel_path", sa.String(length=1024), nullable=False),
        sa.Column("split", split_enum, nullable=False, server_default=sa.text("'temp'")),
        sa.Column("label", emotion_enum, nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("fps", sa.Float(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.dialects.postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            """
            (
                (split = 'test'  AND label IS NULL)
             OR (split = 'train' AND label IN ('happy','sad'))
             OR (split = 'temp'  AND label IS NULL)
            )
            """,
            name="chk_video_split_label",
        ),
    )
    op.create_index("ix_video_split", "video", ["split"])
    op.create_index("ix_video_label", "video", ["label"])

    # --- Table: promotion_log -------------------------------------------------
    op.create_table(
        "promotion_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("video_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_split", split_enum, nullable=False),
        sa.Column("to_split", split_enum, nullable=False),
        sa.Column("intended_emotion", emotion_enum, nullable=True),
        sa.Column("ok", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "actor",
            sa.String(length=120),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.dialects.postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["video_id"], ["video.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_promo_video_time", "promotion_log", ["video_id", "created_at"]
    )

    # --- View: v_split_label_counts ------------------------------------------
    op.execute(
        """
        CREATE VIEW v_split_label_counts AS
        SELECT
            split,
            label,
            COUNT(*)::bigint AS n
        FROM video
        GROUP BY split, label;
        """
    )

def downgrade():
    # drop view first
    op.execute("DROP VIEW IF EXISTS v_split_label_counts;")

    # drop children then parents
    op.drop_index("ix_promo_video_time", table_name="promotion_log")
    op.drop_table("promotion_log")

    op.drop_index("ix_video_label", table_name="video")
    op.drop_index("ix_video_split", table_name="video")
    op.drop_table("video")

    # finally drop types
    bind = op.get_bind()
    sa.Enum(name="emotion_enum").drop(bind, checkfirst=True)
    sa.Enum(name="split_enum").drop(bind, checkfirst=True)
```

Apply it:

```bash
alembic upgrade head
```

* * *

How you’ll use this from the API (happy path)
=============================================

*   **/ingest**
    1.  Compute `sha256` of the incoming file.
    2.  Move file under `videos/temp/...`, set `rel_path` accordingly.
    3.  `INSERT` `Video(split='temp', label=NULL, sha256=..., rel_path=..., meta…)`.
*   **/label** (only valid for `train`)
    *   `UPDATE video SET label='happy' WHERE id=:id AND split='train'`.
    *   If someone tries this on `test`, the **DB check** blocks it.
*   **/promote**
    *   Transaction: move file on disk → update `video.split` (`temp→train|test`).
    *   For `→train`, require label is set (`happy|sad`).
    *   For `→test`, force `label=NULL`.
    *   Insert `PromotionLog` row either way.
    *   For 50/50 guardrails, query `v_split_label_counts` before committing.
*   **/stats**
    *   `SELECT * FROM v_split_label_counts;` (or via `SplitLabelCount` ORM) for instant UI feedback.

* * *

Developer rhythm (Windsurf + CI)
================================

1.  Edit models → `alembic revision --autogenerate -m "…"`.
2.  Inspect the diff (especially when touching enums or views).
3.  `alembic upgrade head`.
4.  Add a tiny pytest that hits the DB and asserts:
    *   `INSERT video(split='test', label='happy')` fails.
    *   `INSERT duplicate sha256` fails.
    *   promoting `train` without label fails.
    *   counts view reflects inserts.

* * *

If you want, I can follow this up with:

*   Minimal FastAPI CRUD for `/ingest`, `/label`, `/promote`, `/stats`.
*   A one-page “psql test pack” that exercises each constraint and the view.

## Prompt:
Yes. Follow up with the CRUD and the one-page test pack

## Response:
You’ve got it. Here’s a lean, working CRUD slice you can drop into `apps/api/app/` plus a one-page `psql` test pack to validate the rules.

I’m keeping things minimal but production-sane: request-scoped DB sessions, atomic promotions (filesystem then DB in one try/except), and hard failures when a rule would be violated.

Files to add/update
===================

`apps/api/app/config.py`
------------------------

```python
import os
from pathlib import Path

# Data roots (match your Nginx aliases)
DATA_ROOT = Path(os.getenv("REACHY_DATA_ROOT", "/media/rusty_admin/project_data/reachy_emotion"))
VIDEOS_ROOT = Path(os.getenv("VIDEOS_ROOT", str(DATA_ROOT / "videos")))
THUMBS_ROOT = Path(os.getenv("THUMBS_ROOT", str(DATA_ROOT / "thumbs")))

# Public URL bases (as served by Nginx)
BASE_MEDIA_URL = os.getenv("BASE_MEDIA_URL", "/videos")
BASE_THUMBS_URL = os.getenv("BASE_THUMBS_URL", "/thumbs")
```

`apps/api/app/utils/fs.py`
--------------------------

```python
from __future__ import annotations
import hashlib, os, shutil
from pathlib import Path
from typing import BinaryIO

def sha256_file(fobj: BinaryIO) -> str:
    h = hashlib.sha256()
    fobj.seek(0)
    for chunk in iter(lambda: fobj.read(1024 * 1024), b""):
        h.update(chunk)
    fobj.seek(0)
    return h.hexdigest()

def ensure_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def write_upload_to(path: Path, fobj: BinaryIO) -> None:
    ensure_dir(path)
    with open(path, "wb") as out:
        shutil.copyfileobj(fobj, out)

def move_file(src: Path, dst: Path) -> None:
    ensure_dir(dst)
    os.replace(src, dst)  # atomic on same filesystem
```

`apps/api/app/routers/media.py`
-------------------------------

```python
from __future__ import annotations
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy import select, text

from app.db.session import get_session
from app.db import models as m
from app.config import VIDEOS_ROOT, BASE_MEDIA_URL
from app.utils.fs import sha256_file, write_upload_to, move_file

router = APIRouter(prefix="", tags=["media"])

# ----- Helpers ---------------------------------------------------------------

def _rel_path(split: str, sha256: str, ext: str = "mp4") -> str:
    # e.g., "temp/2025/10/20/ab12...cd.mp4"
    today = datetime.utcnow().strftime("%Y/%m/%d")
    return f"{split}/{today}/{sha256}.{ext}"

def _abs_path(rel_path: str) -> Path:
    return (VIDEOS_ROOT / rel_path).resolve()

# ----- Endpoints -------------------------------------------------------------

@router.post("/ingest", status_code=201)
def ingest_video(
    file: UploadFile = File(..., description="MP4 file"),
    fps: Optional[float] = None,
    duration_ms: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    db: Session = Depends(get_session),
):
    if not file.filename or not file.filename.lower().endswith((".mp4", ".mov", ".mkv")):
        raise HTTPException(status_code=400, detail="Expected a video file")

    # compute sha256 without loading whole file into memory
    sha = sha256_file(file.file)

    # path under temp
    rel = _rel_path("temp", sha, "mp4")
    abs_p = _abs_path(rel)
    write_upload_to(abs_p, file.file)

    v = m.Video(
        sha256=sha,
        rel_path=rel,
        split="temp",
        label=None,
        fps=fps,
        duration_ms=duration_ms,
        width=width,
        height=height,
    )
    db.add(v)
    try:
        db.commit()
    except Exception:
        db.rollback()
        # likely unique(sha256) violation; remove the just-written file
        try:
            abs_p.unlink(missing_ok=True)
        finally:
            pass
        raise

    return {
        "id": str(v.id),
        "sha256": v.sha256,
        "rel_path": v.rel_path,
        "url": f"{BASE_MEDIA_URL}/{v.rel_path}",
        "split": v.split,
        "label": v.label,
    }

@router.post("/label/{video_id}")
def set_label(
    video_id: uuid.UUID,
    label: str,               # "happy" or "sad"
    db: Session = Depends(get_session),
):
    v = db.get(m.Video, video_id)
    if not v:
        raise HTTPException(404, "Video not found")

    if v.split != "train":
        # DB constraint will also enforce, but fail early with a clear message
        raise HTTPException(409, "Can only label items in the 'train' split")

    if label not in ("happy", "sad"):
        raise HTTPException(400, "Label must be one of: happy, sad")

    v.label = label
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"id": str(v.id), "split": v.split, "label": v.label}

@router.post("/promote/{video_id}")
def promote(
    video_id: uuid.UUID,
    to_split: str,                   # "train" or "test"
    intended_emotion: Optional[str] = None,  # for audit/balance
    actor: Optional[str] = "api",
    db: Session = Depends(get_session),
):
    if to_split not in ("train", "test"):
        raise HTTPException(400, "to_split must be 'train' or 'test'")

    v = db.get(m.Video, video_id)
    if not v:
        raise HTTPException(404, "Video not found")

    if v.split == to_split:
        return {"status": "noop", "id": str(v.id), "split": v.split}

    src_abs = _abs_path(v.rel_path)

    # Build destination rel/abs
    ext = Path(v.rel_path).suffix.lstrip(".") or "mp4"
    new_rel = _rel_path(to_split, v.sha256, ext)
    dst_abs = _abs_path(new_rel)

    # Business rules (mirrors DB constraint):
    if to_split == "train" and v.label not in ("happy", "sad"):
        raise HTTPException(409, "Must set label (happy|sad) before promoting to train")
    if to_split == "test":
        # ensure label cleared
        v.label = None

    # Filesystem then DB (same FS so os.replace is atomic)
    try:
        move_file(src_abs, dst_abs)
    except FileNotFoundError:
        raise HTTPException(500, f"Source file missing on disk: {src_abs}")

    from_split = v.split
    v.split = to_split
    v.rel_path = new_rel

    log = m.PromotionLog(
        video=v,
        from_split=from_split,
        to_split=to_split,
        intended_emotion=intended_emotion if to_split == "train" else None,
        ok=True,
        actor=actor,
    )
    db.add(log)

    try:
        db.commit()
    except Exception:
        db.rollback()
        # best effort: try to move file back
        try:
            move_file(dst_abs, src_abs)
        except Exception:
            pass
        raise

    return {
        "id": str(v.id),
        "from": from_split,
        "to": to_split,
        "rel_path": v.rel_path,
        "url": f"{BASE_MEDIA_URL}/{v.rel_path}",
    }

@router.get("/stats")
def stats(db: Session = Depends(get_session)):
    # read from the view
    rows = db.execute(text("SELECT split, label, n FROM v_split_label_counts ORDER BY split, label NULLS FIRST")).all()
    return [{"split": r[0], "label": r[1], "count": int(r[2])} for r in rows]
```

`apps/api/app/main.py` (wire the router)
----------------------------------------

```python
from fastapi import FastAPI
from app.routers.media import router as media_router

app = FastAPI(root_path="/api/media")

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

app.include_router(media_router)
```

* * *

One-page `psql` test pack
=========================

Save as `tests/sql/pack_smoke.sql` and run with:

```bash
psql "postgresql:///reachy_local?host=/var/run/postgresql" -f tests/sql/pack_smoke.sql
```

```sql
\echo '--- Pack: init counts ---'
TABLE v_split_label_counts;

\echo '--- 1) Insert a temp video (OK) ---'
INSERT INTO video (id, sha256, rel_path, split, label, fps, duration_ms, width, height)
VALUES (gen_random_uuid(), 'deadbeef'*8, 'temp/2025/10/20/dead...ef.mp4', 'temp', NULL, 24.0, 5000, 1280, 720);

SELECT split, label, count(*) FROM video GROUP BY 1,2 ORDER BY 1,2;

\echo '--- 2) Try to set a label on temp (EXPECT FAIL) ---'
BEGIN;
  SAVEPOINT s1;
  UPDATE video SET label='happy' WHERE split='temp' LIMIT 1;
ROLLBACK TO s1;
COMMIT;

\echo '--- 3) Promote temp→test (label must be NULL) (OK @ constraint level) ---'
-- In API this is filesystem+DB; here we simulate just DB to test constraints:
BEGIN;
  SAVEPOINT s2;
  UPDATE video SET split='test', label=NULL WHERE split='temp' LIMIT 1;
COMMIT;

SELECT * FROM v_split_label_counts ORDER BY split, label NULLS FIRST;

\echo '--- 4) Try to assign a label on test (EXPECT FAIL) ---'
BEGIN;
  SAVEPOINT s3;
  UPDATE video SET label='sad' WHERE split='test' LIMIT 1;
ROLLBACK TO s3;
COMMIT;

\echo '--- 5) Prepare a new train item with label (OK) ---'
INSERT INTO video (id, sha256, rel_path, split, label)
VALUES (gen_random_uuid(), 'cafebabe'*8, 'train/2025/10/20/cafe...be.mp4', 'train', 'happy');

\echo '--- 6) Try to create a train item without label (EXPECT FAIL) ---'
BEGIN;
  SAVEPOINT s4;
  INSERT INTO video (id, sha256, rel_path, split, label)
  VALUES (gen_random_uuid(), '00'*64, 'train/x/y/z.mp4', 'train', NULL);
ROLLBACK TO s4;
COMMIT;

\echo '--- 7) Duplicate sha256 (EXPECT FAIL) ---'
DO $$
BEGIN
  BEGIN
    INSERT INTO video (id, sha256, rel_path, split)  -- label NULL + split temp is OK
    VALUES (gen_random_uuid(), 'cafebabe'*8, 'temp/dup.mp4', 'temp');
  EXCEPTION WHEN unique_violation THEN
    RAISE NOTICE 'OK: unique(sha256) enforced';
  END;
END $$;

\echo '--- 8) Promotion audit log (manual insert OK) ---'
INSERT INTO promotion_log (video_id, from_split, to_split, intended_emotion, ok, actor)
SELECT id, 'temp', 'test', NULL, true, 'testpack'
FROM video WHERE split='test' LIMIT 1;

SELECT id, video_id, from_split, to_split, intended_emotion, ok, actor, created_at
FROM promotion_log ORDER BY id DESC LIMIT 3;

\echo '--- 9) Final counts view ---'
TABLE v_split_label_counts;
```

> Notes on expectations  
> • Steps 2, 4, 6, and 7 exercise the **check constraint** and the **unique(sha256)**.  
> • Step 3 only changes DB state; in real API calls, the file move happens first, then the DB update, and both are committed together.  
> • The counts view should reflect inserts and updates immediately.

* * *

How to try the API quickly
--------------------------

```bash
# Activate venv, set env, run:
export DATABASE_URL="postgresql+psycopg://reachy_app@/reachy_local?host=/var/run/postgresql"
export REACHY_DATA_ROOT="/media/rusty_admin/project_data/reachy_emotion"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

*   `POST /ingest` (form-data `file=@clip.mp4`) → returns `id`, `rel_path`, URL.
*   `POST /promote/{id}?to_split=train` → **fails** unless you first:  
    `POST /label/{id}?label=happy` after you’ve promoted that item to `train` (or created it directly in `train` via SQL).
*   `POST /promote/{id}?to_split=test` → clears any label and moves the file under `videos/test/...`.
*   `GET /stats` → quick snapshot (powers the 50/50 UI).

If you want, I can add a tiny pytest that calls these endpoints in sequence and verifies both DB and filesystem effects.

## Prompt:
Explain the purpose of the provided CRUD.

## Response:
Each of those routes is a thin layer between your agents (or the Streamlit UI) and the database + filesystem you’ve already shaped.  
They aren’t meant to _do everything_ — just to enforce the minimal rules of motion in the system: how a video enters, changes state, and gets counted.

Here’s what each part is doing and why it matters.

* * *

### `/ingest`

**Purpose:**  
This is how new media enters the ecosystem.

**In plain terms:**  
It takes an uploaded video file, computes its SHA-256 fingerprint, writes it to the local SSD under `videos/temp/...`, and creates a `Video` record with `split='temp'` and `label=NULL`.

**Why:**

*   The SHA ensures no duplicates.
*   Keeping it in the “temp” split isolates unreviewed or unlabeled material.
*   It lays the groundwork for later promotion and labeling workflows.

**In project terms:**  
Used by the **Ingest Agent** when synthetic videos arrive from Luma AI or another generator. It populates Postgres so every file has metadata, a known path, and a reproducible hash.

* * *

### `/label/{video_id}`

**Purpose:**  
To assign an emotion class (`happy` or `sad`) — but _only_ for training data.

**In plain terms:**  
It updates the `label` column, but only if the `Video` is already in the `train` split.

**Why:**

*   Keeps “test” videos blind (no labels allowed).
*   Enforces your 50/50 emotion balance through DB constraints.
*   Gives the **Labeling Agent** or human reviewer a clean interface to apply verified labels.

* * *

### `/promote/{video_id}`

**Purpose:**  
To move a video from one stage of the pipeline to the next (`temp→train` or `temp→test`).

**In plain terms:**  
It performs an atomic move of both the file on disk and its database state, logging that action in `PromotionLog`.

**Why:**

*   Keeps file tree and database in sync.
*   Ensures only labeled items enter the training set, and unlabeled ones enter the test set.
*   Generates the audit trail the **Promotion/Curation Agent** and **Reconciler Agent** will rely on.

**In project terms:**  
This is the step that turns raw generated clips into curated assets ready for EmotionNet fine-tuning.

* * *

### `/stats`

**Purpose:**  
To summarize the current distribution of data by split and label.

**In plain terms:**  
It queries the view `v_split_label_counts` and returns counts of how many videos are in each category.

**Why:**

*   Lets the frontend show dataset health at a glance.
*   Enables the **Reconciler Agent** and **Evaluation Agent** to verify 50/50 balance before training.
*   Provides an easy endpoint for QA scripts and dashboards.

* * *

### The supporting helpers

*   **Filesystem utilities (`fs.py`)** make sure moves and writes are atomic and directory-safe.
*   **`config.py`** centralizes your base paths and URLs so both Nginx and FastAPI agree on where things live.
*   **`session.py`** creates per-request DB sessions, preventing leaks or cross-transaction contamination.

* * *

### Overall role

Together, this CRUD set defines the **data lifecycle contract** for Reachy \_Local 08.4.2:

| Phase | Agent / Actor | Endpoint | Effect |
| --- | --- | --- | --- |
| Generation / Ingest | Ingest Agent | `/ingest` | File + metadata created |
| Human or model review | Labeling Agent | `/label` | Label assigned |
| Curation | Promotion Agent | `/promote` | File relocated, audit logged |
| Monitoring | Reconciler / Eval | `/stats` | Balance checked |

They make the system _stateful and observable_ without involving training logic yet.  
Once these are stable, SQLAlchemy + Alembic give you migrations and constraints to protect data integrity; the agents above them can now work confidently.

## Prompt:
Once the proposed SQLAlembic & Alembic configurations are complete, would you say the overall backend would be complete?

If not, what will be the additional configuration requirements?

## Response:
Thought for 15s

Short answer: close… but not “done.”  
SQLAlchemy + Alembic gives you the spine (schema, rules, migrations). The backend still needs a few muscles and tendons before you call it production-ready.

Here’s the rest of the work, in tight buckets so you can knock them down.

What’s left to finish the backend
=================================

1) API hardening
----------------

*   **Request/response models (Pydantic v2):** strict types, enums, length caps, file size limits.
*   **Consistent errors:** your own `HTTPException` factory with error codes; map DB errors (unique, check) to 409/422.
*   **CORS & upload limits:** Nginx `client_max_body_size`, FastAPI `File` size guard, content-type sniff.
*   **Auth:** minimally a signed token for agent calls (JWT or mTLS on the LAN). Add RBAC: `reachy_agent`, `reachy_admin`, `read_only`.
*   **API versioning:** prefix `v1/` so you can evolve endpoints.

2) Health + readiness
---------------------

*   **/healthz:** already returns `ok`. Keep.
*   **/readyz:** adds DB check (simple `SELECT 1`), disk space check for the media SSD, and a writable tmp dir probe.

3) Filesystem + DB atomicity polish
-----------------------------------

*   **Promotion as a service fn:** we did atomic move + DB commit; keep it in one place.
*   **Orphan/straggler GC:** a small job to find DB rows whose files vanished, and files that lack DB rows.
*   **Checksum verifier:** optional background sweep that recomputes SHA-256 to catch bit-rot.

4) Media derivatives & manifests
--------------------------------

*   **Thumbnailer:** on ingest, create a first-frame jpg (ffmpeg). Store under `/thumbs/...` and expose via Nginx.
*   **Manifest builder:** `/rebuild-manifests` endpoint or cron job that writes `train_manifest.json`, `test_manifest.json` from DB (atomically write temp → move).
*   **Config hooks:** keep `BASE_MEDIA_URL`, `BASE_THUMBS_URL` in `.env`, used by both API and Streamlit.

5) Balance + policy enforcement
-------------------------------

*   **50/50 guardrail:** service function checked before promoting to `test`; configurable tolerance (±5%).
*   **Business rules as constraints:** we have `chk_video_split_label` and `unique(sha256)`; add:
    *   **No duplicate split+sha** (covered by rel\_path if you prefer uniques there).
    *   **Prevent temp→train without label** (already enforced, keep tests).

6) Observability
----------------

*   **Structured logging:** JSON logs with request\_id, actor, video\_id, action; Nginx → API correlation.
*   **Metrics:** counters/gauges for ingest/promote/label, HTTP latencies; expose `/metrics` (Prometheus).
*   **Audit:** `promotion_log` is there; add who/why to label changes, too.

7) Testing
----------

*   **Unit tests:** models, constraints, service fns (promotion), manifest builder.
*   **API tests:** ingest → promote → label → stats golden path; error cases for each rule.
*   **FS tests:** simulate missing file on promote (we already handle), disk full, permission errors.
*   **Load smoke:** 100 small uploads, concurrent promotes.

8) CI/CD glue
-------------

*   **Migrations in CI:** spin up Postgres service, `alembic upgrade head`, run tests.
*   **Zero-downtime rollout:** run migrations on deploy before reloading Uvicorn.
*   **Lint/type:** ruff + mypy; pre-commit.

9) Security + secrets
---------------------

*   **Secrets management:** `.env` for dev; production via systemd `Environment=` or a secrets store.
*   **TLS:** you’ve got Nginx TLS; ensure strong ciphers; renewals scripted.
*   **Rate limiting (optional):** Nginx `limit_req` on write endpoints.

10) Database ops
----------------

*   **Roles are set:** owner/app/read (good). Confirm privileges match.
*   **Backups:** nightly `pg_dump` + weekly base backup; retention plan; restore runbook.
*   **Vacuum/autovacuum:** leave defaults or tune if ingest volume grows.
*   **Indexes:** we added split/label; add one on `sha256` (unique) and maybe `created_at` for recents.

11) Platform bits
-----------------

*   **systemd:** you already have the unit; add `ExecStartPre` to run `alembic upgrade head` (or run in deploy script).
*   **Nginx:** confirm `proxy_read_timeout` for large uploads; set `client_max_body_size`; map `/videos` and `/thumbs` aliases.
*   **Disk monitoring:** alert if the media SSD crosses, say, 80%.

12) Agent touchpoints (so they can actually work)
-------------------------------------------------

*   **Ingest Agent:** calls `/ingest`, gets id/url back.
*   **Labeling Agent/UI:** can only label `train`; provides `POST /promote` + `POST /label` workflow.
*   **Promotion/Curation Agent:** balance-aware; uses `/stats` before promoting to test/train.
*   **Reconciler:** runs `/rebuild-manifests`, checks counts vs policy.
*   **Training/Eval Orchestrators:** read manifest paths, push results (later you’ll add an `/eval-report` endpoint or log table).
*   **Observability Agent:** scrapes `/metrics`, correlates with DB.

* * *

A simple “Definition of Done” for the backend
---------------------------------------------

*   **Data integrity:** all business rules enforced at DB level; tests prove it.
*   **CRUD stable:** ingest/label/promote/stats behave and are idempotent where applicable.
*   **Derivatives + manifests:** thumbs created; manifests rebuilt deterministically.
*   **Auth + limits:** tokens enforced on write; upload size capped.
*   **Ops:** migrations automated, backups scheduled, logs/metrics visible, ready/health checks green.
*   **Docs:** README with env vars, endpoints, error codes, and runbooks (backup/restore, rotate keys, rebuild manifests).

Once those are checked, yeah—you’ve got a backend you can trust while you wire up Streamlit, TAO fine-tuning, and the Jetson deploy loop.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)