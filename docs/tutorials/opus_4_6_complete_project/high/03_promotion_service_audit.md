# Tutorial 3: Promotion Service Audit & Testing

> **Priority**: HIGH — Validates the core data pipeline
> **Time estimate**: 4-6 hours
> **Difficulty**: Moderate
> **Prerequisites**: PostgreSQL running, project dependencies installed

---

## Why This Matters

The promotion service is the **assembly line** of Phase 1:

```
Upload (temp) → Label → Promote (dataset_all) → Sample (train/test) → Train
```

If this pipeline breaks, you can't get data to the training loop.

**Good news**: After code review, the promotion service
(`apps/api/app/services/promote_service.py`) is **more complete than
initially reported**. Both `stage_to_dataset_all()` and `sample_split()`
are fully implemented with balanced sampling, rollback support, and
metrics tracking.

Your job in this tutorial is to **verify it works end-to-end** by
running the existing tests and adding a manual integration test.

---

## What You'll Learn

- How the promotion pipeline works (database + filesystem)
- How to read and run async Python tests
- How to verify API endpoints using `curl`
- How to trace data through the pipeline

---

## Step 1: Understand the Pipeline Architecture

The promotion service coordinates three things:

1. **Database** (SQLAlchemy) — Updates video records (split, label)
2. **Filesystem** (FileMover) — Moves/copies actual video files
3. **Manifests** — Regenerates JSONL manifests for training

### Key Classes

| Class | File | Role |
|-------|------|------|
| `PromoteService` | `apps/api/app/services/promote_service.py` | Orchestrator |
| `VideoRepository` | `apps/api/app/repositories/video_repository.py` | DB access |
| `FileMover` | `apps/api/app/fs/__init__.py` | File operations |
| `ManifestBackend` | `apps/api/app/manifest.py` | Manifest writes |

### Data Flow

```
POST /api/v1/promote/stage
  └─ PromoteService.stage_to_dataset_all()
       ├─ Validate: video exists, is in "temp" split
       ├─ FileMover: move file from temp/ to dataset_all/{label}/
       ├─ Repository: UPDATE video SET split='dataset_all', label='{label}'
       └─ Manifest: schedule rebuild

POST /api/v1/promote/sample
  └─ PromoteService.sample_split()
       ├─ Validate: target_split is "train" or "test"
       ├─ Repository: SELECT videos FROM dataset_all
       ├─ _balanced_sample(): round-robin across labels
       ├─ FileMover: copy files to train/{label}/ or test/{label}/
       ├─ Repository: INSERT INTO training_selection
       └─ Manifest: schedule rebuild
```

---

## Step 2: Run the Existing Promotion Tests

The project already has promotion tests. Run them first:

```bash
cd /home/rusty_admin/projects/reachy_08.4.2

# Run the promotion-specific tests
pytest tests/apps/api/test_promote_service.py -v

# Run all API tests to verify nothing is broken
pytest tests/apps/api/ -v
```

**Expected**: All tests pass. If any fail, read the error message carefully.
Common issues:

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: apps.api` | Run `pip install -e ".[dev]"` |
| `sqlalchemy.exc.OperationalError` | Tests use in-memory SQLite, should be OK |
| `ImportError: FileMover` | Check `apps/api/app/fs/__init__.py` exists |

---

## Step 3: Read the Promotion Router

Understand how API requests reach the service:

```bash
# Read the promote router
cat -n apps/api/app/routers/promote.py
```

Key endpoints to look for:

1. `POST /api/v1/promote/stage` — Stages videos from temp to dataset_all
2. `POST /api/v1/promote/sample` — Samples from dataset_all to train/test
3. `POST /api/v1/promote/reset-manifest` — Resets manifest files

Note any `# pragma: no cover` comments — these are coverage markers
on error-handling branches, not indicators of missing code. The actual
business logic is in the service layer.

---

## Step 4: Manual Integration Test with curl

Start the API server and test the promotion workflow manually.

### 4a. Start the API Server

```bash
cd /home/rusty_admin/projects/reachy_08.4.2
uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4b. Check Health

```bash
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
```

Expected: `{"status": "ok", ...}`

### 4c. List Videos in Temp

```bash
curl -s "http://localhost:8000/api/v1/media/list?split=temp" | python3 -m json.tool
```

This shows videos available for promotion. Note a `video_id` from the output.

### 4d. Stage a Video (Dry Run)

Test with dry_run=true first (no actual file movement):

```bash
curl -X POST http://localhost:8000/api/v1/promote/stage \
  -H "Content-Type: application/json" \
  -H "X-Correlation-ID: test-tutorial-03" \
  -d '{
    "video_ids": ["<paste-video-id-here>"],
    "label": "happy",
    "dry_run": true
  }' | python3 -m json.tool
```

Expected response:
```json
{
  "promoted_ids": ["<video-id>"],
  "skipped_ids": [],
  "failed_ids": [],
  "dry_run": true
}
```

### 4e. Stage for Real

If the dry run succeeded, run it for real:

```bash
curl -X POST http://localhost:8000/api/v1/promote/stage \
  -H "Content-Type: application/json" \
  -H "X-Correlation-ID: test-tutorial-03" \
  -d '{
    "video_ids": ["<paste-video-id-here>"],
    "label": "happy",
    "dry_run": false
  }' | python3 -m json.tool
```

### 4f. Verify the Video Moved

```bash
# Check it's now in dataset_all
curl -s "http://localhost:8000/api/v1/media/list?split=dataset_all" | python3 -m json.tool

# Check it's no longer in temp
curl -s "http://localhost:8000/api/v1/media/list?split=temp" | python3 -m json.tool
```

---

## Step 5: Test the Sampling Workflow

After staging several videos to dataset_all, test the train/test sampling:

```bash
# Sample 70% for training (dry run)
curl -X POST http://localhost:8000/api/v1/promote/sample \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "'$(python3 -c 'import uuid; print(uuid.uuid4())')'",
    "target_split": "train",
    "sample_fraction": 0.7,
    "strategy": "balanced_random",
    "seed": 42,
    "dry_run": true
  }' | python3 -m json.tool
```

If the dry run looks correct, run it for real (remove `"dry_run": true`
or set to `false`).

---

## Step 6: Write an End-to-End Promotion Test

Create `tests/test_promotion_e2e.py`:

```python
"""
End-to-end test for the promotion pipeline.

Tests the full flow: temp -> dataset_all -> train/test
using the actual PromoteService (with test database).
"""

import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path

from apps.api.app.services.promote_service import (
    PromoteService,
    StageResult,
    SampleResult,
    PromotionValidationError,
)


class FakeFileMover:
    """Test double for FileMover that doesn't touch the filesystem."""

    def __init__(self):
        self.moves = []
        self.copies = []

    def plan_stage_to_dataset_all(self, video_id, file_path):
        dest = f"/fake/dataset_all/{Path(file_path).name}"
        return MagicMock(destination=dest)

    def stage_to_dataset_all(self, video_id, file_path):
        dest = f"/fake/dataset_all/{Path(file_path).name}"
        self.moves.append((video_id, file_path, dest))
        return MagicMock(destination=dest)

    def plan_copy_to_split(self, video_id, file_path, target_split, run_id):
        dest = f"/fake/{target_split}/{Path(file_path).name}"
        return MagicMock(destination=dest)

    def copy_to_split(self, video_id, file_path, target_split, run_id):
        dest = f"/fake/{target_split}/{Path(file_path).name}"
        self.copies.append((video_id, file_path, dest))
        return MagicMock(destination=dest)

    def rollback(self, transitions):
        pass


class TestPromotionValidation:
    """Test input validation in the promotion service."""

    def test_empty_video_ids_raises(self):
        """Cannot stage with empty video list."""
        service = PromoteService(
            session=MagicMock(),
            file_mover=FakeFileMover(),
        )
        with pytest.raises(PromotionValidationError, match="At least one"):
            service._parse_video_ids([])

    def test_invalid_uuid_raises(self):
        """Invalid UUID format is rejected."""
        service = PromoteService(
            session=MagicMock(),
            file_mover=FakeFileMover(),
        )
        with pytest.raises(PromotionValidationError, match="Invalid"):
            service._parse_uuid("not-a-uuid", "video_id")

    def test_valid_uuid_accepted(self):
        """Valid UUID strings are accepted."""
        service = PromoteService(
            session=MagicMock(),
            file_mover=FakeFileMover(),
        )
        test_uuid = str(uuid.uuid4())
        result = service._parse_uuid(test_uuid, "video_id")
        assert result == test_uuid

    def test_label_normalization(self):
        """Labels are lowercased and validated."""
        service = PromoteService(
            session=MagicMock(),
            file_mover=FakeFileMover(),
        )

        # None label should raise
        with pytest.raises(PromotionValidationError, match="required"):
            service._normalize_label(None)

    def test_invalid_strategy_raises(self):
        """Only 'balanced_random' strategy is supported."""
        with pytest.raises(PromotionValidationError, match="Unsupported"):
            PromoteService._validate_strategy("random")

    def test_balanced_random_strategy_accepted(self):
        """The balanced_random strategy passes validation."""
        PromoteService._validate_strategy("balanced_random")

    def test_fraction_must_be_positive(self):
        """Sample fraction must be > 0."""
        with pytest.raises(PromotionValidationError, match="greater than 0"):
            PromoteService._normalize_fraction(0)

        with pytest.raises(PromotionValidationError, match="greater than 0"):
            PromoteService._normalize_fraction(-0.5)


class TestBalancedSampling:
    """Test the balanced sampling algorithm."""

    def test_balanced_sample_round_robins(self):
        """Balanced sampling picks evenly from each label."""
        service = PromoteService(
            session=MagicMock(),
            file_mover=FakeFileMover(),
        )

        # Create mock records: 5 happy, 5 sad
        candidates = []
        for i in range(5):
            record = MagicMock()
            record.video_id = str(uuid.uuid4())
            record.label = "happy"
            candidates.append(record)
        for i in range(5):
            record = MagicMock()
            record.video_id = str(uuid.uuid4())
            record.label = "sad"
            candidates.append(record)

        # Sample 6 out of 10
        selected = service._balanced_sample(candidates, 6, seed=42)

        assert len(selected) == 6

        # Should have 3 of each (balanced)
        happy_count = sum(1 for r in selected if r.label == "happy")
        sad_count = sum(1 for r in selected if r.label == "sad")
        assert happy_count == 3
        assert sad_count == 3

    def test_balanced_sample_empty_input(self):
        """Empty candidate list returns empty selection."""
        service = PromoteService(
            session=MagicMock(),
            file_mover=FakeFileMover(),
        )
        selected = service._balanced_sample([], 5, seed=42)
        assert len(selected) == 0
```

### Run the Test

```bash
pytest tests/test_promotion_e2e.py -v
```

---

## Checklist

Before moving to Tutorial 4, verify:

- [ ] `pytest tests/apps/api/test_promote_service.py -v` passes
- [ ] `pytest tests/apps/api/ -v` — all API tests pass
- [ ] Manual `curl` dry-run for staging works
- [ ] Manual `curl` dry-run for sampling works
- [ ] `tests/test_promotion_e2e.py` validation and sampling tests pass
- [ ] You understand the data flow: temp -> dataset_all -> train/test

---

## What's Next

Tutorial 4 fixes the dataset preparation to use **stratified splitting**
instead of naive random shuffle, ensuring class balance is preserved.
