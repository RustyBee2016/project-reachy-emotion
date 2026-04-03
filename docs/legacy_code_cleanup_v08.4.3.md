# Legacy Code Cleanup - v08.4.3

## Overview

This document tracks the cleanup of legacy dataset creation code that uses incorrect paths or outdated patterns.

---

## Fixed Issues

### ✅ Issue #1: Legacy Validation Ingestion Method

**File:** `trainer/ingest_affectnet.py`

**Method:** `ingest_validation_set()`

**Problem:** Copies validation images to `train/<label>/` instead of run-scoped directory

**Fix Applied:** Added deprecation warning in docstring and runtime warning

**Status:** DEPRECATED (not removed to avoid breaking external scripts)

**Replacement:** Use `create_validation_dataset()` which creates run-scoped datasets at `/videos/validation/run/<run_id>/`

---

### ✅ Issue #2: Legacy Dataset Creation Script

**File:** `trainer/create_affectnet_datasets.py`

**Problems:**
- Copies validation images to `/test/validation/<emotion>/` (wrong location)
- Copies test images to `/test/<emotion>/` (wrong location)
- Does not support run-scoped datasets
- Mixes AffectNet with Luma videos

**Fix Applied:** Added comprehensive deprecation notice in module docstring

**Status:** DEPRECATED (kept for reference but should not be used)

**Replacement:**
- `trainer.ingest_affectnet validation-run` for validation datasets
- `trainer.manage_test_datasets create` for test datasets

---

## Remaining Legacy Code (Low Priority)

### Issue #3: Legacy Train Ingestion

**File:** `trainer/ingest_affectnet.py`

**Method:** `ingest_train_set()`

**Issue:** Copies AffectNet training images to `/train/<label>/` (mixes with Luma videos)

**Recommendation:** Keep but document clearly that it's for augmenting training data, not for validation/test

**Impact:** Low - intentional feature for adding AffectNet training data

**Status:** DOCUMENTED (no changes needed)

---

### Issue #4: Consolidated Dataset Builder

**File:** `trainer/build_consolidated_dataset.py`

**Issue:** Complex script that mixes Luma videos + AffectNet images, then splits 90/10

**Recommendation:** Deprecate in favor of:
- Frame extraction for Luma videos
- Separate AffectNet validation/test dataset creation

**Impact:** Medium - may be used for specific experiments

**Status:** PENDING REVIEW (needs user approval before deprecation)

---

### Issue #5: Split Run Dataset Script

**File:** `trainer/split_run_dataset.py`

**Issue:** Standalone script for 90/10 splitting (now removed from main pipeline)

**Recommendation:** Remove entirely (redundant with removed `split_run_dataset()` method)

**Impact:** Low - no longer used

**Status:** PENDING REMOVAL (safe to delete)

---

### Issue #6: Test Dataset Archive Path

**File:** `trainer/manage_test_datasets.py`

**Method:** `archive_test_dataset()`

**Current Path:** `/test/archive/run_<run_id>_YYYYMMDD_HHMMSS/`

**Question:** Should this be `/test/run/archive/` for consistency?

**Recommendation:** Review archive path structure for consistency

**Impact:** Low - archiving works correctly, just path organization question

**Status:** PENDING REVIEW (cosmetic change)

---

## Migration Guide

### Old Workflow (DEPRECATED)
```bash
# DO NOT USE - creates wrong directory structure
python -m trainer.create_affectnet_datasets \
    --run-id run_0300 \
    --train-per-class 20000 \
    --test-per-class 500
```

### New Workflow (CORRECT)
```bash
# Step 1: Create validation dataset
python -m trainer.ingest_affectnet validation-run \
    --run-id run_0300 \
    --samples-per-class 500 \
    --min-confidence 0.6 \
    --seed 42

# Step 2: Create test dataset
python -m trainer.manage_test_datasets create \
    --run-id run_0300 \
    --samples-per-class 250 \
    --source validation \
    --seed 142

# Step 3: Extract training frames (Luma videos)
# Use web UI: "Manual Execute Live" button
# Or via API: POST /api/v1/ingest/prepare-run-frames
```

---

## Web UI Changes

### Dataset Preparation Section

**Old:** Single "Create Both Datasets" button

**New:** Three separate buttons:
1. **🎬 Create Training Dataset** - Extracts frames from Luma videos
2. **📊 Create Validation Dataset** - Creates AffectNet validation set
3. **🧪 Create Test Dataset** - Creates AffectNet test set

**Result:** All datasets stored in correct run-scoped directories

---

## Directory Structure Comparison

### Old (INCORRECT)
```
/videos/
├── train/
│   ├── happy/                    # Luma videos + AffectNet images mixed
│   ├── sad/
│   ├── neutral/
│   └── run/
│       └── run_0300/
│           ├── train_ds_run_0300/    # 90% split
│           └── valid_ds_run_0300/    # 10% split
├── test/
│   ├── validation/
│   │   ├── happy/                # WRONG LOCATION
│   │   ├── sad/
│   │   └── neutral/
│   ├── happy/                    # WRONG LOCATION
│   ├── sad/
│   └── neutral/
```

### New (CORRECT)
```
/videos/
├── train/
│   ├── happy/                    # Luma videos ONLY
│   ├── sad/
│   ├── neutral/
│   └── run/
│       └── run_0300/             # All 119,110 frames in one directory
├── validation/
│   └── run/
│       └── run_0300/             # 1,500 AffectNet images (unlabeled)
├── test/
│   └── run_0300/                 # 750 AffectNet images (unlabeled)
```

---

## Summary

**Fixed:**
- ✅ Deprecated `ingest_validation_set()` method
- ✅ Deprecated `create_affectnet_datasets.py` script
- ✅ Removed 90/10 split from main pipeline
- ✅ Fixed test dataset paths (removed `affectnet_test_dataset` subdirectory)

**Pending:**
- ⏳ Review `build_consolidated_dataset.py` for deprecation
- ⏳ Remove `split_run_dataset.py` script
- ⏳ Review test dataset archive path structure

**Impact:**
All critical issues fixed. Remaining items are low-priority cleanup tasks that don't affect functionality.
