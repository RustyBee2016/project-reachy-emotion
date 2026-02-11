# Hands-On Exercises & Lab Guide

This document contains all hands-on exercises consolidated from the curriculum modules.

---

## Prerequisites

Before starting, ensure you have:

```bash
# PostgreSQL running
sudo systemctl status postgresql

# Database created
psql -U reachy_app -d reachy_local -c "SELECT 1;"

# Alembic migrations applied
alembic -c apps/api/app/db/alembic/alembic.ini upgrade head

# Verify tables exist (should show video, training_run, training_selection, promotion_log, alembic_version)
psql -U reachy_app -d reachy_local -c "\dt"
```

---

## Lab 1: SQL Basics (Module 1)

### Setup
```sql
-- Connect to database
psql -U reachy_app -d reachy_local

-- Insert test videos
INSERT INTO video (file_path, split, size_bytes) VALUES
    ('videos/lab1/001.mp4', 'temp', 1024000),
    ('videos/lab1/002.mp4', 'temp', 2048000),
    ('videos/lab1/003.mp4', 'temp', 512000);
```

### Exercises

**1.1** Select all videos and display file_path and size:
```sql
-- Your answer:

```

**1.2** Count how many videos are in 'temp' split:
```sql
-- Your answer:

```

**1.3** Update one video to have label='happy' and split='dataset_all':
```sql
-- Your answer:

```

**1.4** Try to set split='dataset_all' without a label (should fail):
```sql
-- Your answer:

```

### Cleanup
```sql
DELETE FROM video WHERE file_path LIKE 'videos/lab1/%';
```

<details>
<summary>Solutions</summary>

```sql
-- 1.1
SELECT file_path, size_bytes FROM video WHERE file_path LIKE 'videos/lab1/%';

-- 1.2
SELECT COUNT(*) FROM video WHERE split = 'temp';

-- 1.3
UPDATE video SET split = 'dataset_all', label = 'happy'
WHERE file_path = 'videos/lab1/001.mp4';

-- 1.4 (Will fail with constraint violation)
UPDATE video SET split = 'dataset_all'
WHERE file_path = 'videos/lab1/002.mp4';
-- ERROR: violates check constraint "chk_video_split_label_policy"
```
</details>

---

## Lab 2: PostgreSQL Features (Module 2)

### Setup
```sql
INSERT INTO video (file_path, split, size_bytes, metadata) VALUES
    ('videos/lab2/001.mp4', 'temp', 1000000,
     '{"source": "jetson", "camera": "front"}'),
    ('videos/lab2/002.mp4', 'temp', 2000000,
     '{"source": "upload", "user": "alice"}');
```

### Exercises

**2.1** List all enum values for video_split:
```sql
-- Your answer:

```

**2.2** Query videos where metadata source is 'jetson':
```sql
-- Your answer:

```

**2.3** Add a new key to metadata using JSONB update:
```sql
-- Your answer:

```

**2.4** Check the execution plan for a query on split:
```sql
-- Your answer:

```

### Cleanup
```sql
DELETE FROM video WHERE file_path LIKE 'videos/lab2/%';
```

<details>
<summary>Solutions</summary>

```sql
-- 2.1
SELECT enum_range(NULL::video_split);

-- 2.2
SELECT file_path, metadata
FROM video
WHERE metadata->>'source' = 'jetson';

-- 2.3
UPDATE video
SET metadata = metadata || '{"processed": true}'::jsonb
WHERE file_path = 'videos/lab2/001.mp4';

-- 2.4
EXPLAIN ANALYZE SELECT * FROM video WHERE split = 'temp';
```
</details>

---

## Lab 3: Schema Exploration (Module 3)

### Exercises

**3.1** Count videos in each split:
```sql
-- Your answer:

```

**3.2** Find the total size of all videos in dataset_all (in MB):
```sql
-- Your answer:

```

**3.3** Join training_selection with video to show file paths for a run:
```sql
-- Your answer:

```

**3.4** Find videos that have never been used in any training run:
```sql
-- Your answer:

```

<details>
<summary>Solutions</summary>

```sql
-- 3.1
SELECT split, COUNT(*) as count
FROM video
GROUP BY split
ORDER BY split;

-- 3.2
SELECT ROUND(SUM(size_bytes) / 1048576.0, 2) as total_mb
FROM video
WHERE split = 'dataset_all';

-- 3.3 (replace RUN_ID with actual UUID)
SELECT v.file_path, v.label, ts.target_split
FROM training_selection ts
JOIN video v ON ts.video_id = v.video_id
WHERE ts.run_id = 'RUN_ID';

-- 3.4
SELECT v.file_path
FROM video v
LEFT JOIN training_selection ts ON v.video_id = ts.video_id
WHERE ts.video_id IS NULL;
```
</details>

---

## Lab 4: Stored Procedures (Module 4)

### Setup
```sql
-- Insert labeled videos for testing
INSERT INTO video (file_path, split, label, size_bytes, duration_sec) VALUES
    ('videos/lab4/happy_001.mp4', 'dataset_all', 'happy', 1000000, 5.0),
    ('videos/lab4/happy_002.mp4', 'dataset_all', 'happy', 1500000, 6.0),
    ('videos/lab4/sad_001.mp4', 'dataset_all', 'sad', 1200000, 5.5),
    ('videos/lab4/temp_001.mp4', 'temp', NULL, 800000, 4.0);
```

### Exercises

**4.1** Call get_class_distribution for dataset_all:
```sql
-- Your answer:

```

**4.2** Check if dataset is balanced (min 2 samples, max ratio 2.0):
```sql
-- Your answer:

```

**4.3** Promote the temp video with dry_run=TRUE:
```sql
-- Your answer:

```

**4.4** Actually promote the video (dry_run=FALSE):
```sql
-- Your answer:

```

### Cleanup
```sql
DELETE FROM video WHERE file_path LIKE 'videos/lab4/%';
DELETE FROM promotion_log WHERE user_id = 'lab_user';
```

<details>
<summary>Solutions</summary>

```sql
-- 4.1
SELECT * FROM get_class_distribution('dataset_all');

-- 4.2
SELECT * FROM check_dataset_balance(2, 2.0);

-- 4.3
SELECT * FROM promote_video_safe(
    (SELECT video_id FROM video WHERE file_path = 'videos/lab4/temp_001.mp4'),
    'dataset_all',
    'happy',
    'lab_user',
    'lab4-dry-run',
    TRUE
);

-- 4.4
SELECT * FROM promote_video_safe(
    (SELECT video_id FROM video WHERE file_path = 'videos/lab4/temp_001.mp4'),
    'dataset_all',
    'happy',
    'lab_user',
    'lab4-actual'
);
```
</details>

---

## Lab 5: Python ORM (Module 5)

### Setup

Create file `lab5_orm.py`:

```python
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func

# Adjust import path as needed
import sys
sys.path.insert(0, '/home/user/project-reachy-emotion/apps/api/app')
from db.models import Video, Base

DATABASE_URL = "postgresql+asyncpg://reachy_app:password@localhost/reachy_local"

async def main():
    engine = create_async_engine(DATABASE_URL, echo=True)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as session:
        # Your code here
        pass

if __name__ == "__main__":
    asyncio.run(main())
```

### Exercises

**5.1** Create 3 Video objects and insert them:
```python
# Your code:

```

**5.2** Query all temp videos and print their file_paths:
```python
# Your code:

```

**5.3** Update a video's label and split:
```python
# Your code:

```

**5.4** Count videos grouped by split:
```python
# Your code:

```

<details>
<summary>Solutions</summary>

```python
# 5.1
async with Session() as session:
    videos = [
        Video(file_path="videos/lab5/001.mp4", size_bytes=1000),
        Video(file_path="videos/lab5/002.mp4", size_bytes=2000),
        Video(file_path="videos/lab5/003.mp4", size_bytes=3000),
    ]
    session.add_all(videos)
    await session.commit()

# 5.2
async with Session() as session:
    result = await session.execute(
        select(Video).where(Video.split == "temp")
    )
    for video in result.scalars():
        print(video.file_path)

# 5.3
async with Session() as session:
    result = await session.execute(
        select(Video).where(Video.file_path == "videos/lab5/001.mp4")
    )
    video = result.scalar_one()
    video.split = "dataset_all"
    video.label = "happy"
    await session.commit()

# 5.4
async with Session() as session:
    result = await session.execute(
        select(Video.split, func.count(Video.video_id))
        .group_by(Video.split)
    )
    for split, count in result.all():
        print(f"{split}: {count}")
```
</details>

---

## Lab 6: API Endpoints (Module 6)

### Setup

Create file `lab6_api.py`:

```python
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import sys
sys.path.insert(0, '/home/user/project-reachy-emotion/apps/api/app')
from db.models import Video

DATABASE_URL = "postgresql+asyncpg://reachy_app:password@localhost/reachy_local"
engine = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app = FastAPI()

async def get_db():
    async with SessionLocal() as session:
        yield session

# Add your endpoints here

# Run with: uvicorn lab6_api:app --reload --port 8000
```

### Exercises

**6.1** Create GET /videos endpoint that lists all videos:
```python
# Your code:

```

**6.2** Create GET /videos/{video_id} endpoint:
```python
# Your code:

```

**6.3** Create POST /videos endpoint with request validation:
```python
# Your code:

```

**6.4** Add error handling for not found:
```python
# Your code:

```

<details>
<summary>Solutions</summary>

```python
class VideoOut(BaseModel):
    video_id: str
    file_path: str
    split: str
    label: Optional[str] = None

    class Config:
        from_attributes = True

class VideoCreate(BaseModel):
    file_path: str
    size_bytes: int

# 6.1
@app.get("/videos", response_model=list[VideoOut])
async def list_videos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Video).limit(100))
    return result.scalars().all()

# 6.2 & 6.4
@app.get("/videos/{video_id}", response_model=VideoOut)
async def get_video(video_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Video).where(Video.video_id == video_id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video

# 6.3
@app.post("/videos", response_model=VideoOut)
async def create_video(data: VideoCreate, db: AsyncSession = Depends(get_db)):
    video = Video(file_path=data.file_path, size_bytes=data.size_bytes)
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video
```
</details>

---

## Lab 7: Migrations (Module 7)

### Exercises

**7.1** Check which tables exist:
```bash
# Your command:

```

**7.2** Backup the database:
```bash
# Your command:

```

**7.3** Check database size:
```sql
-- Your query:

```

**7.4** Create a new migration file that adds a column:
```sql
-- Your SQL:

```

<details>
<summary>Solutions</summary>

```bash
# 7.1
psql -U reachy_app -d reachy_local -c "\dt"

# 7.2
pg_dump -U reachy_app -d reachy_local > backup_$(date +%Y%m%d).sql
```

```sql
-- 7.3
SELECT pg_size_pretty(pg_database_size('reachy_local'));

-- 7.4
ALTER TABLE video ADD COLUMN IF NOT EXISTS
    quality_score NUMERIC(3,2) CHECK (quality_score >= 0 AND quality_score <= 1);
```
</details>

---

## Lab 8: Troubleshooting (Module 8)

### Exercises

**8.1** Diagnose why this query is slow:
```sql
SELECT * FROM video WHERE metadata->>'source' = 'jetson';
```

**8.2** Fix it:
```sql
-- Your solution:

```

**8.3** Find all active database connections:
```sql
-- Your query:

```

**8.4** Check for long-running queries:
```sql
-- Your query:

```

<details>
<summary>Solutions</summary>

```sql
-- 8.1
EXPLAIN ANALYZE SELECT * FROM video WHERE metadata->>'source' = 'jetson';
-- Will show Seq Scan (no index)

-- 8.2
CREATE INDEX idx_video_metadata_source ON video ((metadata->>'source'));
EXPLAIN ANALYZE SELECT * FROM video WHERE metadata->>'source' = 'jetson';
-- Now shows Index Scan

-- 8.3
SELECT pid, usename, application_name, client_addr, state
FROM pg_stat_activity
WHERE datname = 'reachy_local';

-- 8.4
SELECT pid, now() - query_start as duration, query
FROM pg_stat_activity
WHERE datname = 'reachy_local'
  AND state = 'active'
ORDER BY duration DESC;
```
</details>

---

## Final Capstone Challenge

### Build a Complete Video Management System

Create a mini-application that:

1. **Ingests videos** - Insert new video records
2. **Labels videos** - Promote from temp to dataset_all with label
3. **Creates training runs** - Sample videos for training
4. **Generates reports** - Show class distribution and training history

### Requirements

- Use FastAPI for the API
- Use SQLAlchemy for database access
- Follow the repository pattern
- Include proper error handling
- Add at least one stored procedure call

### Evaluation Criteria

- [ ] All CRUD operations work
- [ ] Business rules enforced (split/label policy)
- [ ] Proper error messages returned
- [ ] Code follows project patterns
- [ ] Documentation included

---

## Congratulations!

You've completed all the hands-on exercises. You should now be confident working with the Reachy database system.

**Next steps:**
1. Review any exercises you found difficult
2. Explore the actual codebase
3. Try fixing one of the known issues
4. Build a feature using what you learned
