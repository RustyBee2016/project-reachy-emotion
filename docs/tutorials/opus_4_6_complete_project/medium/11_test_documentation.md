# Tutorial 11: Test Documentation & Pytest Markers

> **Priority**: MEDIUM — Developer onboarding
> **Time estimate**: 4-6 hours
> **Difficulty**: Easy
> **Prerequisites**: pytest basics

---

## Why This Matters

The project has 44 test files but no documentation about:
- Which tests can run locally (no external services)
- Which tests require PostgreSQL, MLflow, or LM Studio
- How to run just the fast tests vs. the full suite

New developers waste hours figuring this out.

---

## What You'll Build

1. A `TESTING.md` file explaining how to run tests
2. Pytest markers to categorize tests
3. A `conftest.py` with skip-if-unavailable logic

---

## Step 1: Create TESTING.md

Create `docs/TESTING.md`:

```markdown
# Testing Guide

## Quick Start

Run the fast, self-contained tests:

    pytest tests/apps/api/ -v            # API tests (no external deps)
    pytest tests/ -m unit -v             # All unit tests

## Test Categories

| Marker | Description | External Deps | Run Time |
|--------|-------------|--------------|----------|
| `unit` | Pure logic tests | None | < 30s |
| `integration` | Tests with DB/API | PostgreSQL | < 2 min |
| `slow` | Training pipeline | GPU, TAO | > 5 min |
| `external` | Needs LM Studio/Luma | Network services | Varies |

## Running Specific Categories

    pytest -m unit                       # Unit tests only
    pytest -m "not slow"                 # Everything except slow
    pytest -m "not external"             # Skip external service tests
    pytest -m "integration and not slow" # Integration but fast

## Test Structure

    tests/
    ├── apps/api/          # API tests (self-contained, async)
    ├── test_face_detector.py
    ├── test_hsemotion_weights.py
    ├── test_stratified_splitting.py
    ├── test_promotion_e2e.py
    ├── test_alembic_migration.py
    └── test_shared_contracts.py

## Environment Variables for Integration Tests

    export DATABASE_URL="postgresql+psycopg://reachy_dev:password@localhost:5432/reachy_emotion_test"
    export MLFLOW_TRACKING_URI="file:///tmp/mlruns"

## Adding New Tests

1. Place in appropriate directory
2. Add pytest markers: `@pytest.mark.unit` or `@pytest.mark.integration`
3. If test needs external service, use `@pytest.mark.external`
4. Run `pytest --collect-only` to verify discovery
```

---

## Step 2: Register Markers in pyproject.toml

Add to `pyproject.toml` (in the `[tool.pytest.ini_options]` section):

```toml
[tool.pytest.ini_options]
markers = [
    "unit: Pure logic tests with no external dependencies",
    "integration: Tests requiring database or API",
    "slow: Tests that take more than 30 seconds",
    "external: Tests requiring external services (LM Studio, Luma AI)",
]
testpaths = ["tests"]
asyncio_mode = "auto"
```

---

## Step 3: Create Root conftest.py

Create or update `tests/conftest.py`:

```python
"""
Root conftest — shared fixtures and skip logic.
"""

import os
import pytest


def pytest_configure(config):
    """Register custom markers."""
    # Markers are registered in pyproject.toml, but this ensures
    # they're available even without the config file.
    pass


@pytest.fixture
def requires_postgres():
    """Skip test if PostgreSQL is not available."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        pytest.skip("DATABASE_URL not set — skipping PostgreSQL test")


@pytest.fixture
def requires_gpu():
    """Skip test if CUDA GPU is not available."""
    try:
        import torch
        if not torch.cuda.is_available():
            pytest.skip("CUDA GPU not available")
    except ImportError:
        pytest.skip("PyTorch not installed")
```

---

## Checklist

- [ ] `docs/TESTING.md` created with test categories
- [ ] Pytest markers registered in `pyproject.toml`
- [ ] `tests/conftest.py` has skip fixtures
- [ ] `pytest --markers` shows custom markers
- [ ] `pytest -m unit --collect-only` shows only unit tests
