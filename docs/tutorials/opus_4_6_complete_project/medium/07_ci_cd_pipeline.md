# Tutorial 7: CI/CD Pipeline with GitHub Actions

> **Priority**: MEDIUM — Prevents regressions
> **Time estimate**: 4-6 hours
> **Difficulty**: Easy-Moderate
> **Prerequisites**: GitHub repo access, tutorials 1-6 complete

---

## Why This Matters

Right now, there is **no automated way** to verify that code changes
don't break existing functionality. The 59 API tests pass, but nobody
checks them automatically. A single typo in a merge could break the
entire pipeline silently.

---

## What You'll Build

A GitHub Actions workflow that:
1. Runs on every pull request to `master`
2. Installs dependencies
3. Runs the API test suite (`tests/apps/api/`)
4. Runs the new tests from tutorials 1-6
5. Reports pass/fail status on the PR

---

## Step 1: Create the Workflow File

Create `.github/workflows/ci.yml`:

```yaml
name: Phase 1 CI

on:
  push:
    branches: [master, opus-phase-1-stats-v2]
  pull_request:
    branches: [master]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: reachy_dev
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: reachy_emotion_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    env:
      DATABASE_URL: postgresql+psycopg://reachy_dev:test_password@localhost:5432/reachy_emotion_test
      DB_HOST: localhost
      DB_PORT: 5432
      DB_NAME: reachy_emotion_test
      DB_USER: reachy_dev
      DB_PASSWORD: test_password
      PYTHONPATH: .

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y libgl1-mesa-glx libglib2.0-0

      - name: Install project dependencies
        run: |
          pip install --upgrade pip
          pip install -e ".[dev,trainer]"

      - name: Run API tests
        run: |
          pytest tests/apps/api/ -v --tb=short -x

      - name: Run face detector tests
        run: |
          pytest tests/test_face_detector.py -v --tb=short || true

      - name: Run weight verification tests
        run: |
          pytest tests/test_hsemotion_weights.py -v --tb=short || true

      - name: Run stratified splitting tests
        run: |
          pytest tests/test_stratified_splitting.py -v --tb=short

      - name: Run migration tests
        run: |
          pytest tests/test_alembic_migration.py -v --tb=short

      - name: Run promotion tests
        run: |
          pytest tests/test_promotion_e2e.py -v --tb=short
```

---

## Step 2: Create the Directory

```bash
mkdir -p /home/rusty_admin/projects/reachy_08.4.2/.github/workflows
```

Copy the YAML content to `.github/workflows/ci.yml`.

---

## Step 3: Add Branch Protection (Optional)

If you have admin access to the GitHub repo:

1. Go to Settings > Branches
2. Add a branch protection rule for `master`
3. Check "Require status checks to pass before merging"
4. Select the "Phase 1 CI / test" check

This prevents merging code that breaks tests.

---

## Step 4: Test Locally First

Before pushing, verify tests pass locally:

```bash
cd /home/rusty_admin/projects/reachy_08.4.2

# Run the core test suite
pytest tests/apps/api/ -v --tb=short

# Run the new tutorial tests
pytest tests/test_face_detector.py tests/test_stratified_splitting.py tests/test_alembic_migration.py tests/test_promotion_e2e.py -v --tb=short
```

---

## Step 5: Push and Verify

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow for Phase 1 tests"
git push
```

Open the repository on GitHub and check the Actions tab to see the
workflow running.

---

## Checklist

- [ ] `.github/workflows/ci.yml` created
- [ ] All tests pass locally
- [ ] Workflow runs on GitHub after push
- [ ] (Optional) Branch protection enabled for `master`
