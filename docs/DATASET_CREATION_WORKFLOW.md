# Dataset Creation Workflow — Manual Videos + AffectNet

**Project:** Reachy_Local_08.4.2  
**Date:** 2026-04-01  
**Purpose:** Complete workflow for creating training, validation, and test datasets using manually-generated videos and AffectNet images.

---

## Overview

This workflow creates three dataset types:

1. **Training Dataset**: Manual videos (frames extracted) + AffectNet training images
2. **Validation Dataset**: AffectNet validation_set images (run-scoped, unlabeled)
3. **Test Dataset**: AffectNet validation_set images (run-scoped, unlabeled, separate sample)

### Key Principles

- **Manual videos**: Used for training only (10 frames extracted per video)
- **AffectNet validation_set**: Source for both validation AND test datasets (different seeds prevent overlap)
- **Run-scoped**: Each run gets unique validation + test datasets
- **Unlabeled storage**: Validation and test images stored with unlabeled filenames
- **Ground truth separation**: Labels stored in separate manifest files, not in DB

---

## Dataset Architecture

```
/videos/
├── train/
│   ├── happy/                          # Manual videos + AffectNet train images
│   ├── sad/
│   ├── neutral/
│   └── run/<run_id>/                   # Consolidated dataset (frames + images)
│       ├── train_ds_<run_id>/          # 90% training split
│       └── valid_ds_<run_id>/          # 10% validation split (for early stopping)
│
├── validation/
│   ├── run/<run_id>/                   # ← Run-scoped validation (variant comparison)
│   │   └── affectnet_*.jpg             # Unlabeled filenames (COPIED, not moved)
│   └── archive/                        # ← Archived validation sets
│       └── <run_id>_<timestamp>/
│
├── test/
│   └── affectnet_test_dataset/
│       ├── run<run_id>/                # Test datasets (Gate A evaluation)
│       │   └── affectnet_*.jpg         # Unlabeled filenames (COPIED, not moved)
│       └── archive/                    # Archived test sets

/videos/manifests/
├── <run_id>_validation_labels.jsonl    # Ground truth for validation
├── <run_id>_test_labels.jsonl          # Ground truth for test
└── ...
```

---

## Validation Strategy for Variant Models

**Question:** Should variant models (Variant 1 & Variant 2) be validated using AffectNet validation data or synthetic training videos?

**Answer:** **Use AffectNet validation data** for the following reasons:

1. **Independent evaluation**: AffectNet validation_set provides human-annotated benchmark
2. **Consistent comparison**: All variants evaluated on same validation set enables fair comparison
3. **Real-world generalization**: AffectNet contains diverse real faces (better proxy for production)
4. **Prevents overfitting**: Using synthetic videos for validation could leak training distribution patterns

**Implementation:**
- Create one validation dataset per run: `/videos/validation/run/<run_id>/`
- AffectNet images are **COPIED** (not moved) from source directory
- All variant models for that run use the same validation dataset
- After run completion, archive to `/videos/validation/archive/`

---

## Step-by-Step Workflow

### Prerequisites

1. **Manual videos** already recorded and stored in rename_prefix directories:
   - `/media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/happy_rename/`
   - `/media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/sad_rename/`
   - `/media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/neutral_rename/`

2. **AffectNet** dataset available at:
   - Training: `/media/rusty_admin/project_data/reachy_emotion/affectnet/consolidated/AffectNet+/human_annotated/train_set/`
   - Validation: `/media/rusty_admin/project_data/reachy_emotion/affectnet/consolidated/AffectNet+/human_annotated/validation_set/`

3. **Python environment**: `/home/rusty_admin/projects/reachy_08.4.2/venv/bin/python`

---

### Step 1: Rename and Move Manual Videos

**Purpose:** Move manual videos from `rename_prefix/` to `train/<label>/` with proper naming.

**Script:** `./scripts/rename_and_move_manual_videos.sh`

**Source Directories:**
- `/media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/happy_rename/`
- `/media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/sad_rename/`
- `/media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/neutral_rename/`

**Destination Directories:**
- `/media/rusty_admin/project_data/reachy_emotion/videos/train/happy/`
- `/media/rusty_admin/project_data/reachy_emotion/videos/train/sad/`
- `/media/rusty_admin/project_data/reachy_emotion/videos/train/neutral/`

**What it does:**
- Extracts emotion label from directory name (e.g., `happy_rename` → `happy`)
- Renames videos to format: `<emotion>_luma_YYYYMMDD_HHMMSS.mp4`
- **Moves** (not copies) videos from `rename_prefix/<emotion>_rename/` to `train/<emotion>/`
- Processes all three emotion classes automatically

**Command:**
```bash
cd /home/rusty_admin/projects/reachy_08.4.2
./scripts/rename_and_move_manual_videos.sh
```

**Expected output:**
```
============================================
Manual Video Rename and Move
============================================
Processing videos from rename_prefix directories
============================================

Processing: happy (from happy_rename)
----------------------------------------
  Found 50 video files

  ✓ Moved: video001.mp4 → happy_luma_20260401_120000.mp4
  ✓ Moved: video002.mp4 → happy_luma_20260401_120001.mp4
  ...

  Summary for happy:
    Moved: 50
    Skipped: 0
    Destination: /media/.../videos/train/happy

Processing: sad (from sad_rename)
----------------------------------------
  ...

Processing: neutral (from neutral_rename)
----------------------------------------
  ...

============================================
✓ All manual videos processed
============================================
```

**Verify:**
```bash
# Count videos per class
find /media/rusty_admin/project_data/reachy_emotion/videos/train/happy -name "*_luma_*.mp4" | wc -l
find /media/rusty_admin/project_data/reachy_emotion/videos/train/sad -name "*_luma_*.mp4" | wc -l
find /media/rusty_admin/project_data/reachy_emotion/videos/train/neutral -name "*_luma_*.mp4" | wc -l

# Verify rename_prefix directories are empty
ls /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/happy_rename/
ls /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/sad_rename/
ls /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/neutral_rename/
```

---

### Step 2: Ingest AffectNet Training Images

**Purpose:** Add 10,000 AffectNet training images per class to `train/<label>/`.

**Command:**
```bash
cd /home/rusty_admin/projects/reachy_08.4.2
/home/rusty_admin/projects/reachy_08.4.2/venv/bin/python -m trainer.ingest_affectnet train \
    --samples-per-class 10000 \
    --min-confidence 0.6 \
    --max-subset 1 \
    --seed 42
```

**Parameters:**
- `--samples-per-class 10000`: 10K images per emotion class
- `--min-confidence 0.6`: Minimum soft-label confidence (filters low-quality annotations)
- `--max-subset 1`: Include easy (0) and challenging (1) subsets, exclude difficult (2)
- `--seed 42`: Reproducible sampling

**Expected output:**
```
=== Ingesting AffectNet Training Set ===
Samples per class: 10000
Min confidence: 0.6
Max subset: 1
Filtering complete:
  happy: 45231 samples
  sad: 38492 samples
  neutral: 52103 samples
Balanced sampling complete:
  happy: 10000 samples
  sad: 10000 samples
  neutral: 10000 samples
Copying 10000 images to train/happy/...
Copying 10000 images to train/sad/...
Copying 10000 images to train/neutral/...
Wrote manifest: /media/.../manifests/affectnet_train_ingestion_20260401_120530.jsonl
```

**Verify:**
```bash
# Count AffectNet images per class
find /media/rusty_admin/project_data/reachy_emotion/videos/train/happy -name "affectnet_*.jpg" | wc -l
find /media/rusty_admin/project_data/reachy_emotion/videos/train/sad -name "affectnet_*.jpg" | wc -l
find /media/rusty_admin/project_data/reachy_emotion/videos/train/neutral -name "affectnet_*.jpg" | wc -l
```

---

### Step 3: Create Consolidated Training Dataset

**Purpose:** Combine manual video frames + AffectNet images into run-scoped training dataset.

**Command:**
```bash
cd /home/rusty_admin/projects/reachy_08.4.2
/home/rusty_admin/projects/reachy_08.4.2/venv/bin/python -m trainer.build_consolidated_dataset \
    --run-id run_0001 \
    --luma-videos-per-class 50 \
    --affectnet-images-per-class 10000 \
    --frames-per-video 10 \
    --seed 42
```

**Parameters:**
- `--run-id run_0001`: Run identifier
- `--luma-videos-per-class 50`: Select 50 manual videos per class
- `--affectnet-images-per-class 10000`: Use all 10K AffectNet images
- `--frames-per-video 10`: Extract 10 frames from each video
- `--seed 42`: Reproducible sampling

**What it does:**
1. Selects 50 manual videos per class (150 total)
2. Extracts 10 frames per video (500 frames per class)
3. Combines with 10K AffectNet images (10,500 samples per class)
4. Splits 90/10 into `train_ds_run_0001/` and `valid_ds_run_0001/`

**Expected output:**
```
=== Building Consolidated Dataset for run_0001 ===
Collecting Luma videos...
  happy: 50 videos selected
  sad: 50 videos selected
  neutral: 50 videos selected
Extracting frames...
  Extracted 500 frames from happy videos
  Extracted 500 frames from sad videos
  Extracted 500 frames from neutral videos
Collecting AffectNet images...
  happy: 10000 images
  sad: 10000 images
  neutral: 10000 images
Total samples: 31,500 (10,500 per class)
Creating train/valid split (90/10)...
  train_ds_run_0001: 28,350 samples
  valid_ds_run_0001: 3,150 samples
Wrote manifest: /media/.../manifests/run_0001_train.jsonl
```

**Verify:**
```bash
# Check consolidated dataset
ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/train/run/run_0001/
# Should show: train_ds_run_0001/ and valid_ds_run_0001/

# Count samples
find /media/rusty_admin/project_data/reachy_emotion/videos/train/run/run_0001/train_ds_run_0001 -name "*.jpg" | wc -l
find /media/rusty_admin/project_data/reachy_emotion/videos/train/run/run_0001/valid_ds_run_0001 -name "*.jpg" | wc -l
```

---

### Step 4: Create Validation Dataset

**Purpose:** Create run-scoped validation dataset for variant model comparison.

**Command:**
```bash
cd /home/rusty_admin/projects/reachy_08.4.2
/home/rusty_admin/projects/reachy_08.4.2/venv/bin/python -m trainer.ingest_affectnet validation-run \
    --run-id run_0001 \
    --samples-per-class 500 \
    --min-confidence 0.6 \
    --max-subset 1
```

**Parameters:**
- `--run-id run_0001`: Run identifier
- `--samples-per-class 500`: 500 images per class (1,500 total)
- `--min-confidence 0.6`: Quality filter
- `--max-subset 1`: Easy + challenging subsets
- `--seed`: Auto-generated (142 + run_number = 143) to prevent overlap with test

**What it does:**
1. Samples 500 images per class from AffectNet validation_set
2. **COPIES** (not moves) images to `/videos/validation/run/run_0001/` with **unlabeled filenames**
3. Source AffectNet images remain in original location
4. Stores ground truth in `/videos/manifests/run_0001_validation_labels.jsonl`

**Expected output:**
```
=== Creating Validation Dataset for run_0001 ===
Samples per class: 500
Random seed: 143
Filtering complete:
  happy: 823 samples
  sad: 612 samples
  neutral: 1204 samples
Balanced sampling complete:
  happy: 500 samples
  sad: 500 samples
  neutral: 500 samples
Copying 1500 images to validation/run/run_0001/...
Copied 1500 validation images
Wrote manifest: /media/.../manifests/run_0001_validation_ingestion.jsonl
Wrote manifest: /media/.../manifests/run_0001_validation_labels.jsonl
```

**Verify:**
```bash
# Check validation dataset
ls /media/rusty_admin/project_data/reachy_emotion/videos/validation/run/run_0001/ | head -10
# Should show: affectnet_00000.jpg, affectnet_00001.jpg, ... (unlabeled)

# Count samples
find /media/rusty_admin/project_data/reachy_emotion/videos/validation/run/run_0001 -name "*.jpg" | wc -l
# Should output: 1500

# Confirm source images still exist (COPIED, not moved)
ls /media/rusty_admin/project_data/reachy_emotion/affectnet/consolidated/AffectNet+/human_annotated/validation_set/images/ | head -5

# Check ground truth manifest
head -3 /media/rusty_admin/project_data/reachy_emotion/videos/manifests/run_0001_validation_labels.jsonl
```

---

### Step 5: Create Test Dataset

**Purpose:** Create run-scoped test dataset for Gate A evaluation.

**Command:**
```bash
cd /home/rusty_admin/projects/reachy_08.4.2
/home/rusty_admin/projects/reachy_08.4.2/venv/bin/python -m trainer.ingest_affectnet test \
    --run-id run_0001 \
    --samples-per-class 250 \
    --min-confidence 0.5 \
    --max-subset 2 \
    --source validation
```

**Parameters:**
- `--run-id run_0001`: Run identifier (note: path will be `run<run_id>` = `runrun_0001`)
- `--samples-per-class 250`: 250 images per class (750 total)
- `--min-confidence 0.5`: Lower threshold (more challenging)
- `--max-subset 2`: Include all difficulty levels
- `--source validation`: Use AffectNet validation_set (human-annotated)
- `--seed`: Auto-generated (42 + run_number = 43) to prevent overlap with validation

**What it does:**
1. Samples 250 images per class from AffectNet validation_set
2. **COPIES** (not moves) images to `/videos/test/affectnet_test_dataset/runrun_0001/` with **unlabeled filenames**
3. Source AffectNet images remain in original location
4. Stores ground truth in `/videos/manifests/run_0001_test_labels.jsonl`

**Expected output:**
```
=== Creating Test Dataset for run_0001 ===
Source: validation
Samples per class: 250
Random seed: 43
Filtering complete:
  happy: 823 samples
  sad: 612 samples
  neutral: 1204 samples
Balanced sampling complete:
  happy: 250 samples
  sad: 250 samples
  neutral: 250 samples
Copying 750 images to test/affectnet_test_dataset/runrun_0001/...
Copied 750 test images
Wrote manifest: /media/.../manifests/run_0001_test_ingestion.jsonl
Wrote manifest: /media/.../manifests/run_0001_test_labels.jsonl
```

**Verify:**
```bash
# Check test dataset
ls /media/rusty_admin/project_data/reachy_emotion/videos/test/affectnet_test_dataset/runrun_0001/ | head -10
# Should show: affectnet_00000.jpg, affectnet_00001.jpg, ... (unlabeled)

# Count samples
find /media/rusty_admin/project_data/reachy_emotion/videos/test/affectnet_test_dataset/runrun_0001 -name "*.jpg" | wc -l
# Should output: 750

# Confirm source images still exist (COPIED, not moved)
ls /media/rusty_admin/project_data/reachy_emotion/affectnet/consolidated/AffectNet+/human_annotated/validation_set/images/ | head -5

# Check ground truth manifest
head -3 /media/rusty_admin/project_data/reachy_emotion/videos/manifests/run_0001_test_labels.jsonl
```

---

### Step 6: Verify Complete Dataset Structure

**Command:**
```bash
tree -L 3 /media/rusty_admin/project_data/reachy_emotion/videos/
```

**Expected structure:**
```
/videos/
├── train/
│   ├── happy/
│   │   ├── happy_luma_*.mp4 (manual videos)
│   │   └── affectnet_*.jpg (10K images - COPIED from AffectNet)
│   ├── sad/
│   ├── neutral/
│   └── run/
│       └── run_0001/
│           ├── train_ds_run_0001/ (28,350 images)
│           └── valid_ds_run_0001/ (3,150 images)
├── validation/
│   ├── run/
│   │   └── run_0001/ (1,500 unlabeled images - COPIED from AffectNet)
│   └── archive/
├── test/
│   └── affectnet_test_dataset/
│       ├── runrun_0001/ (750 unlabeled images - COPIED from AffectNet)
│       └── archive/
└── manifests/
    ├── affectnet_train_ingestion_*.jsonl
    ├── run_0001_train.jsonl
    ├── run_0001_validation_labels.jsonl
    └── run_0001_test_labels.jsonl
```

---

## Dataset Usage in Training Pipeline

### Training Phase

**Config:** `trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml`

```yaml
data:
  train_dir: /media/rusty_admin/project_data/reachy_emotion/videos/train/run/run_0001/train_ds_run_0001
  valid_dir: /media/rusty_admin/project_data/reachy_emotion/videos/train/run/run_0001/valid_ds_run_0001
```

**Launch training:**
```bash
/home/rusty_admin/projects/reachy_08.4.2/venv/bin/python -m trainer.run_efficientnet_pipeline \
    --run-id run_0001 \
    --mode train
```

### Validation Phase (Variant Comparison)

**Purpose:** Evaluate variant models on the same validation dataset.

**Command:**
```bash
# Variant 1
/home/rusty_admin/projects/reachy_08.4.2/venv/bin/python -m trainer.run_efficientnet_pipeline \
    --run-id run_0001_variant1 \
    --mode validate \
    --checkpoint /path/to/variant1_checkpoint.pth \
    --validation-dir /media/rusty_admin/project_data/reachy_emotion/videos/validation/run/run_0001 \
    --ground-truth-manifest /media/rusty_admin/project_data/reachy_emotion/videos/manifests/run_0001_validation_labels.jsonl

# Variant 2
/home/rusty_admin/projects/reachy_08.4.2/venv/bin/python -m trainer.run_efficientnet_pipeline \
    --run-id run_0001_variant2 \
    --mode validate \
    --checkpoint /path/to/variant2_checkpoint.pth \
    --validation-dir /media/rusty_admin/project_data/reachy_emotion/videos/validation/run/run_0001 \
    --ground-truth-manifest /media/rusty_admin/project_data/reachy_emotion/videos/manifests/run_0001_validation_labels.jsonl
```

### Test Phase (Gate A Evaluation)

**Command:**
```bash
/home/rusty_admin/projects/reachy_08.4.2/venv/bin/python -m trainer.gate_a_validator \
    --predictions stats/results/run_0001/predictions.npz \
    --ground-truth-manifest /media/rusty_admin/project_data/reachy_emotion/videos/manifests/run_0001_test_labels.jsonl \
    --output stats/results/run_0001/gate_a_validation.json
```

---

## Archiving Datasets

### Archive Validation Dataset

**When:** After all variant models have been evaluated and run is complete.

**Command:**
```bash
# Archive validation dataset
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p /media/rusty_admin/project_data/reachy_emotion/videos/validation/archive
mv /media/rusty_admin/project_data/reachy_emotion/videos/validation/run/run_0001 \
   /media/rusty_admin/project_data/reachy_emotion/videos/validation/archive/run_0001_${TIMESTAMP}

# Archive ground truth manifest
mkdir -p /media/rusty_admin/project_data/reachy_emotion/videos/manifests/archive
mv /media/rusty_admin/project_data/reachy_emotion/videos/manifests/run_0001_validation_labels.jsonl \
   /media/rusty_admin/project_data/reachy_emotion/videos/manifests/archive/run_0001_validation_labels_${TIMESTAMP}.jsonl
```

**Verify:**
```bash
ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/validation/archive/
```

### Archive Test Dataset

**When:** After Gate A evaluation is complete and results are recorded.

**Command:**
```bash
# Archive test dataset
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p /media/rusty_admin/project_data/reachy_emotion/videos/test/affectnet_test_dataset/archive
mv /media/rusty_admin/project_data/reachy_emotion/videos/test/affectnet_test_dataset/runrun_0001 \
   /media/rusty_admin/project_data/reachy_emotion/videos/test/affectnet_test_dataset/archive/runrun_0001_${TIMESTAMP}

# Archive ground truth manifest
mkdir -p /media/rusty_admin/project_data/reachy_emotion/videos/manifests/archive
mv /media/rusty_admin/project_data/reachy_emotion/videos/manifests/run_0001_test_labels.jsonl \
   /media/rusty_admin/project_data/reachy_emotion/videos/manifests/archive/run_0001_test_labels_${TIMESTAMP}.jsonl
```

**Verify:**
```bash
ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/test/affectnet_test_dataset/archive/
```

---

## Summary

### Dataset Counts (run_0001)

| Dataset | Source | Samples | Storage | Labels | Copy/Move |
|---------|--------|---------|---------|--------|-----------|
| Training | Manual videos (50/class) + AffectNet train (10K/class) | 28,350 | `train/run/run_0001/train_ds_run_0001/` | In filenames | COPIED |
| Training Validation | 10% holdout from training | 3,150 | `train/run/run_0001/valid_ds_run_0001/` | In filenames | Extracted |
| Validation (variant comparison) | AffectNet validation_set | 1,500 | `validation/run/run_0001/` | Separate manifest | COPIED |
| Test (Gate A) | AffectNet validation_set | 750 | `test/affectnet_test_dataset/runrun_0001/` | Separate manifest | COPIED |

### Key Points

✅ **Manual videos**: Training only (frames extracted)  
✅ **AffectNet images**: **COPIED** (not moved) - source files remain in AffectNet directory  
✅ **AffectNet validation_set**: Source for both validation AND test (different seeds)  
✅ **Run-scoped**: Each run gets unique validation + test datasets  
✅ **Unlabeled storage**: Validation/test images stored without emotion in filename  
✅ **Ground truth separation**: Labels in separate manifests, not in DB  
✅ **Archiving**: Validation and test datasets archived after use  

### Deprecated Paths (NOT USED)

❌ `/videos/test/validation/happy`  
❌ `/videos/test/validation/sad`  
❌ `/videos/test/validation/neutral`  

These paths are **never created or used**. The `/test/` directory is reserved exclusively for test datasets.

---

## Next Steps

1. ✅ Run Step 1: Rename manual videos
2. ✅ Run Step 2: Ingest AffectNet training images
3. ✅ Run Step 3: Create consolidated training dataset
4. ✅ Run Step 4: Create validation dataset
5. ✅ Run Step 5: Create test dataset
6. ✅ Verify dataset structure
7. 🚀 Launch training pipeline
8. 📊 Evaluate variants on validation dataset
9. ✅ Run Gate A evaluation on test dataset
10. 📦 Archive validation dataset after run completion
