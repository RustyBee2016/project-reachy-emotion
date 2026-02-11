# Tutorial 15: Legacy File Cleanup

> **Priority**: LOW — Code hygiene
> **Time estimate**: 1-2 hours
> **Difficulty**: Easy
> **Prerequisites**: Git basics

---

## Why This Matters

The repository contains backup files, dead imports, and legacy code
that adds confusion without providing value.

---

## Files to Remove

### 1. Web UI Backup Files

```bash
cd /home/rusty_admin/projects/reachy_08.4.2

# Remove backup files (verify they're not referenced first)
grep -r "landing_page_msi-ds" apps/ --include="*.py" || echo "Not referenced"

# If not referenced, delete:
git rm apps/web/landing_page_msi-ds.py 2>/dev/null || true
git rm apps/web/landing_page_msi-ds_backup.py 2>/dev/null || true
```

### 2. Archive Legacy SQL Migrations

The root `/alembic/versions/` SQL files were superseded by Python
migrations in Tutorial 6. If you haven't already archived them:

```bash
mkdir -p alembic/_archived
git mv alembic/versions/001_phase1_schema.sql alembic/_archived/ 2>/dev/null || true
git mv alembic/versions/002_stored_procedures.sql alembic/_archived/ 2>/dev/null || true
git mv alembic/versions/003_missing_tables.sql alembic/_archived/ 2>/dev/null || true
```

### 3. Clean Root alembic/env.py

If the root `alembic/env.py` is empty or unused, remove it and
keep only the app-level env.py:

```bash
# Check if it's empty
wc -l alembic/env.py

# If empty or minimal, remove
git rm alembic/env.py 2>/dev/null || true
```

---

## Verification

After cleanup:

```bash
# Verify no broken imports
python -c "from apps.web.landing_page import *" 2>&1 | head -5
python -c "from apps.api.app.main import app" 2>&1 | head -5

# Verify tests still pass
pytest tests/apps/api/ -v --tb=short -q
```

---

## Checklist

- [ ] Backup files removed from `apps/web/`
- [ ] Legacy SQL migrations archived
- [ ] No broken imports
- [ ] Tests still pass
- [ ] Git commit with cleanup changes

---

## All Tutorials Complete!

Congratulations! You've worked through all 15 tutorials:

- **HIGH** (1-6): Core functionality — face detection, weight verification,
  promotion pipeline, stratified splitting, training run, database migrations
- **MEDIUM** (7-12): Reliability — CI/CD, web UI pages, shared contracts,
  test documentation, batch operations
- **LOW** (13-15): Polish — deploy page, project metadata, cleanup

**Phase 1 is complete** when Tutorial 5's training run passes Gate A
on real face data. Everything else supports and validates that goal.
