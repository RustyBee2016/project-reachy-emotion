# Module 8: Troubleshooting & Capstone

**Duration**: 2 hours
**Prerequisites**: All previous modules
**Goal**: Debug database issues and apply all learned skills

---

## Learning Objectives

By the end of this module, you will be able to:
1. Diagnose common database errors
2. Fix the known issues in Reachy's database
3. Debug connection problems
4. Optimize slow queries
5. Complete a capstone project

---

## Lesson 8.1: Common Errors and Fixes (45 minutes)

### Connection Refused

**Error:**
```
psql: error: connection to server at "localhost" (127.0.0.1), port 5432 failed:
Connection refused
```

**Causes & Fixes:**

| Cause | Fix |
|-------|-----|
| PostgreSQL not running | `sudo systemctl start postgresql` |
| Wrong port | Check `postgresql.conf` for `port` setting |
| PostgreSQL not installed | `sudo apt install postgresql-16` |

**Diagnostic:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check which port it's listening on
sudo netstat -tlnp | grep postgres
```

### Authentication Failed

**Error:**
```
FATAL: password authentication failed for user "reachy_app"
```

**Fixes:**
```bash
# Reset password
sudo -u postgres psql -c "ALTER USER reachy_app PASSWORD 'new_password';"

# Check pg_hba.conf for authentication method
sudo cat /etc/postgresql/16/main/pg_hba.conf
```

### Permission Denied

**Error:**
```
ERROR: permission denied for table video
```

**Fixes:**
```sql
-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO reachy_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO reachy_app;
```

### Enum Value Invalid

**Error:**
```
ERROR: invalid input value for enum video_split: "purged"
```

**Cause:** The enum doesn't include that value.

**Fix:**
```sql
-- Add missing value
ALTER TYPE video_split ADD VALUE 'purged';

-- Check current values
SELECT enum_range(NULL::video_split);
```

### Foreign Key Violation

**Error:**
```
ERROR: insert or update on table "training_selection" violates foreign key constraint
DETAIL: Key (run_id)=(abc-123) is not present in table "training_run"
```

**Cause:** Trying to reference a row that doesn't exist.

**Fix:** Insert the parent row first, or use valid existing IDs.

### Unique Constraint Violation

**Error:**
```
ERROR: duplicate key value violates unique constraint "video_sha256_size_bytes_key"
```

**Cause:** Trying to insert a duplicate.

**Fix:** Use `ON CONFLICT` for upsert:
```sql
INSERT INTO video (sha256, size_bytes, file_path, split)
VALUES ('abc123', 1024, 'path.mp4', 'temp')
ON CONFLICT (sha256, size_bytes) DO UPDATE SET
    file_path = EXCLUDED.file_path;
```

### Check Constraint Violation

**Error:**
```
ERROR: new row for relation "video" violates check constraint "chk_video_split_label_policy"
```

**Cause:** Business rule violation (e.g., dataset_all without label).

**Fix:** Follow the business rules:
```sql
-- dataset_all requires label
UPDATE video SET split = 'dataset_all', label = 'happy' WHERE ...;

-- NOT: UPDATE video SET split = 'dataset_all' WHERE ...;
```

---

## Lesson 8.2: Fixing Known Issues (30 minutes)

### Issue #1: Missing 'fearful' Emotion

**Problem:** Python enums missing 'fearful'.

**Fix in `apps/api/app/db/enums.py`:**
```python
EmotionEnum = Enum(
    "neutral",
    "happy",
    "sad",
    "angry",
    "surprise",
    "fearful",  # ADD THIS LINE
    name=EMOTION_ENUM_NAME,
    native_enum=False,
)
```

### Issue #2: Missing 'purged' Split

**Problem:** Alembic migration missing 'purged'.

**Fix in Alembic migration:**
```python
split_enum = sa.Enum(
    "temp",
    "dataset_all",
    "train",
    "test",
    "purged",  # ADD THIS LINE
    name="video_split_enum",
)
```

### Issue #3: Check Constraint Mismatch

**Problem:** SQL files missing check constraint.

**Fix - Add to `001_phase1_schema.sql`:**
```sql
ALTER TABLE video ADD CONSTRAINT chk_video_split_label_policy CHECK (
    (split IN ('temp', 'test', 'purged') AND label IS NULL)
    OR
    (split IN ('dataset_all', 'train') AND label IS NOT NULL)
);
```

### Issue #4: Missing SQLAlchemy Models

**Problem:** `user_session`, `generation_request`, `emotion_event` not in models.py.

**Fix - Add to `apps/api/app/db/models.py`:**
```python
class UserSession(Base):
    __tablename__ = "user_session"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

class GenerationRequest(Base):
    __tablename__ = "generation_request"

    request_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    emotion: Mapped[str] = mapped_column(EmotionEnum, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")

class EmotionEvent(Base):
    __tablename__ = "emotion_event"

    event_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    device_id: Mapped[str] = mapped_column(String(255), nullable=False)
    emotion: Mapped[str] = mapped_column(EmotionEnum, nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
```

---

## Lesson 8.3: Performance Troubleshooting (30 minutes)

### Identify Slow Queries

```sql
-- Enable timing
\timing on

-- Run your query
SELECT * FROM video WHERE label = 'happy';
-- Time: 1523.456 ms  <-- Slow!

-- Analyze query plan
EXPLAIN ANALYZE SELECT * FROM video WHERE label = 'happy';
```

### Reading EXPLAIN Output

```sql
EXPLAIN ANALYZE SELECT * FROM video WHERE split = 'train';

-- Good output (using index):
Index Scan using idx_video_split on video  (cost=0.29..8.30 rows=1 width=200)
  Index Cond: (split = 'train'::video_split)
  Actual time: 0.023..0.025 rows=100 loops=1

-- Bad output (scanning all rows):
Seq Scan on video  (cost=0.00..1234.00 rows=50000 width=200)
  Filter: (split = 'train'::video_split)
  Actual time: 0.010..150.234 rows=100 loops=1
```

### Fix: Add Missing Index

```sql
-- If Seq Scan on frequently queried column:
CREATE INDEX idx_video_label ON video(label);

-- Verify index is used
EXPLAIN ANALYZE SELECT * FROM video WHERE label = 'happy';
```

### Fix: Vacuum and Analyze

```sql
-- Update statistics for query planner
ANALYZE video;

-- Reclaim dead tuple space
VACUUM video;

-- Both together
VACUUM ANALYZE video;
```

---

## Capstone Project: Build a Metrics Dashboard (30 minutes)

### Objective

Create API endpoints that power a training metrics dashboard.

### Requirements

1. **Endpoint: Dataset Overview**
   - Total videos per split
   - Total videos per label
   - Total dataset size in MB

2. **Endpoint: Training Run Summary**
   - List of training runs with status
   - Video counts per run
   - Train/test distribution

3. **Endpoint: Recent Activity**
   - Last 10 promotions
   - Last 5 training runs

### Starter Code

```python
# routers/dashboard.py
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_db
from ..db.models import Video, TrainingRun, TrainingSelection, PromotionLog

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    # TODO: Implement
    # Return: videos_by_split, videos_by_label, total_size_mb
    pass

@router.get("/training-runs")
async def get_training_runs(db: AsyncSession = Depends(get_db)):
    # TODO: Implement
    # Return: list of runs with video counts
    pass

@router.get("/recent-activity")
async def get_recent_activity(db: AsyncSession = Depends(get_db)):
    # TODO: Implement
    # Return: recent promotions, recent runs
    pass
```

### Solution

```python
@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    # Videos by split
    split_result = await db.execute(
        select(Video.split, func.count(Video.video_id))
        .group_by(Video.split)
    )
    videos_by_split = {row[0]: row[1] for row in split_result.all()}

    # Videos by label
    label_result = await db.execute(
        select(Video.label, func.count(Video.video_id))
        .where(Video.label.isnot(None))
        .group_by(Video.label)
    )
    videos_by_label = {row[0]: row[1] for row in label_result.all()}

    # Total size
    size_result = await db.execute(
        select(func.sum(Video.size_bytes))
    )
    total_bytes = size_result.scalar() or 0

    return {
        "videos_by_split": videos_by_split,
        "videos_by_label": videos_by_label,
        "total_size_mb": round(total_bytes / 1048576, 2)
    }

@router.get("/training-runs")
async def get_training_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            TrainingRun.run_id,
            TrainingRun.strategy,
            TrainingRun.status,
            TrainingRun.created_at,
            func.count(TrainingSelection.video_id).label("video_count")
        )
        .outerjoin(TrainingSelection)
        .group_by(TrainingRun.run_id)
        .order_by(TrainingRun.created_at.desc())
        .limit(10)
    )
    return [
        {
            "run_id": row.run_id,
            "strategy": row.strategy,
            "status": row.status,
            "created_at": row.created_at.isoformat(),
            "video_count": row.video_count
        }
        for row in result.all()
    ]

@router.get("/recent-activity")
async def get_recent_activity(db: AsyncSession = Depends(get_db)):
    # Recent promotions
    promo_result = await db.execute(
        select(PromotionLog)
        .order_by(PromotionLog.promoted_at.desc())
        .limit(10)
    )
    promotions = [
        {
            "video_id": p.video_id,
            "from_split": p.from_split,
            "to_split": p.to_split,
            "label": p.label,
            "success": p.success,
            "promoted_at": p.promoted_at.isoformat()
        }
        for p in promo_result.scalars()
    ]

    # Recent runs
    run_result = await db.execute(
        select(TrainingRun)
        .order_by(TrainingRun.created_at.desc())
        .limit(5)
    )
    runs = [
        {
            "run_id": r.run_id,
            "strategy": r.strategy,
            "status": r.status,
            "created_at": r.created_at.isoformat()
        }
        for r in run_result.scalars()
    ]

    return {"promotions": promotions, "training_runs": runs}
```

---

## Final Knowledge Check

1. What's the first thing to check when you get "connection refused"?
2. How do you add a new value to an existing ENUM?
3. What does `EXPLAIN ANALYZE` show you?
4. What constraint prevents adding a video to dataset_all without a label?

<details>
<summary>Click to see answers</summary>

1. Check if PostgreSQL is running: `sudo systemctl status postgresql`

2. `ALTER TYPE enum_name ADD VALUE 'new_value';`

3. The query execution plan and actual timing - helps identify if indexes are being used and where time is spent.

4. The `chk_video_split_label_policy` CHECK constraint.

</details>

---

## Course Completion Checklist

You should now be able to:

- [ ] Explain relational database concepts
- [ ] Write SQL queries (SELECT, INSERT, UPDATE, DELETE)
- [ ] Navigate PostgreSQL with psql
- [ ] Understand all 12 Reachy tables
- [ ] Call stored procedures
- [ ] Define SQLAlchemy models
- [ ] Build FastAPI endpoints with database access
- [ ] Apply migrations
- [ ] Debug common database issues

---

## Next Steps

1. **Practice**: Build more endpoints using the database
2. **Explore**: Read the full documentation in `docs/database/`
3. **Contribute**: Help fix the known issues
4. **Monitor**: Set up database health checks in production

**Congratulations on completing the Reachy Database Training!**
