# Postgres video URL & metadata setup

**User:** Anonymous (rustybee255@gmail.com)  
**Created:** 10/9/2025 14:13:00  
**Updated:** 10/21/2025 20:21:51  
**Exported:** 10/21/2025 20:23:12  
**Link:** [https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e7fb2a-d130-8324-ab35-701c4946c6d5](https://chatgpt.com/g/g-p-687d178cc6b481919c71aa820f0163ba-reachy-app/c/68e7fb2a-d130-8324-ab35-701c4946c6d5)  

## Prompt:
Consider the chat titled 'Postgres config for Reachy_Local.'

Remember Postgres will store the metadata for each video and the URL used to locate the video on the local storage device.
I don't see any reference to this process or an explanation of how it will be implemented. 

Explain the process in detail and the implementation.

## Response:
Thought for 1m 34s

You’re right to press here. The “how” is three parts working together: (1) a **Postgres schema** that treats the DB as the source of truth for labels/splits and stores a path to the clip, (2) a **filesystem layout** that never changes its root, and (3) a tiny **Media Mover API** that atomically moves files and keeps DB + manifests in lock-step.

I’ll lay out the end-to-end flow first, then show the practical implementation (DDL, Alembic, SQLAlchemy, and FastAPI endpoints).

1) The flow at a glance
=======================

1.  **Ingest (temp)**
    *   New clip lands on Ubuntu 1 under `/videos/temp/…`.
*   We compute `sha256`, `size_bytes`, probe media (fps, dims), render a thumbnail, and insert one `video` row with a **relative** file path like `videos/temp/clip_123.mp4`. DB keeps _relative_ paths by design. requirements\_08.3.3
    2.  **Label in the web app**
    *   The UI writes `label` for that `video_id` (no file move yet). DB remains the source of truth for label/split status. requirements\_08.3.3
    3.  **Promote to train/test**
    *   Clicking “Promote” calls `POST /api/promote { video_id, dest_split }`.
*   The service atomically moves the file on disk (`temp → train` or `test`), updates the row’s `split` and `file_path`, and (optionally) triggers `manifest/rebuild`. All metadata writes use idempotency keys. requirements\_08.3.3 requirements\_08.3.3 requirements\_08.3.3
    4.  **Serve to UI & tools**
    *   Nginx serves media directly for speed; the UI payload carries `video_url` (relative) and `thumb_url`. Example: `"/videos/temp/clip_00123.mp4"`, `"/thumbs/clip_00123.jpg"`. requirements\_08.3.3 requirements\_08.3.3
    5.  **Training linkage**
    *   Rebuilt JSONL manifests under `/videos/manifests/` reflect current DB labels/splits and feed TAO/DeepStream pipelines; MLflow links runs to a `dataset_hash`. requirements\_08.3.3

> Principle that makes this work: **DB is the source of truth** for labels/splits; manifests are **derived** from DB + filesystem. requirements\_08.3.3

2) The data model (Postgres)
============================

**Table:** `video` (one row per clip).

*   `video_id UUID PK`
*   `file_path TEXT` — **relative** path under `videos/…` (never absolute)
*   `split TEXT CHECK IN ('temp','train','test')`
*   `label TEXT` (e.g., happy/sad/…)
*   media probe fields (`duration_sec`, `fps`, `width`, `height`), integrity (`sha256`, `size_bytes`), bookkeeping timestamps.
*   Dedup safety: unique on `(sha256, size_bytes)`. requirements\_08.3.3 requirements\_08.3.3

```sql
-- 15. Database Schema (Metadata)
CREATE TABLE video (
  video_id     UUID PRIMARY KEY,
  file_path    TEXT NOT NULL,  -- relative under videos/
  split        TEXT CHECK (split IN ('temp','train','test')) NOT NULL,
  label        TEXT,
  duration_sec NUMERIC,
  fps          NUMERIC,
  width        INT,
  height       INT,
  size_bytes   BIGINT,
  sha256       TEXT,
  zfs_snapshot TEXT,
  created_at   TIMESTAMPTZ DEFAULT now(),
  updated_at   TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX uq_video_sha ON video(sha256, size_bytes);
```

> Reason for **relative** `file_path`: we can rename or remount the top-level storage root without rewriting millions of rows; URLs are then trivially `"/" + file_path`. The spec calls out using relative paths explicitly. requirements\_08.3.3

3) Filesystem + URLs + Nginx
============================

*   Canonical layout (Ubuntu 1): `/videos/{temp,train,test,thumbs,manifests}`. requirements\_08.3.3
*   UI payload fields: `video_url`, `thumb_url` (relative). requirements\_08.3.3
*   Media is served directly via Nginx for efficiency; the app doesn’t stream bytes. requirements\_08.3.3

Minimal Nginx location blocks (conceptually):

```nginx
location /videos/  { alias /videos/;  autoindex off; types { video/mp4 mp4; } }
location /thumbs/  { alias /videos/thumbs/;  add_header Cache-Control "public, max-age=3600"; }
```

4) API surface (Media Mover & friends)
======================================

The spec already names the exact endpoints we need to back this: list, detail, thumb, promote, relabel, and manifest rebuild; mutating calls require Bearer/JWT and idempotency keys. requirements\_08.3.3 requirements\_08.3.3 requirements\_08.3.3

*   `GET /api/videos/list?split=temp|train|test` → page through minimal fields for tables.
*   `GET /api/videos/{video_id}` → full metadata.
*   `GET /api/videos/{video_id}/thumb` → redirect/file from `/thumbs/{video_id}.jpg`.
*   `POST /api/relabel { video_id, label }` → update label only.
*   `POST /api/promote { video_id, dest_split, dry_run? }` → atomic move + DB update; `dry_run=true` returns the plan without side effects.
*   `POST /api/manifest/rebuild` → regenerate JSONL and return `dataset_hash`. requirements\_08.3.3

5) Implementation sketch (Alembic + SQLAlchemy + FastAPI)
=========================================================

**Alembic migration** (first cut):

```py
# versions/20251006_init_video.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20251006_init_video"
down_revision = None

def upgrade():
    op.create_table(
        "video",
        sa.Column("video_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("file_path", sa.Text(), nullable=False),  # relative under videos/
        sa.Column("split", sa.Text(), nullable=False),
        sa.Column("label", sa.Text()),
        sa.Column("duration_sec", sa.Numeric()),
        sa.Column("fps", sa.Numeric()),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("size_bytes", sa.BigInteger()),
        sa.Column("sha256", sa.Text()),
        sa.Column("zfs_snapshot", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint("split in ('temp','train','test')", name="ck_video_split"),
    )
    op.create_unique_constraint("uq_video_sha", "video", ["sha256", "size_bytes"])

def downgrade():
    op.drop_constraint("uq_video_sha", "video", type_="unique")
    op.drop_table("video")
```

**SQLAlchemy model** (2.0 style):

```py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import CheckConstraint, text
from uuid import uuid4, UUID

class Base(DeclarativeBase): pass

class Video(Base):
    __tablename__ = "video"
    __table_args__ = (CheckConstraint("split in ('temp','train','test')", name="ck_video_split"),)

    video_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    file_path: Mapped[str]
    split:     Mapped[str]  # 'temp' | 'train' | 'test'
    label:     Mapped[str | None]
    duration_sec: Mapped[float | None]
    fps:          Mapped[float | None]
    width:        Mapped[int  | None]
    height:       Mapped[int  | None]
    size_bytes:   Mapped[int  | None]
    sha256:       Mapped[str  | None]
    zfs_snapshot: Mapped[str  | None]
    created_at:   Mapped[str] = mapped_column(server_default=text("now()"))
    updated_at:   Mapped[str] = mapped_column(server_default=text("now()"))
```

**FastAPI endpoints (core bits):**

```py
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from pathlib import Path
import os, shutil
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

VIDEOS_ROOT = Path(os.getenv("VIDEOS_ROOT", "/videos"))

def file_url(file_path: str) -> str:
    # file_path is 'videos/<split>/<name>.mp4'
    return "/" + file_path

def thumb_url(video_id: str) -> str:
    return f"/thumbs/{video_id}.jpg"

class PromoteIn(BaseModel):
    video_id: str
    dest_split: str  # 'train' or 'test'
    dry_run: bool = False

@app.get("/api/videos/list")
async def list_videos(split: str, limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    q = select(Video).where(Video.split == split).order_by(Video.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "video_id": str(v.video_id),
            "file_path": v.file_path,
            "video_url": file_url(v.file_path),
            "thumb_url": thumb_url(str(v.video_id)),
            "size_bytes": v.size_bytes,
            "created_at": v.created_at,
            "label": v.label,
        } for v in rows
    ]

@app.post("/api/relabel")
async def relabel(video_id: str, label: str, db: AsyncSession = Depends(get_db), auth=Depends(require_jwt)):
    v = await db.get(Video, video_id)
    if not v: raise HTTPException(404, "not found")
    v.label = label
    await db.commit()
    return {"ok": True}

@app.post("/api/promote")
async def promote(p: PromoteIn, db: AsyncSession = Depends(get_db),
                  idem: str | None = Header(default=None, alias="Idempotency-Key"),
                  auth=Depends(require_jwt)):
    if p.dest_split not in ("train", "test"):
        raise HTTPException(400, "dest_split must be train or test")

    v = await db.get(Video, p.video_id)
    if not v: raise HTTPException(404, "not found")
    # Compute source/dest paths on disk
    src = VIDEOS_ROOT / Path(v.file_path).relative_to("videos")
    dest_rel = Path("videos") / p.dest_split / Path(v.file_path).name
    dest = VIDEOS_ROOT / dest_rel.relative_to("videos")

    plan = {"move": {"from": str(src), "to": str(dest)}, "db": {"split": p.dest_split, "file_path": str(dest_rel)}}
    if p.dry_run:
        return {"dry_run": True, "plan": plan}

    # Atomic move within same filesystem
    dest.parent.mkdir(parents=True, exist_ok=True)
    os.replace(src, dest)

    # Update DB
    v.split = p.dest_split
    v.file_path = str(dest_rel)
    await db.commit()

    # Optionally trigger manifest rebuild (sync or async)
    enqueue_manifest_rebuild()

    return {"ok": True, "video_url": file_url(v.file_path), "thumb_url": thumb_url(str(v.video_id))}
```

**Notes that line up with the spec**

*   Endpoints & semantics (list, thumb, promote, relabel, manifest/rebuild). requirements\_08.3.3
*   `dry_run` promotion support and atomic moves on the same filesystem. requirements\_08.3.3
*   Mutations require Bearer/JWT; writes use `Idempotency-Key`. requirements\_08.3.3 requirements\_08.3.3
*   Thumbnails live in `/videos/thumbs/{video_id}.jpg`. requirements\_08.3.3

6) Manifests + MLflow linkage
=============================

*   `POST /api/manifest/rebuild` walks the DB for `split in ('train','test')`, writes JSONL rows under `/videos/manifests/`, and returns a `dataset_hash`. Training pipelines consume these manifests, and MLflow tracks that `dataset_hash` for each run. requirements\_08.3.3

7) Operations & guardrails that keep it sane
============================================

*   **Dedup:** unique `(sha256, size_bytes)` prevents accidental duplicates. requirements\_08.3.3
*   **Integrity:** nightly reconciler compares DB vs. FS; promotion log stays append-only; TTL purges old `temp/`. requirements\_08.3.3
*   **Security:** mutate endpoints use JWT; DB access is least-privilege; API hardening is in place. requirements\_08.3.3 requirements\_08.3.3
*   **Networking:** Ubuntu 2 talks to Ubuntu 1 for Postgres (`:5432`), Media Mover, and media via Nginx; Jetson never streams raw video off-device. requirements\_08.3.3

* * *

What this gives you
-------------------

*   **Single source of truth** (DB) for labels/splits with relative paths, so storage can move without a migration. requirements\_08.3.3 requirements\_08.3.3
*   **Simple URLs** for the UI (`/videos/...`, `/thumbs/...`) backed by Nginx. requirements\_08.3.3
*   **Safe promotions** that keep DB, filesystem, and manifests consistent, with `dry_run` and idempotency. requirements\_08.3.3 requirements\_08.3.3

If you want, I can turn the snippets above into a ready-to-drop `apps/api/` module (models, CRUD, routes, Alembic migration) wired to your current env vars and service layout.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)