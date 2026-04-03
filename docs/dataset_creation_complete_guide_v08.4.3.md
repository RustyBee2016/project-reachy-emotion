# Complete Dataset Creation Guide - v08.4.3

## Overview

This document provides comprehensive coverage of all dataset creation logic, scripts, workflows, and architecture for the Reachy emotion classification system.

---

## Table of Contents

1. [Dataset Types and Purposes](#dataset-types-and-purposes)
2. [Directory Structure](#directory-structure)
3. [Dataset Creation Scripts](#dataset-creation-scripts)
4. [Web UI Integration](#web-ui-integration)
5. [API Endpoints](#api-endpoints)
6. [Database Schema](#database-schema)
7. [Complete Workflows](#complete-workflows)
8. [Fixes Applied in v08.4.3](#fixes-applied-in-v0843)
9. [Legacy Code Identified](#legacy-code-identified)

---

## Dataset Types and Purposes

### 1. Training Videos (Luma Synthetic)
- **Source:** Manually generated Luma AI videos
- **Location:** `/videos/train/<emotion>/`
- **Count:** 11,911 videos (3,589 happy, 5,015 sad, 3,307 neutral)
- **Format:** MP4 videos, ~5 seconds each, 24 fps, 1152×864
- **Naming:** `<emotion>_luma_YYYYMMDD_HHMMSS.mp4`
- **Purpose:** Primary training data for emotion classifier
- **Database:** Registered in `video` table with `split='train'`, `label=<emotion>`

### 2. Training Frames (Extracted)
- **Source:** Extracted from Luma videos
- **Location:** `/videos/train/run/<run_id>/`
- **Count:** 119,110 frames (11,911 videos × 10 frames)
- **Format:** JPG images
- **Naming:** `<emotion>_<video_stem>_frame_<index>.jpg`
- **Purpose:** Frame-level training data for CNN
- **Database:** Registered in `extracted_frame` table with `run_id`, `label`

### 3. Validation Dataset (AffectNet)
- **Source:** AffectNet human-annotated validation_set
- **Location:** `/videos/validation/run/<run_id>/`
- **Count:** 1,500 images (500 per class)
- **Format:** JPG images
- **Naming:** `affectnet_<index>.jpg` (unlabeled filenames)
- **Purpose:** Early stopping, hyperparameter tuning during training
- **Database:** Registered in `video` table with `split='validation'`, `label=NULL`
- **Ground Truth:** Separate manifest at `/manifests/<run_id>_validation_labels.jsonl`

### 4. Test Dataset (AffectNet)
- **Source:** AffectNet human-annotated validation_set (different samples than validation)
- **Location:** `/videos/test/<run_id>/` (simplified path - no affectnet_test_dataset subdirectory)
- **Count:** 750 images (250 per class)
- **Format:** JPG images
- **Naming:** `affectnet_<index>.jpg` (unlabeled filenames)
- **Purpose:** Final unbiased evaluation after training
- **Database:** Registered in `video` table with `split='test'`, `label=NULL`
- **Ground Truth:** Separate manifest at `/manifests/<run_id>_test_labels.jsonl`

---

## Directory Structure

```
/media/rusty_admin/project_data/reachy_emotion/videos/
├── train/
│   ├── happy/                    # 3,589 Luma videos
│   ├── sad/                      # 5,015 Luma videos
│   ├── neutral/                  # 3,307 Luma videos
│   └── run/
│       └── run_XXXX/             # 119,110 extracted frames (all in one directory)
│
├── validation/
│   └── run/
│       └── run_XXXX/             # 1,500 AffectNet images (unlabeled filenames)
│
├── test/
│   ├── run_XXXX/                 # 750 AffectNet images (unlabeled filenames)
│   └── archive/                  # Archived test datasets
│
├── temp/                         # Temporary uploads (auto-purged after TTL)
└── thumbs/                       # Auto-generated thumbnails

/media/rusty_admin/project_data/reachy_emotion/manifests/
├── run_XXXX_train.jsonl          # Training frames manifest
├── run_XXXX_validation_labels.jsonl   # Validation ground truth
└── run_XXXX_test_labels.jsonl    # Test ground truth
```

---

## Dataset Creation Scripts

### 1. Video Registration Script
**File:** `scripts/register_renamed_videos.py`

**Purpose:** Register existing Luma videos in database

**Key Functions:**
- `extract_video_metadata()` - Uses OpenCV to get duration, fps, resolution
- `compute_sha256()` - Computes file hash for deduplication
- `register_video_in_db()` - Inserts record into `video` table

**Database Fields:**
```python
{
    'file_path': 'train/<emotion>/<filename>',
    'split': 'train',
    'label': '<emotion>',
    'duration_sec': float,
    'fps': float,
    'width': int,
    'height': int,
    'size_bytes': int,
    'sha256': str,
    'created_at': datetime,
    'updated_at': datetime,
    'extra_data': {
        'source': 'manual_luma',
        'ingested_at': ISO timestamp
    }
}
```

**Usage:**
```bash
python scripts/register_renamed_videos.py
```

**Output:** Registers all videos in `/train/<emotion>/` directories

---

### 2. Frame Extraction Script
**File:** `trainer/prepare_dataset.py`

**Class:** `DatasetPreparer`

**Key Methods:**

#### `prepare_run_frames()`
Extracts frames from Luma videos for a specific run.

**Parameters:**
- `run_id` - Run identifier (e.g., 'run_0300')
- `train_fraction` - Fraction of videos to use (default: 1.0)
- `frames_per_video` - Frames to extract per video (default: 10)
- `seed` - Random seed for reproducibility
- `face_crop` - Enable face detection and cropping (default: False)
- `face_target_size` - Face crop output size (default: 224)
- `face_confidence` - Min face detection confidence (default: 0.6)

**Process:**
1. Scans `/train/<emotion>/` directories for videos
2. Samples `train_fraction` of videos per class
3. Extracts `frames_per_video` random frames from each video
4. Optionally detects faces and crops to face ROI
5. Saves frames to `/train/run/<run_id>/`
6. Generates manifest at `/manifests/<run_id>_train.jsonl`

**Frame Naming:**
```
<emotion>_<video_stem>_frame_<index>.jpg
Example: happy_happy_luma_20260401_095738_001_frame_003.jpg
```

**Manifest Format:**
```json
{
  "frame_path": "train/run/run_0300/happy_..._frame_003.jpg",
  "source_video": "train/happy/happy_luma_20260401_095738_001.mp4",
  "label": "happy",
  "frame_index": 3,
  "timestamp_sec": 1.25,
  "sha256": "abc123...",
  "width": 1152,
  "height": 864
}
```

#### `resolve_run_id()`
Auto-generates next sequential run_ID if not provided.

**Logic:**
1. Scans `/train/run/` for existing run_XXXX directories
2. Finds highest number
3. Returns `run_{next_number:04d}`

**Example:** If `run_0299` exists, returns `run_0300`

---

### 3. AffectNet Validation Dataset Script
**File:** `trainer/ingest_affectnet.py`

**Class:** `AffectNetIngester`

**Key Methods:**

#### `create_validation_dataset()`
Creates run-scoped validation dataset from AffectNet validation_set.

**Parameters:**
- `run_id` - Run identifier (e.g., 'run_0300')
- `samples_per_class` - Images per emotion class (default: 500)
- `min_confidence` - Min soft-label confidence (default: 0.6)
- `max_subset` - Max difficulty level 0=easy, 1=challenging, 2=difficult (default: 1)
- `seed` - Random seed (auto-generated from run_id if not provided)

**Process:**
1. Reads AffectNet annotations from `/affectnet/human_annotated/validation_set/annotations/`
2. Filters annotations:
   - Labels: 0 (neutral), 1 (happy), 2 (sad)
   - Confidence ≥ `min_confidence`
   - Subset ≤ `max_subset`
3. Balanced sampling: `samples_per_class` per emotion
4. Copies images to `/validation/run/<run_id>/`
5. Uses **unlabeled filenames**: `affectnet_<index>.jpg`
6. Shuffles images to prevent label leakage from ordering
7. Creates DB manifest with `split='validation'`, `label=NULL`
8. Creates ground truth manifest with actual labels

**Database Records:**
```python
{
    'file_path': 'validation/run/run_0300/affectnet_00042.jpg',
    'split': 'validation',
    'label': None,  # NULL - unlabeled in DB
    'sha256': str,
    'size_bytes': int,
    'width': int,
    'height': int,
    'metadata': {
        'affectnet_id': str,
        'soft_label': dict,
        'confidence': float,
        'subset': int,
        'valence': float,
        'arousal': float
    }
}
```

**Ground Truth Manifest:**
```json
{
  "file_path": "validation/run/run_0300/affectnet_00042.jpg",
  "label": "happy",
  "affectnet_id": "val_1234",
  "soft_label": {"happy": 0.95, "sad": 0.03, "neutral": 0.02},
  "confidence": 0.95,
  "subset": 0,
  "valence": 0.8,
  "arousal": 0.6
}
```

**CLI Usage:**
```bash
python -m trainer.ingest_affectnet validation-run \
    --run-id run_0300 \
    --samples-per-class 500 \
    --min-confidence 0.6 \
    --seed 42
```

---

### 4. AffectNet Test Dataset Script
**File:** `trainer/manage_test_datasets.py`

**Class:** `TestDatasetManager`

**Key Methods:**

#### `create_test_dataset()`
Creates run-scoped test dataset from AffectNet.

**Parameters:**
- `run_id` - Run identifier (e.g., 'run_0300')
- `samples_per_class` - Images per emotion class (default: 250)
- `source` - 'validation' or 'no_human' (default: 'validation')
- `seed` - Random seed (auto-generated from run_id if not provided)

**Process:**
1. Uses different seed than validation to ensure non-overlapping samples
2. Reads AffectNet annotations from specified source
3. Filters and samples (same logic as validation)
4. Copies images to `/test/run/<run_id>/`
5. Uses **unlabeled filenames**: `affectnet_<index>.jpg`
6. Creates DB manifest with `split='test'`, `label=NULL`
7. Creates ground truth manifest with actual labels

**Seed Generation:**
- Validation: `seed = 142 + run_number`
- Test: `seed = 42 + run_number`
- Different offsets ensure non-overlapping samples

**CLI Usage:**
```bash
python -m trainer.manage_test_datasets create \
    --run-id run_0300 \
    --samples-per-class 250 \
    --source validation \
    --seed 142
```

#### `archive_test_dataset()`
Archives test dataset after evaluation.

**Process:**
1. Moves `/test/run_<run_id>/` to `/test/archive/run_<run_id>_YYYYMMDD_HHMMSS/`
2. Preserves ground truth manifest
3. Updates status log

---

## Web UI Integration

### Dataset Preparation Section
**File:** `apps/web/pages/03_Train.py`

**Components:**

#### 1. Dataset Run ID Input
```python
dataset_run_id = st.text_input(
    "Dataset Run ID (e.g., run_0300)",
    value=st.session_state.get("train_run_id", ""),
    help="This run_ID will be used for both validation and test datasets"
)
```

#### 2. Dataset Parameters (Expandable)
```python
with st.expander("⚙️ Dataset Parameters"):
    val_samples = st.number_input("Validation samples per class", value=500)
    test_samples = st.number_input("Test samples per class", value=250)
    val_confidence = st.slider("Validation min confidence", value=0.6)
    val_seed = st.number_input("Validation seed", value=42)
    test_seed = st.number_input("Test seed", value=142)
```

#### 3. Action Buttons
```python
# Button 1: Create Validation Dataset
if st.button("📊 Create Validation Dataset"):
    resp = api_client.create_validation_dataset(
        run_id=dataset_run_id,
        samples_per_class=val_samples,
        min_confidence=val_confidence,
        seed=val_seed,
    )

# Button 2: Create Test Dataset
if st.button("🧪 Create Test Dataset"):
    resp = api_client.create_test_dataset(
        run_id=dataset_run_id,
        samples_per_class=test_samples,
        source="validation",
        seed=test_seed,
    )

# Button 3: Create Both Datasets
if st.button("📦 Create Both Datasets"):
    _create_validation_dataset()
    _create_test_dataset()
```

---

## API Endpoints

### 1. Create Validation Dataset
**Endpoint:** `POST /api/v1/datasets/validation/create`

**File:** `apps/api/app/routers/dataset_control.py`

**Request Schema:**
```python
class CreateValidationDatasetRequest(BaseModel):
    run_id: str
    samples_per_class: int = 500
    min_confidence: float = 0.6
    max_subset: int = 1
    seed: int = 42
```

**Response Schema:**
```python
class DatasetCreationResponse(BaseModel):
    run_id: str
    split: str
    total_samples: int
    samples_per_class: Dict[str, int]
    output_path: str
    manifest_path: Optional[str]
    ground_truth_path: Optional[str]
    status: str
```

**Implementation:**
```python
cmd = [
    sys.executable,
    "-m", "trainer.ingest_affectnet",
    "validation-run",
    "--run-id", request.run_id,
    "--samples-per-class", str(request.samples_per_class),
    "--min-confidence", str(request.min_confidence),
    "--max-subset", str(request.max_subset),
    "--seed", str(request.seed),
]
result = subprocess.run(cmd, cwd=project_root, capture_output=True, timeout=600)
```

**Timeout:** 10 minutes (600 seconds)

---

### 2. Create Test Dataset
**Endpoint:** `POST /api/v1/datasets/test/create`

**File:** `apps/api/app/routers/dataset_control.py`

**Request Schema:**
```python
class CreateTestDatasetRequest(BaseModel):
    run_id: str
    samples_per_class: int = 250
    source: str = "validation"
    seed: int = 142
```

**Implementation:**
```python
cmd = [
    sys.executable,
    "-m", "trainer.manage_test_datasets",
    "create",
    "--run-id", request.run_id,
    "--samples-per-class", str(request.samples_per_class),
    "--source", request.source,
    "--seed", str(request.seed),
]
result = subprocess.run(cmd, cwd=project_root, capture_output=True, timeout=600)
```

---

### 3. Prepare Run Frames
**Endpoint:** `POST /api/v1/media/prepare-run-frames`

**File:** `apps/api/app/routers/ingest.py`

**Request Schema:**
```python
class PrepareRunFramesRequest(BaseModel):
    run_id: Optional[str] = None
    train_fraction: float = 1.0
    dry_run: bool = False
    face_crop: bool = False
    face_target_size: int = 224
    face_confidence: float = 0.6
    # DEPRECATED - do not use:
    split_run: bool = False
    split_train_ratio: float = 0.9
```

**Implementation:**
```python
preparer = DatasetPreparer(str(config.videos_root))
result = preparer.prepare_run_frames(
    run_id=run_id,
    train_fraction=request.train_fraction,
    frames_per_video=10,
    seed=request.seed,
    face_crop=request.face_crop,
    face_target_size=request.face_target_size,
    face_confidence=request.face_confidence,
)
```

---

## Database Schema

### Video Table
```sql
CREATE TABLE video (
    video_id VARCHAR(36) PRIMARY KEY,
    file_path VARCHAR(1024) NOT NULL,
    split VARCHAR CHECK (split IN ('temp', 'train', 'validation', 'test', 'purged')),
    label VARCHAR CHECK (label IN ('happy', 'sad', 'neutral')),
    duration_sec FLOAT,
    fps FLOAT,
    width INTEGER,
    height INTEGER,
    size_bytes BIGINT NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    metadata JSON,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,
    zfs_snapshot VARCHAR(255),
    
    CONSTRAINT uq_video_sha256_size UNIQUE (sha256, size_bytes),
    CONSTRAINT chk_video_split_label_policy CHECK (
        (split IN ('temp', 'test', 'purged') AND label IS NULL) OR
        (split = 'train' AND label IS NOT NULL) OR
        (split = 'validation' AND label IS NULL)
    )
);
```

**Key Constraints:**
- `temp`, `test`, `validation`, `purged` splits: `label` must be NULL
- `train` split: `label` must be NOT NULL
- Unique constraint on (sha256, size_bytes) prevents duplicates

### Extracted Frame Table
```sql
CREATE TABLE extracted_frame (
    frame_id VARCHAR(36) PRIMARY KEY,
    frame_path VARCHAR(1024) NOT NULL,
    source_video_id VARCHAR(36) REFERENCES video(video_id),
    run_id VARCHAR(64),
    label VARCHAR CHECK (label IN ('happy', 'sad', 'neutral')),
    frame_index INTEGER,
    timestamp_sec FLOAT,
    sha256 VARCHAR(64),
    width INTEGER,
    height INTEGER,
    metadata JSON,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

---

## Complete Workflows

### Workflow 1: Create Datasets for New Run

**Objective:** Prepare validation and test datasets for run_0300

**Steps:**

1. **Open Web UI**
   ```
   Navigate to: http://localhost:8501 → Training page
   ```

2. **Create Validation Dataset**
   ```
   Dataset Preparation section:
   - Enter run_ID: run_0300
   - Samples per class: 500
   - Min confidence: 0.6
   - Validation seed: 42
   - Click: 📊 Create Validation Dataset
   ```
   
   **Expected Output:**
   ```
   ✓ Validation dataset created: 1500 images
   {
     "run_id": "run_0300",
     "split": "validation",
     "total_samples": 1500,
     "samples_per_class": {"happy": 500, "sad": 500, "neutral": 500},
     "output_path": "/videos/validation/run/run_0300",
     "manifest_path": "/manifests/run_0300_validation_labels.jsonl",
     "status": "completed"
   }
   ```

3. **Create Test Dataset**
   ```
   Dataset Preparation section:
   - Same run_ID: run_0300
   - Samples per class: 250
   - Test seed: 142 (different from validation)
   - Click: 🧪 Create Test Dataset
   ```
   
   **Expected Output:**
   ```
   ✓ Test dataset created: 750 images (unlabeled)
   {
     "run_id": "run_0300",
     "split": "test",
     "total_samples": 750,
     "samples_per_class": {"happy": 250, "sad": 250, "neutral": 250},
     "output_path": "/videos/test/run_0300",
     "ground_truth_path": "/manifests/run_0300_test_labels.jsonl",
     "status": "completed"
   }
   ```

4. **Verify Datasets**
   ```bash
   ls -la /videos/validation/run/run_0300/ | wc -l  # Should show 1500
   ls -la /videos/test/run_0300/ | wc -l             # Should show 750
   ```

---

### Workflow 2: Extract Training Frames

**Objective:** Extract frames from Luma videos for run_0300

**Steps:**

1. **Configure Frame Extraction**
   ```
   Manifest + Frame Extraction section:
   - Enter run_ID: run_0300 (same as datasets)
   - Train fraction: 1.0 (use all videos)
   - Dry run: OFF
   - Face crop: OFF (unless needed)
   - Split run (DEPRECATED): OFF (must be disabled)
   ```

2. **Execute Extraction**
   ```
   Click: Manual Execute Live
   ```
   
   **Expected Output:**
   ```
   ✓ Manual execute live completed for run: run_0300
   {
     "run_id": "run_0300",
     "train_count": 119110,
     "videos_processed": 11911,
     "frames_per_video": 10,
     "train_manifest": "/manifests/run_0300_train.jsonl"
   }
   ```

3. **Verify Frames**
   ```bash
   ls -la /videos/train/run/run_0300/ | wc -l  # Should show 119110
   ```

---

### Workflow 3: Train Model

**Objective:** Train EfficientNet-B0 model using run_0300 datasets

**Steps:**

1. **Configure Training**
   ```
   ML Runs section:
   - Enter ML Run ID: run_0300 (same as datasets)
   - Checkpoint path: (leave default or specify)
   ```

2. **Launch Training**
   ```
   Click: 🚀 Start Training
   ```
   
   **Training Pipeline:**
   ```
   1. Load training frames: /videos/train/run/run_0300/ (119,110 images)
   2. Load validation dataset: /videos/validation/run/run_0300/ (1,500 images)
      - Auto-detected because run-scoped validation exists
      - No 90/10 split occurs
   3. Train EfficientNet-B0 with frozen backbone
   4. Evaluate on validation set (early stopping)
   5. Run Gate A validation (F1 ≥ 0.84, ECE ≤ 0.08, Brier ≤ 0.16)
   6. Export to ONNX if Gate A passes
   ```

3. **Final Evaluation**
   ```
   After training completes:
   - Click: 🧪 Start Test
   - Evaluates on /videos/test/run_0300/ (750 unlabeled images)
   - Compares predictions to ground truth manifest
   - Generates final metrics report
   ```

---

## Fixes Applied in v08.4.3

### Fix 1: Removed 90/10 Split (COMPLETED)

**Files Modified:**
- `trainer/prepare_dataset.py` - Removed `split_run_dataset()` method
- `apps/api/app/routers/ingest.py` - Removed `split_run` parameter
- `apps/web/pages/03_Train.py` - Removed split toggle and related controls

**Reason:** Split is unnecessary when using dedicated AffectNet validation datasets. Caused directory clutter and wasted 10% of training data.

### Fix 2: Corrected Test Dataset Path (COMPLETED)

**Changed From:**
```
/videos/test/affectnet_test_dataset/run/<run_id>/
```

**Changed To:**
```
/videos/test/run/<run_id>/
```

**Files Modified:**
- `trainer/manage_test_datasets.py` - Updated output path
- `trainer/ingest_affectnet.py` - Updated test dataset creation
- `apps/api/app/routers/dataset_control.py` - Updated response path
- All references to `affectnet_test_dataset` removed

**Reason:** Simplified directory structure, consistent with validation dataset pattern.

### Fix 3: Corrected Validation Manifest Path

**Changed From:**
```
/manifests/<run_id>_valid_ds_labeled.jsonl
```

**Changed To:**
```
/manifests/<run_id>_validation_labels.jsonl
```

**Files Modified:**
- `apps/api/app/routers/dataset_control.py` - Updated manifest path in response

---

## Legacy Code Identified (No Changes Made)

### 1. Legacy Validation Ingestion
**File:** `trainer/ingest_affectnet.py`

**Method:** `ingest_validation_set()`

**Issue:** Copies images to `/train/<label>/` instead of run-scoped directory

**CLI Command:** `python -m trainer.ingest_affectnet validation`

**Recommendation:** Remove this method entirely. Use `create_validation_dataset()` instead.

**Impact:** Low - not used by web UI, only accessible via CLI

---

### 2. Legacy Dataset Creation Script
**File:** `trainer/create_affectnet_datasets.py`

**Issue:** Copies validation images to `/test/validation/<emotion>/` (wrong location)

**Functions:**
- `prepare_validation_set()` - Copies to `/test/validation/{class_name}/`
- `prepare_test_set()` - Copies to `/test/{class_name}/`

**Recommendation:** Deprecate or remove entire script. Replaced by:
- `trainer/ingest_affectnet.py` (validation datasets)
- `trainer/manage_test_datasets.py` (test datasets)

**Impact:** Medium - may be used by external scripts or documentation

---

### 3. Legacy Train Ingestion
**File:** `trainer/ingest_affectnet.py`

**Method:** `ingest_train_set()`

**Issue:** Copies AffectNet training images to `/train/<label>/` (mixes with Luma videos)

**CLI Command:** `python -m trainer.ingest_affectnet train`

**Recommendation:** Keep but document clearly that it's for augmenting training data, not for validation/test

**Impact:** Low - intentional feature for adding AffectNet training data

---

### 4. Consolidated Dataset Builder
**File:** `trainer/build_consolidated_dataset.py`

**Issue:** Complex script that mixes Luma videos + AffectNet images, then splits 90/10

**Recommendation:** Deprecate in favor of:
- Frame extraction for Luma videos
- Separate AffectNet validation/test dataset creation

**Impact:** Medium - may be used for specific experiments

---

### 5. Split Run Dataset Script
**File:** `trainer/split_run_dataset.py`

**Issue:** Standalone script for 90/10 splitting (now removed from main pipeline)

**Recommendation:** Remove entirely (part of split removal)

**Impact:** Low - redundant with removed `split_run_dataset()` method

---

### 6. Test Dataset Archive Path
**File:** `trainer/manage_test_datasets.py`

**Method:** `archive_test_dataset()`

**Current Path:** `/test/archive/run_<run_id>_YYYYMMDD_HHMMSS/`

**Issue:** Should this be `/test/run/archive/` for consistency?

**Recommendation:** Review archive path structure for consistency

**Impact:** Low - archiving works correctly, just path organization question

---

## Model Type Differentiation

The system supports three model types with different training and evaluation requirements:

### Base Model (HSEmotion Pretrained)
**Purpose:** Baseline evaluation using original HSEmotion weights

**Checkpoint:** `/checkpoints/hsemotion/enet_b0_8_best_vgaf.pth`

**Dataset Requirements:**
- Training: ❌ Not needed
- Validation: ❌ Not needed  
- Test: ✅ Required (AffectNet test set)

**Available Operations:**
- Training: ❌ Disabled
- Validation: ❌ Disabled
- Test: ✅ Enabled

**Use Case:** Establish baseline performance metrics for comparison

---

### Variant 1 (Base + Luma Synthetic Videos)
**Purpose:** Fine-tune HSEmotion on Luma-generated synthetic emotion videos

**Checkpoint:** `/checkpoints/efficientnet_b0_3cls/best_model.pth`

**Dataset Requirements:**
- Training: ✅ Required (119,110 Luma frames from 11,911 videos)
- Validation: ✅ Required (1,500 AffectNet images)
- Test: ✅ Required (750 AffectNet images)

**Available Operations:**
- Training: ✅ Enabled (full pipeline: train → evaluate → Gate A)
- Validation: ✅ Enabled (evaluate on AffectNet validation set)
- Test: ✅ Enabled (final evaluation on AffectNet test set)

**Use Case:** Primary model for emotion classification on Reachy robot

---

### Variant 2 (Fine-tuned Variant 1)
**Purpose:** Further weight adjustment/fine-tuning of Variant 1 model

**Checkpoint:** `/checkpoints/efficientnet_b0_3cls_finetuned/best_model.pth`

**Dataset Requirements:**
- Training: ❌ Not needed (no new training data)
- Validation: ✅ Required (1,500 AffectNet images)
- Test: ✅ Required (750 AffectNet images)

**Available Operations:**
- Training: ❌ Disabled (uses existing Variant 1 checkpoint)
- Validation: ✅ Enabled (evaluate fine-tuned weights)
- Test: ✅ Enabled (final evaluation)

**Use Case:** Optimize Variant 1 performance through hyperparameter tuning or weight adjustment

---

### Web UI Implementation

**Model Type Selector:**
```
Model Type: [Variant 1 ▼]
  • Base Model (HSEmotion pretrained)
  • Variant 1 (Base + Luma synthetic)
  • Variant 2 (Fine-tuned Variant 1)
```

**Button Availability Matrix:**

| Model Type | 🚀 Start Training | 📊 Start Validation | 🧪 Start Test |
|------------|-------------------|---------------------|---------------|
| Base Model | ❌ Disabled | ❌ Disabled | ✅ Enabled |
| Variant 1 | ✅ Enabled | ✅ Enabled | ✅ Enabled |
| Variant 2 | ❌ Disabled | ✅ Enabled | ✅ Enabled |

**Workflow Examples:**

**Base Model Evaluation:**
1. Create test dataset: `run_0300`
2. Select "Base Model" from dropdown
3. Click "🧪 Start Test"
4. Result: Baseline metrics using pretrained weights

**Variant 1 Full Pipeline:**
1. Create all three datasets: `run_0300`
2. Select "Variant 1" from dropdown
3. Click "🚀 Start Training" → trains on Luma frames
4. Click "📊 Start Validation" → evaluates on AffectNet validation
5. Click "🧪 Start Test" → final evaluation on AffectNet test
6. Result: Trained model checkpoint saved

**Variant 2 Fine-tuning:**
1. Create validation + test datasets: `run_0300`
2. Select "Variant 2" from dropdown
3. Adjust checkpoint path to Variant 1 output
4. Click "📊 Start Validation" → evaluate fine-tuned weights
5. Click "🧪 Start Test" → final evaluation
6. Result: Fine-tuned model performance metrics

---

## Summary

This guide provides complete coverage of:
- ✅ All dataset types and their purposes
- ✅ Complete directory structure
- ✅ All dataset creation scripts and their logic
- ✅ Web UI integration and workflows
- ✅ API endpoints and schemas
- ✅ Database schema and constraints
- ✅ Step-by-step workflows for common tasks
- ✅ Fixes applied in v08.4.3
- ✅ Legacy code identified for future cleanup

**Next Steps:**
1. Test all three dataset creation buttons with new run_ID
2. Review legacy code recommendations
3. Approve additional cleanup changes
4. Update requirements.md and memory bank with new paths
