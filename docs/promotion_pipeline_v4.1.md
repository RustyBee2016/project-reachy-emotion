# Video Promotion & Dataset Creation Pipeline v4.1

> **Project**: Reachy_Local_08.4.2
> **Date**: 2026-03-31
> **Status**: Final pre-training verification
> **Author**: Claude Opus 4.6 + Russell Bray

---

## Table of Contents

1. [Overview & Data Flow](#1-overview--data-flow)
2. [Storage Layout](#2-storage-layout)
3. [Phase A: Video Ingestion into /videos/temp](#3-phase-a-video-ingestion-into-videostemp)
4. [Phase B: Labeling](#4-phase-b-labeling)
5. [Phase C: Promotion (temp -> train/test)](#5-phase-c-promotion-temp---traintest)
6. [Phase D: Manual Video Handling](#6-phase-d-manual-video-handling)
7. [Phase E: Frame Extraction](#7-phase-e-frame-extraction-prepare_training_dataset)
8. [Phase F: Train/Validation Splitting](#8-phase-f-trainvalidation-splitting-split_run_dataset)
9. [Phase G: Dataset Hash & MLflow Logging](#9-phase-g-dataset-hash--mlflow-logging)
10. [Phase H: PyTorch DataLoader Integration](#10-phase-h-pytorch-dataloader-integration)
11. [Phase I: Training Launch](#11-phase-i-training-launch)
12. [Appendix A: API Endpoint Reference](#appendix-a-api-endpoint-reference)
13. [Appendix B: Database Tables](#appendix-b-database-tables)
14. [Appendix C: Key Scripts & Files Index](#appendix-c-key-scripts--files-index)

---

## 1. Overview & Data Flow

The promotion pipeline moves videos from ingestion through to model-ready frame datasets in six sequential stages. There are **two ingestion paths** (web-app-generated and manually-generated videos) that converge at the `train/<emotion>/` level before frame extraction.

```
                         ┌─────────────────────────┐
                         │    VIDEO GENERATION      │
                         │                          │
                 ┌───────┤  Path 1: Luma AI / Upload│
                 │       │  (Streamlit Web App)     │
                 │       └─────────────────────────┘
                 │
                 ▼
        /videos/temp/<uuid>.mp4
                 │
                 │  Phase B: Label in Streamlit UI
                 │  Phase C: POST /api/v1/media/promote
                 │           (atomic file move + DB update)
                 │
                 ▼
        /videos/train/<emotion>/<video>.mp4     ◄─── Path 2: Manual copy + rename
                 │                                    (reconcile_videos.py)
                 │
                 │  Phase E: POST /api/v1/ingest/prepare-run-frames
                 │           (10 random frames extracted per video)
                 │
                 ▼
        /videos/train/run/<run_id>/*.jpg         (flat consolidated frames)
                 │
                 │  Phase F: split_run_dataset()
                 │           (stratified 90/10 train/valid split)
                 │
                 ├──► /videos/train/run/<run_id>/train_ds_<run_id>/*.jpg
                 │
                 └──► /videos/train/run/<run_id>/valid_ds_<run_id>/*.jpg
                                │
                                │  Phase H: EmotionDataset + DataLoader
                                │  Phase I: Training launch
                                ▼
                         EfficientNet-B0 Training
```

### Two Video Ingestion Paths

| Path | Source | Arrives At | Next Step |
|------|--------|------------|-----------|
| **Path 1** (Web App) | Luma AI generation or file upload via Streamlit | `/videos/temp/` | Label -> Promote via API |
| **Path 2** (Manual) | Manually recorded/downloaded videos copied by the user | `/videos/train/<emotion>/` directly | Run `reconcile_videos.py` to rename + register in DB |

---

## 2. Storage Layout

**Root**: `/mnt/videos/` (configurable via `REACHY_VIDEOS_ROOT` environment variable)

```
/mnt/videos/
├── temp/                                    # Incoming videos awaiting review
│   ├── <uuid>.mp4                           # Web-app-generated (Luma AI)
│   ├── <uploaded_name>.mp4                  # User-uploaded files
│   └── ...
│
├── train/                                   # Promoted source videos by emotion
│   ├── happy/
│   │   ├── happy_luma_20260122_003058.mp4   # Standardized naming
│   │   ├── happy_luma_20260215_141200.mp4
│   │   └── ...
│   ├── sad/
│   │   ├── sad_luma_20260123_091500.mp4
│   │   └── ...
│   ├── neutral/
│   │   ├── neutral_luma_20260124_110000.mp4
│   │   └── ...
│   └── run/                                 # Run-scoped extracted frame datasets
│       ├── run_0001/
│       │   ├── happy_luma_20260122_f00_idx00042.jpg    # Flat extracted frames
│       │   ├── happy_luma_20260122_f01_idx00087.jpg
│       │   ├── sad_luma_20260123_f00_idx00015.jpg
│       │   ├── neutral_luma_20260124_f00_idx00033.jpg
│       │   ├── ...
│       │   ├── train_ds_run_0001/           # After split: training frames
│       │   │   ├── happy_luma_20260122_f00_idx00042.jpg
│       │   │   ├── sad_luma_20260123_f00_idx00015.jpg
│       │   │   └── ...
│       │   └── valid_ds_run_0001/           # After split: validation frames
│       │       ├── luma_20260122_f09_idx00198.jpg       # Label prefix stripped
│       │       ├── luma_20260123_f07_idx00145.jpg
│       │       └── ...
│       └── run_0002/
│           └── ...
│
├── test/                                    # Test split videos
│   ├── <uuid>.mp4                           # Promoted test videos (no label)
│   ├── affectnet_test_dataset/              # Fixed external test set
│   └── run_0001/                            # Legacy run-scoped test (unused)
│
├── manifests/                               # JSONL manifest files
│   ├── run_0001_train.jsonl                 # Canonical extraction manifest
│   ├── run_0001_test.jsonl                  # Test manifest (empty for frame-first)
│   ├── run_0001_train_ds.jsonl              # Training split manifest (after split)
│   ├── run_0001_valid_ds_labeled.jsonl      # Validation with labels preserved
│   └── run_0001_valid_ds_unlabeled.jsonl    # Validation without labels (prevents leakage)
│
└── thumbs/                                  # Video thumbnails (served by Nginx)
    └── <video_id>.jpg
```

### Configuration Source

**File**: `apps/api/app/config.py` (class `AppConfig`)

| Setting | Env Var | Default |
|---------|---------|---------|
| `videos_root` | `REACHY_VIDEOS_ROOT` | `/mnt/videos` |
| `temp_dir` | `REACHY_TEMP_DIR` | `temp` |
| `train_dir` | `REACHY_TRAIN_DIR` | `train` |
| `test_dir` | `REACHY_TEST_DIR` | `test` |
| `thumbs_dir` | `REACHY_THUMBS_DIR` | `thumbs` |
| `manifests_dir` | `REACHY_MANIFESTS_DIR` | `manifests` |

**Note**: The `reconcile_videos.py` script uses a hardcoded path (`/media/rusty_admin/project_data/reachy_emotion/videos`). The API and trainer use the configurable `REACHY_VIDEOS_ROOT`.

---

## 3. Phase A: Video Ingestion into /videos/temp

Videos arrive in `/videos/temp/` through three mechanisms:

### A1. Luma AI Video Generation (Web App)

**UI**: `apps/web/landing_page.py` (lines 386-502)

1. User enters a text prompt in Streamlit (e.g., "a happy girl eating lunch")
2. Clicks "Generate Video"
3. `LumaVideoGenerator` client calls Luma AI Dream Machine API:
   - Model: `ray-2`
   - Resolution: `720p`
   - Duration: `5s`
   - Aspect ratio: `3:4`
4. Video is downloaded and saved to `/mnt/videos/temp/<filename>.mp4`
5. Optionally, an n8n Ingest Agent webhook is triggered for metadata extraction

**Config**:
```
LUMAAI_API_KEY=<key>
VIDEO_DATA_DIR=/mnt/videos/temp
```

### A2. Manual File Upload (Web App)

**UI**: `apps/web/landing_page.py` (lines 344-379)

1. User uploads a file via `st.file_uploader()` in Streamlit
2. Streamlit calls `api_client.upload_video(file_name, file_bytes)`
3. API client sends the file to the gateway: `POST /api/v1/ingest/upload`

### A3. Ingest API (Backend Registration)

**Endpoint**: `POST /api/v1/ingest/upload`
**Handler**: `apps/api/app/routers/ingest.py` (lines 722-800)

**Steps**:
1. Writes the video file to `temp/` directory
2. Computes SHA256 hash of the file contents
3. Extracts metadata via FFprobe (duration, fps, width, height)
4. Generates a thumbnail to `/thumbs/<video_id>.jpg`
5. Inserts a new row into the `video` table:
   - `video_id`: auto-generated UUID
   - `split`: `"temp"`
   - `label`: `NULL`
   - `sha256`, `size_bytes`: computed from file
   - `duration_sec`, `fps`, `width`, `height`: from FFprobe
6. Returns `video_id` + file path to the caller

### A4. n8n Ingest Agent (Agent 1)

**Workflow**: `n8n/workflows/ml-agentic-ai_v.3/01_ingest_agent.json`
**Webhook**: `POST /webhook/video_gen_hook`

- Normalizes the ingest payload (source_url, label, metadata)
- Calls `POST /api/v1/ingest/pull` on the Media Mover API
- Extracts correlation_id and idempotency key
- Handles duplicates gracefully (no double-ingest)

---

## 4. Phase B: Labeling

Before promotion, videos in `temp/` must be labeled with an emotion class.

### B1. Labeling UI

**File**: `apps/web/pages/02_Label.py`

1. User selects the `temp` split to browse unlabeled videos
2. Each video is displayed with its metadata (video_id, file_path, size, mtime)
3. User selects an emotion label from a dropdown: `[happy, sad, neutral]`
4. Two actions are available:
   - **Submit Classification** -- Promotes to train split with the selected label
   - **Reject / Incorrect** -- Calls `reject_video()` to redact/discard

### B2. Video Management UI

**File**: `apps/web/pages/05_Video_Management.py`

Provides batch promotion capabilities:
1. List videos from any split (temp, train, test, purged)
2. Select one or more videos
3. Choose destination split (train or test) and emotion label
4. Promote with dry-run toggle for preview
5. Calls `api_client.promote()` for each selected video

### B3. n8n Labeling Agent (Agent 2)

**Workflow**: `n8n/workflows/ml-agentic-ai_v.3/02_labeling_agent.json`
**Webhook**: `POST /webhook/label`

- Validates video_id, label, action
- Fetches video metadata from database
- Inserts a `label_event` record (idempotent via `idempotency_key`)
- Updates `video.label` field
- Routes to: `label_only`, `promote_train`, `promote_test`, or `discard`

### B4. Database: label_event Table

Every labeling action is recorded in the `label_event` table for audit:

| Column | Type | Description |
|--------|------|-------------|
| `event_id` | INT (PK) | Auto-increment |
| `video_id` | STRING (FK) | References `video.video_id` |
| `label` | ENUM | `happy`, `sad`, or `neutral` |
| `action` | STRING | Action taken (e.g., `promote_train`) |
| `rater_id` | STRING | Who labeled it (optional) |
| `idempotency_key` | STRING (UNIQUE) | Prevents duplicate labeling events |
| `correlation_id` | STRING | Distributed tracing |
| `created_at` | TIMESTAMPTZ | When labeled |

---

## 5. Phase C: Promotion (temp -> train/test)

Promotion is the controlled movement of a video from `temp/` to either `train/<emotion>/` or `test/`.

### C1. Canonical Endpoint

**Endpoint**: `POST /api/v1/media/promote`
**Handler**: `apps/api/routers/media.py`
**HTTP Headers**: `Idempotency-Key: <uuid>` (optional, prevents duplicate promotions)

**Request Body** (adapter mode):
```json
{
    "video_id": "<uuid>",
    "dest_split": "train",
    "label": "happy",
    "correlation_id": "tracking-uuid",
    "dry_run": false
}
```

**Constraints**:
- `dest_split`: must be `"train"` or `"test"`
- `label`: required when `dest_split = "train"`, must be `"happy"`, `"sad"`, or `"neutral"`
- `label`: must be `NULL` when `dest_split = "test"`

### C2. Video Lookup (Multi-Stage Resolution)

The handler resolves `video_id` through a 4-stage fallback:

| Stage | Method | Description |
|-------|--------|-------------|
| 1 | Direct DB lookup | Query `Video` table by `video_id` (UUID) |
| 2 | Filename/stem match | SQL `WHERE file_path LIKE '%/<filename>'` |
| 3 | Filesystem glob | Scan `temp/` directory for matching filenames (tries `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`) |
| 4 | Auto-register | If file found on disk but not in DB: compute SHA256, insert new `Video` row, then promote |

### C3. Idempotency & Deduplication

**Idempotency** (via `Idempotency-Key` header):
1. Client sends a unique key (e.g., UUID) in the `Idempotency-Key` header
2. Server queries `promotion_log.idempotency_key` for an existing entry
3. If found: returns the cached result with `idempotent_replay: true` (no mutation)
4. If not found: proceeds with promotion, stores the key in the new `PromotionLog` row
5. Database enforces uniqueness via `UNIQUE(idempotency_key)` constraint

**Deduplication** (by video state):
- If the video is already in the target split with the correct label: returns success as a no-op (`already_in_target: true`)
- If the video is in a different split (not `temp`): returns `409 Conflict`

**SHA256 Deduplication** (auto-registration fallback):
- If a file is found on disk but not in DB, the handler computes SHA256
- If the insert fails due to `UNIQUE(sha256, size_bytes)` constraint, reuses the existing video record

### C4. Atomic File Move (FileMover)

**File**: `apps/api/app/fs/media_mover.py` (class `FileMover`)

The `stage_to_train()` method performs an atomic two-phase rename:

```
Step 1: os.replace(source, tmp_destination)      # temp/clip.mp4 -> train/happy/clip.tmp-<uuid>
Step 2: fsync(tmp_destination)                    # Force write to disk
Step 3: os.replace(tmp_destination, destination)  # train/happy/clip.tmp-<uuid> -> train/happy/clip.mp4
Step 4: fsync(destination.parent)                 # Force directory metadata to disk
```

**Key properties**:
- `os.replace()` is atomic on POSIX (single rename syscall)
- Intermediate `.tmp-<uuid>` file prevents partial writes
- `fsync()` on file and directory ensures durability after power loss
- On failure, the temporary file is cleaned up

**Rollback**: If the DB commit fails after the file move, the handler reverses the move:
```python
file_mover.rollback([transition])  # moves train/happy/clip.mp4 back to temp/clip.mp4
```

### C5. Database Mutations

After the file move succeeds:

1. **Video table** update:
   ```sql
   UPDATE video SET
       split = 'train',
       label = 'happy',
       file_path = 'train/happy/clip.mp4'
   WHERE video_id = '<uuid>';
   ```

2. **PromotionLog** insert:
   ```sql
   INSERT INTO promotion_log
       (video_id, from_split, to_split, intended_label,
        actor, success, idempotency_key, correlation_id, dry_run)
   VALUES
       ('<uuid>', 'temp', 'train', 'happy',
        'media_mover_promote', true, '<idem-key>', '<corr-id>', false);
   ```

3. Both operations are committed in a single DB transaction. If the commit fails, the file move is rolled back.

### C6. Structured Logging for Reconciliation

Two paired log entries bracket every promotion:

```
media_mover_promote_pending    → emitted BEFORE file move
media_mover_promote_committed  → emitted AFTER DB commit
```

The Reconciler Agent (n8n Agent 4) detects incomplete promotions by finding `pending` entries without matching `committed` entries.

### C7. Dry-Run Mode

When `dry_run: true`:
- `FileMover.plan_stage_to_train()` is called instead of `stage_to_train()`
- Validates that the source file exists and the destination path is valid
- Returns a `FileTransition` object describing what *would* happen
- No file is moved, no DB row is updated

### C8. Legacy Deprecated Endpoints

| Endpoint | Status | Message |
|----------|--------|---------|
| `POST /api/v1/promote/stage` | `410 GONE` | "Use POST /api/v1/media/promote with dest_split='train'" |
| `POST /api/v1/promote/sample` | `410 GONE` | "Use run-scoped frame dataset preparation instead" |

**Handler**: `apps/api/app/routers/promote.py`

The old flow was `temp -> dataset_all -> train/test`. This has been replaced by the direct `temp -> train/<emotion>` flow.

### C9. Response Format

**Success (200 OK)**:
```json
{
    "status": "ok",
    "video_id": "<uuid>",
    "src": "temp/clip.mp4",
    "dst": "train/happy/clip.mp4",
    "dry_run": false,
    "adapter_mode": "adapter",
    "idempotent_replay": false,
    "already_in_target": false
}
```

**Error Codes**:

| Code | Condition |
|------|-----------|
| `400` | Missing required fields, invalid split or label |
| `404` | Video not found in DB or on filesystem |
| `409` | Video already promoted to a different split/label |
| `422` | Train promotion without a valid label |
| `500` | Filesystem or database failure |

---

## 6. Phase D: Manual Video Handling

Videos generated *outside* the web app (e.g., screen recordings, downloaded clips) must be manually placed into the correct `train/<emotion>/` folder and registered in the database.

### D1. Manual Copy Process

1. **Copy the video** to the correct emotion subfolder:
   ```bash
   cp /path/to/my_video.mp4 /mnt/videos/train/happy/
   cp /path/to/another.mp4 /mnt/videos/train/sad/
   ```

2. **Run the reconciliation script** to rename and register:
   ```bash
   # Preview changes (dry-run)
   python scripts/reconcile_videos.py --dry-run

   # Apply changes
   python scripts/reconcile_videos.py
   ```

### D2. Reconciliation Script

**File**: `scripts/reconcile_videos.py`

The script performs three sequential steps:

#### Step 1: Rename Videos

**Function**: `step1_rename_videos(dry_run)`

Scans each `train/<emotion>/` directory and renames files that lack the standard `<emotion>_` prefix:

| Original Name | Standardized Name |
|---------------|-------------------|
| `2026-01-22T00-30-58_create_a.mp4` | `happy_luma_20260122_003058.mp4` |
| `my_custom_video.mp4` | `happy_luma_my_custom_video.mp4` |
| `happy_existing.mp4` | *(skipped -- already prefixed)* |

**Naming logic** (`_make_luma_name()`):
- Extracts ISO timestamp if present (`YYYY-MM-DDTHH-MM-SS`) and reformats it
- If file already has an emotion prefix, leaves it unchanged
- Otherwise, prefixes with `<emotion>_luma_<stem>.mp4`

#### Step 2: Register in Database

**Function**: `step2_register_videos(dry_run)`

For each `.mp4` file in `train/<emotion>/`:
1. Checks if `file_path` already exists in the `video` table
2. If missing, computes:
   - SHA256 hash of file contents
   - Video metadata via FFprobe (duration, fps, width, height, size_bytes)
3. Inserts a new `video` row:
   - `video_id`: new UUID
   - `split`: `"train"`
   - `label`: the emotion folder name (e.g., `"happy"`)
   - `file_path`: relative path (e.g., `train/happy/happy_luma_20260122_003058.mp4`)

#### Step 3: Clean Up Orphans

**Function**: `step3_cleanup_orphans(dry_run)`

Queries all `video` rows where `split = 'train'` and deletes any whose `file_path` no longer exists on disk. This handles cases where videos were manually removed from the filesystem but not from the database.

### D3. Configuration (Reconciliation Script)

The script uses hardcoded paths:
```python
VIDEOS_ROOT = Path("/media/rusty_admin/project_data/reachy_emotion/videos")
TRAIN_DIR = VIDEOS_ROOT / "train"
EMOTIONS = ["happy", "sad", "neutral"]
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv"}
DB_DSN = "host=localhost port=5432 dbname=reachy_emotion user=reachy_dev ..."
```

---

## 7. Phase E: Frame Extraction (prepare_training_dataset)

Once source videos exist in `train/<emotion>/` (from either Path 1 or Path 2), frames are extracted to create the run-scoped image dataset.

### E1. Trigger Mechanisms

Frame extraction can be triggered in three ways:

| Trigger | Entry Point |
|---------|-------------|
| **Streamlit UI** | `apps/web/pages/03_Train.py` -- "Prepare 10-Frame Run" button |
| **API Endpoint** | `POST /api/v1/ingest/prepare-run-frames` |
| **Python Direct** | `DatasetPreparer(base_path).prepare_training_dataset(...)` |

### E2. API Endpoint

**Endpoint**: `POST /api/v1/ingest/prepare-run-frames`
**Handler**: `apps/api/app/routers/ingest.py` (lines 1134-1286)

**Request Body**:
```json
{
    "run_id": null,
    "train_fraction": 0.7,
    "seed": null,
    "dry_run": false,
    "face_crop": false,
    "face_target_size": 224,
    "face_confidence": 0.6,
    "split_run": false,
    "split_train_ratio": 0.9,
    "strip_valid_labels": true,
    "persist_valid_metadata": false,
    "correlation_id": null
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `run_id` | string or null | null (auto-generated) | Run identifier (format: `run_XXXX`) |
| `seed` | int or null | null (derived from run_id) | Random seed for reproducibility |
| `dry_run` | bool | false | Validate without writing frames |
| `face_crop` | bool | false | Enable face detection + cropping |
| `face_target_size` | int | 224 | Output frame size (square, pixels) |
| `face_confidence` | float | 0.6 | Minimum face detection confidence |
| `split_run` | bool | false | Also perform train/valid split after extraction |
| `split_train_ratio` | float | 0.9 | Train fraction when splitting |
| `strip_valid_labels` | bool | true | Remove emotion prefix from validation filenames |
| `persist_valid_metadata` | bool | false | Write frame metadata to `extracted_frame` DB table |

### E3. DatasetPreparer Class

**File**: `trainer/prepare_dataset.py` (class `DatasetPreparer`)

**Constants**:
```python
EMOTIONS = ("happy", "sad", "neutral")
FRAMES_PER_VIDEO = 10
RUN_ID_PATTERN = re.compile(r"^run_\d{4}$")
FACE_DETECTOR_NAME = "opencv_dnn_res10_ssd"
```

**Initialization**: `DatasetPreparer(base_path="/mnt/videos")`

Sets up paths:
- `self.train_path` = `/mnt/videos/train/`
- `self.train_runs_path` = `/mnt/videos/train/run/`
- `self.test_path` = `/mnt/videos/test/`
- `self.manifests_path` = `/mnt/videos/manifests/`

Creates all directories if they don't exist.

### E4. Run ID Resolution

**Method**: `resolve_run_id(run_id)`

- If `run_id` is provided: validates against pattern `^run_\d{4}$`, returns as-is
- If `run_id` is `None`: calls `_next_run_id()` to auto-generate

**Method**: `_next_run_id()`

Scans multiple locations to find the highest existing run index:

1. `train/run/run_XXXX/` directories
2. Nested `train/run/*/run_XXXX/` directories (legacy)
3. Root-level `train_run_XXXX/` and `test_run_XXXX/` directories (legacy)
4. `manifests/run_*_train.jsonl` manifest files

Returns `run_{max_index + 1:04d}` (e.g., if `run_0005` is the highest, returns `run_0006`).
Maximum: `run_9999` (raises `ValueError` if exceeded).

### E5. Seed Determinism

If no explicit seed is provided, a deterministic seed is computed from the run_id:
```python
seed = int(hashlib.md5(run_id.encode()).hexdigest(), 16) % (2**31)
```

This ensures that re-running the same `run_id` with the same source videos produces identical frame selections (assuming source videos haven't changed).

### E6. Source Video Collection

**Method**: `_collect_source_videos()`

Iterates over each emotion directory and collects `.mp4` files:

```
train/happy/*.mp4  -> collected["happy"] = [path1, path2, ...]
train/sad/*.mp4    -> collected["sad"]   = [path1, path2, ...]
train/neutral/*.mp4 -> collected["neutral"] = [path1, path2, ...]
```

**Validation** (`_validate_source_videos()`): Raises `ValueError` if any emotion class has zero source videos. All three classes must be populated before extraction can proceed.

### E7. Frame Extraction

**Method**: `_extract_run_frames()`

1. Creates the output directory: `train/run/<run_id>/`
2. If the directory already exists:
   - If it contains `train_ds_*` or `valid_ds_*` subdirectories (split already applied), raises an error. Call `prune_run_artifacts()` first.
   - Otherwise, deletes and recreates the directory (clean re-extraction).
3. Iterates over each emotion and each video within that emotion.
4. For each video, calls `_extract_random_frames_from_video()`.

**Method**: `_extract_random_frames_from_video()`

For each source video:

1. Opens the video with `cv2.VideoCapture()`
2. Gets total frame count via `CAP_PROP_FRAME_COUNT`
3. Selects frame indices:
   - If `total_frames >= 10`: `rng.sample(range(total_frames), 10)` (no replacement)
   - If `total_frames < 10`: `rng.randrange(total_frames)` repeated 10 times (with replacement)
4. For each selected frame index:
   a. Seeks to the frame: `cap.set(CAP_PROP_POS_FRAMES, frame_idx)`
   b. Reads the frame: `cap.read()`
   c. **If `face_crop=True`**:
      - Runs face detection via OpenCV DNN SSD (ResNet-10, 300x300)
      - If no face detected above `face_confidence` threshold: **frame is skipped**
      - If face detected: crops to face bounding box + 20% margin, resizes to `target_size x target_size`
   d. **If `face_crop=False`**: uses the full frame as-is
   e. Saves the frame as JPEG: `cv2.imwrite()`

**Frame Naming Convention**:
```
{label}_{video_stem}_f{order_idx:02d}_idx{frame_idx:05d}.jpg
```
Example: `happy_luma_20260122_f03_idx00087.jpg`

| Component | Format | Description |
|-----------|--------|-------------|
| `label` | string | Emotion class (`happy`, `sad`, `neutral`) |
| `video_stem` | string | Source video filename without extension |
| `f{NN}` | 2-digit | Order index within this video's extraction (f00-f09) |
| `idx{NNNNN}` | 5-digit | Absolute frame position in the source video |

### E8. Face Detection Details

**Model**: OpenCV DNN SSD (ResNet-10)
**Files Required**:
- `trainer/models/face_detector/deploy.prototxt`
- `trainer/models/face_detector/res10_300x300_ssd_iter_140000.caffemodel`

**Environment Overrides** (optional):
- `REACHY_FACE_DNN_PROTO_PATH`
- `REACHY_FACE_DNN_MODEL_PATH`

**Detection Process**:
1. Resize frame to 300x300
2. Create blob with normalization values `(104.0, 177.0, 123.0)`
3. Run forward pass through the SSD network
4. Select the detection with highest confidence above threshold
5. Expand bounding box by 20% margin on each side
6. Clamp to frame boundaries
7. Return `{x1, y1, x2, y2, w, h, confidence}` or `None`

**Policy**: When `face_crop=True` and no face is detected, the frame is **skipped silently** (not saved). There is no fallback to full-frame extraction.

### E9. Manifest Generation

**Method**: `_generate_manifests(run_id, train_entries, test_entries)`

Creates two JSONL files:

1. `manifests/<run_id>_train.jsonl` -- one JSON line per extracted frame
2. `manifests/<run_id>_test.jsonl` -- empty in the frame-first workflow

**Each train manifest entry**:
```json
{
    "video_id": "luma_20260122",
    "path": "/mnt/videos/train/run/run_0001/happy_luma_20260122_f03_idx00087.jpg",
    "label": "happy",
    "source_video": "/mnt/videos/train/happy/happy_luma_20260122_003058.mp4",
    "face_bbox": {"x": 45, "y": 30, "w": 120, "h": 140},
    "face_confidence": 0.92,
    "face_detector": "opencv_dnn_res10_ssd",
    "face_crop": true,
    "target_size": 224,
    "source_frame_shape": [720, 540]
}
```

The `face_*` fields are only present when `face_crop=True` and a face was detected.

### E10. Dataset Hash

**Method**: `calculate_dataset_hash(run_id)`

After extraction, a SHA256 hash is computed from the dataset structure:
- Iterates all `.jpg` files in `train/run/<run_id>/` recursively
- For each file, feeds `relative_path + file_size` into the hasher
- Returns hex digest

**Note**: This is a path+size hash, NOT a content hash. It is fast but will not detect pixel-level changes if a file is overwritten with different content at the same size.

### E11. Return Value

```python
{
    "run_id": "run_0001",
    "train_count": 300,          # Total frames extracted
    "test_count": 0,             # Always 0 in frame-first workflow
    "videos_processed": 30,      # Total source videos across all emotions
    "frames_per_video": 10,      # Constant: FRAMES_PER_VIDEO
    "seed": 1234567890,
    "dataset_hash": "a1b2c3d4...",
    "face_crop": false,
    "target_size": 224,
    "face_confidence": 0.6
}
```

---

## 8. Phase F: Train/Validation Splitting (split_run_dataset)

After frame extraction produces a flat directory of frames in `train/run/<run_id>/`, the split step partitions them into separate training and validation subdirectories.

### F1. Trigger

- **API**: Called automatically when `split_run: true` in the prepare-run-frames request
- **Python Direct**: `DatasetPreparer.split_run_dataset(run_id, train_ratio=0.9)`

### F2. Method Signature

```python
def split_run_dataset(
    self,
    run_id: str,
    *,
    train_ratio: float = 0.9,     # 90% train, 10% validation
    seed: Optional[int] = None,   # Derived from run_id if None
    strip_valid_labels: bool = True,  # Remove emotion prefix from validation filenames
) -> Dict[str, Any]:
```

### F3. Splitting Process (Step by Step)

1. **Read flat frames**: Collects all `.jpg` files directly under `train/run/<run_id>/`
   - Raises `ValueError` if no frame files found

2. **Load label metadata**: Reads the `<run_id>_train.jsonl` manifest to build a label lookup map
   - Fallback: infers label from filename prefix (e.g., `happy_` -> `"happy"`)

3. **Bucket by emotion**: Groups frames into `{happy: [...], sad: [...], neutral: [...]}`
   - Frames with unrecognizable labels go into an `unknown` bucket, treated as `"neutral"`

4. **Stratified split per emotion**:
   ```
   For each emotion bucket:
       shuffle(bucket)  # using seeded RNG
       split_idx = max(1, min(len-1, int(len * train_ratio)))
       train_frames += bucket[:split_idx]
       valid_frames += bucket[split_idx:]
   ```
   - Guarantees at least 1 frame in each split per emotion (when only 1 exists, it goes to train)
   - The shuffle ensures random selection, the seed ensures reproducibility

5. **Create subdirectories**:
   ```
   train/run/<run_id>/train_ds_<run_id>/
   train/run/<run_id>/valid_ds_<run_id>/
   ```
   If these directories already exist, they are deleted and recreated (clean split).

6. **Move training frames**: `shutil.move()` from flat directory into `train_ds_<run_id>/`
   - Filenames are preserved as-is (e.g., `happy_luma_20260122_f03_idx00087.jpg`)

7. **Move validation frames**: `shutil.move()` from flat directory into `valid_ds_<run_id>/`
   - If `strip_valid_labels=True`: the emotion prefix is stripped
     - `happy_luma_20260122_f03_idx00087.jpg` -> `luma_20260122_f03_idx00087.jpg`
   - This prevents the model from learning labels from filenames during validation
   - Collision handling: if a stripped name already exists, appends `_001`, `_002`, etc.

8. **Generate three manifests**:

   | Manifest File | Content |
   |--------------|---------|
   | `<run_id>_train_ds.jsonl` | Training frames with labels |
   | `<run_id>_valid_ds_labeled.jsonl` | Validation frames with labels (for evaluation) |
   | `<run_id>_valid_ds_unlabeled.jsonl` | Validation frames with `label: null` (prevents leakage) |

### F4. Example Split (30 videos x 10 frames = 300 frames)

```
Before split:
  train/run/run_0001/
    ├── happy_video1_f00_idx00042.jpg
    ├── happy_video1_f01_idx00087.jpg
    ├── ... (100 happy frames total)
    ├── sad_video2_f00_idx00015.jpg
    ├── ... (100 sad frames total)
    ├── neutral_video3_f00_idx00033.jpg
    └── ... (100 neutral frames total)

After split (train_ratio=0.9):
  train/run/run_0001/
    ├── train_ds_run_0001/        (270 frames: 90 happy + 90 sad + 90 neutral)
    │   ├── happy_video1_f00_idx00042.jpg
    │   ├── sad_video2_f00_idx00015.jpg
    │   └── neutral_video3_f00_idx00033.jpg
    │
    └── valid_ds_run_0001/        (30 frames: 10 happy + 10 sad + 10 neutral)
        ├── video1_f08_idx00180.jpg        (label prefix stripped)
        ├── video2_f07_idx00145.jpg
        └── video3_f09_idx00198.jpg
```

### F5. Return Value

```python
{
    "run_id": "run_0001",
    "train_ratio": 0.9,
    "seed": 1234567890,
    "strip_valid_labels": True,
    "train_count": 270,
    "valid_count": 30,
    "train_ds_dir": "/mnt/videos/train/run/run_0001/train_ds_run_0001",
    "valid_ds_dir": "/mnt/videos/train/run/run_0001/valid_ds_run_0001",
    "train_manifest": "/mnt/videos/manifests/run_0001_train_ds.jsonl",
    "valid_labeled_manifest": "/mnt/videos/manifests/run_0001_valid_ds_labeled.jsonl",
    "valid_unlabeled_manifest": "/mnt/videos/manifests/run_0001_valid_ds_unlabeled.jsonl"
}
```

### F6. Database Persistence (Optional)

When `persist_valid_metadata=True` (or `split_run=True`), the API handler calls `_persist_run_frame_metadata()`:

1. Reads canonical and split manifests
2. Parses frame order/index from filenames via regex
3. Looks up `source_video_id` from the `video` table
4. Inserts rows into the `extracted_frame` table:
   - `run_id`, `split` (train/valid), `frame_path`, `label`
   - `source_video_id`, `source_video_path`
   - `frame_order`, `frame_index`
   - `extra_data` (face detection metadata, if any)

---

## 9. Phase G: Dataset Hash & MLflow Logging

### G1. Hash Calculation

The `calculate_dataset_hash(run_id)` method (described in E10) produces a SHA256 hex string that uniquely identifies the dataset structure for a given run.

### G2. MLflow Integration

The dataset hash is:
- Returned in the API response (`dataset_hash` field)
- Logged to MLflow as a parameter during training
- Stored in the `training_run.dataset_hash` column
- Used to detect dataset drift between runs (if the hash changes, the dataset has been modified)

---

## 10. Phase H: PyTorch DataLoader Integration

### H1. Data Root Resolution

**File**: `trainer/data_roots.py`

The `resolve_training_data_roots(data_root, run_id)` function determines where to load data from:

| Priority | Train Root | Condition |
|----------|-----------|-----------|
| 1 (highest) | `train/run/<run_id>/train_ds_<run_id>/` | Split dataset exists |
| 2 | `train/run/<run_id>/` | Unsplit consolidated run |
| 3 (lowest) | `train/` | No run_id or run not found |

| Priority | Validation Root | Condition |
|----------|----------------|-----------|
| 1 (highest) | `train/run/<run_id>/valid_ds_<run_id>/` | Split dataset exists |
| 2 | `test/<run_id>/` | Legacy run-scoped test |
| 3 (lowest) | `test/` | Default fallback |

Returns a `ResolvedDataRoots` namedtuple with flags indicating whether run-scoped data was found.

### H2. EmotionDataset Class

**File**: `trainer/fer_finetune/dataset.py`

Supports two data layouts:

**Layout 1: Class-Subdirectory** (used by `train/` directly)
```
train/
├── happy/
├── sad/
└── neutral/
```

**Layout 2: Flat Label-Prefix** (used by run datasets)
```
train_ds_run_0001/
├── happy_video1_f00_idx00042.jpg
├── sad_video2_f00_idx00015.jpg
└── neutral_video3_f00_idx00033.jpg
```

The dataset class auto-detects which layout is present.

**Manifest Support**: If `manifest_path` is provided, loads samples directly from the JSONL manifest instead of scanning the filesystem.

**Frame Sampling Strategies** (for video files):
- `"middle"`: Extract the middle frame
- `"random"`: Extract a random frame (used during training)
- `"first"`: Extract the first frame

**Class Mapping** (3-class default):
```python
{"happy": 0, "sad": 1, "neutral": 2}
```

### H3. DataLoader Creation

**Function**: `create_dataloaders(data_dir, run_id, batch_size, ...)`

1. Calls `resolve_training_data_roots(data_dir, run_id)` to find train/val directories
2. Creates `EmotionDataset` for training (with `frame_sampling="random"`)
3. Creates `EmotionDataset` for validation (with `frame_sampling="middle"`)
4. **Fallback**: If no dedicated validation directory exists:
   - Loads the full training dataset
   - Performs a 90/10 random split internally
   - Ensures validation always exists even without explicit splitting
5. Returns `(train_loader, val_loader)` tuple

---

## 11. Phase I: Training Launch

### I1. API Endpoint

**Endpoint**: `POST /api/v1/training/launch`
**Handler**: `apps/api/app/routers/training_control.py`

**Request**:
```json
{
    "run_id": "run_0001",
    "mode": "train",
    "variant": "variant_1",
    "checkpoint": null,
    "config_overrides": {}
}
```

### I2. Execution

1. The handler spawns `trainer/run_efficientnet_pipeline.py` as a **background subprocess**
2. The subprocess is fully detached from the API process
3. Logs are written to `logs/{variant}_{run_id}_{mode}.log`
4. Returns immediately with `status: "accepted"` and the `pid`

### I3. Pipeline Stages (`run_efficientnet_pipeline.py`)

1. **Training**: Loads `EfficientNetTrainer`, trains on frames from the resolved data root
2. **Evaluation**: Collects predictions on validation set, saves `predictions.npz`
3. **Gate A Validation**: Checks F1, ECE, Brier, balanced accuracy against thresholds
4. **Artifact Organization**:
   ```
   stats/results/<variant>/<run_type>/<run_id>/
   ├── predictions.npz
   ├── gate_a.json
   └── export/
       └── model.onnx
   ```

### I4. Streamlit Training UI

**File**: `apps/web/pages/03_Train.py`

UI controls for the complete frame extraction + training workflow:

| Control | Description |
|---------|-------------|
| Run ID input | Text field (auto-generated if empty) |
| "Generate New Run ID" button | Creates a new `run_XXXX` identifier |
| Face crop toggle | Enable/disable face detection |
| Face confidence slider | 0.3 - 0.95 |
| Split run toggle | Create train_ds/valid_ds subdirectories |
| Split train ratio slider | 0.5 - 0.95 |
| Strip valid labels toggle | Remove emotion prefix from validation filenames |
| Persist valid metadata toggle | Write frame metadata to DB |
| Dry run toggle | Preview vs. execute |
| "Prepare 10-Frame Run" button | Triggers frame extraction via API |
| "Manual Validate Plan" button | Forces dry_run=True |
| "Manual Execute Live" button | Forces dry_run=False |

---

## Appendix A: API Endpoint Reference

### Promotion & Media Endpoints

| Method | Path | Status | Handler | Description |
|--------|------|--------|---------|-------------|
| POST | `/api/v1/media/promote` | Active | `media.py::promote()` | Promote temp -> train/test |
| GET | `/api/v1/media/list` | Active | `media_v1.py::list_videos()` | List videos by split |
| GET | `/api/v1/media/{video_id}` | Active | `media_v1.py::get_video_metadata()` | Get video metadata |
| GET | `/api/v1/media/{video_id}/thumb` | Active | `media_v1.py::get_video_thumbnail()` | Get thumbnail URL |
| POST | `/api/v1/promote/stage` | **410 GONE** | `promote.py::stage_videos()` | Deprecated |
| POST | `/api/v1/promote/sample` | **410 GONE** | `promote.py::sample_split()` | Deprecated |
| POST | `/api/v1/promote/reset-manifest` | Active | `promote.py::reset_manifest()` | Reset manifest state |

### Ingest Endpoints

| Method | Path | Status | Handler | Description |
|--------|------|--------|---------|-------------|
| POST | `/api/v1/ingest/upload` | Active | `ingest.py` | Upload video to temp/ |
| POST | `/api/v1/ingest/prepare-run-frames` | Active | `ingest.py` | Extract frames + split |

### Training Endpoints

| Method | Path | Status | Handler | Description |
|--------|------|--------|---------|-------------|
| POST | `/api/v1/training/launch` | Active | `training_control.py` | Launch training subprocess |

---

## Appendix B: Database Tables

### video

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `video_id` | STRING(36) PK | UUID default | Unique identifier |
| `file_path` | STRING(1024) | NOT NULL | Relative to videos_root |
| `split` | ENUM | `temp`, `train`, `test`, `purged` | Current split |
| `label` | ENUM | `happy`, `sad`, `neutral`, NULL | Emotion class |
| `sha256` | STRING(64) | NOT NULL | File content hash |
| `size_bytes` | BIGINT | NOT NULL | File size |
| `duration_sec` | FLOAT | nullable | Video duration |
| `fps` | FLOAT | nullable | Frames per second |
| `width` | INT | nullable | Video width |
| `height` | INT | nullable | Video height |
| `deleted_at` | TIMESTAMPTZ | nullable | Soft delete |
| `created_at` | TIMESTAMPTZ | auto | Creation time |
| `updated_at` | TIMESTAMPTZ | auto | Last update |

**Constraints**:
- `UNIQUE(sha256, size_bytes)` -- content deduplication
- `CHECK`: train split requires non-null label; temp/test/purged require null label
- Indexes on `split` and `label`

### promotion_log

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `promotion_id` | INT PK | autoincrement | Unique identifier |
| `video_id` | STRING(36) FK | -> video | Referenced video |
| `from_split` | ENUM | NOT NULL | Source split |
| `to_split` | ENUM | NOT NULL | Destination split |
| `intended_label` | ENUM | nullable | Label assigned |
| `actor` | STRING(120) | nullable | Who/what triggered |
| `success` | BOOL | NOT NULL | Whether it succeeded |
| `idempotency_key` | STRING(64) | UNIQUE, nullable | For replay prevention |
| `correlation_id` | STRING(36) | nullable | Distributed tracing |
| `dry_run` | BOOL | NOT NULL | Was this a dry run |
| `error_message` | TEXT | nullable | Error details if failed |

### extracted_frame

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `frame_id` | INT PK | autoincrement | Unique identifier |
| `run_id` | STRING(32) | NOT NULL | Which run extracted this frame |
| `split` | STRING(16) | `train`, `valid`, `test` | Frame's dataset split |
| `frame_path` | STRING(1024) | NOT NULL | Absolute path to frame file |
| `label` | ENUM | nullable | Emotion label |
| `source_video_id` | STRING(36) FK | -> video (SET NULL) | Source video |
| `source_video_path` | STRING(1024) | nullable | Source video path |
| `frame_order` | INT | nullable | Order index (f00-f09) |
| `frame_index` | INT | nullable | Absolute frame position |
| `metadata` | JSON | nullable | Face detection data, etc. |

**Constraints**:
- `UNIQUE(run_id, frame_path)` -- no duplicate frames per run
- `CHECK`: test split requires null label

### label_event

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `event_id` | INT PK | autoincrement | Unique identifier |
| `video_id` | STRING(36) FK | -> video (SET NULL) | Labeled video |
| `label` | ENUM | NOT NULL | Assigned emotion |
| `action` | STRING(50) | NOT NULL | Action taken |
| `rater_id` | STRING(255) | nullable | Who labeled |
| `idempotency_key` | STRING(64) | UNIQUE, nullable | Replay prevention |
| `correlation_id` | STRING(36) | nullable | Distributed tracing |

### training_run

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `run_id` | STRING(36) PK | UUID default | Run identifier |
| `strategy` | STRING(64) | NOT NULL | Sampling strategy |
| `train_fraction` | FLOAT | (0, 1) | Train split ratio |
| `test_fraction` | FLOAT | sum <= 1.0 | Test split ratio |
| `seed` | BIGINT | nullable | Random seed |
| `status` | STRING(32) | NOT NULL | `pending`, `sampling`, `training`, `evaluating`, `completed`, `failed`, `cancelled` |
| `dataset_hash` | STRING(64) | nullable | Dataset structure hash |
| `mlflow_run_id` | STRING(255) | nullable | MLflow experiment link |

---

## Appendix C: Key Scripts & Files Index

### Promotion System

| File | Purpose |
|------|---------|
| `apps/api/routers/media.py` | Canonical promotion endpoint (POST /api/v1/media/promote) |
| `apps/api/app/fs/media_mover.py` | FileMover class -- atomic file operations |
| `apps/api/app/routers/promote.py` | Legacy deprecated endpoints (410 GONE) |
| `apps/api/app/services/promote_service.py` | Legacy promote service (deprecated, retained for manifest reset) |
| `apps/api/app/schemas/promote.py` | Pydantic schemas for promotion requests/responses |
| `apps/api/app/manifest.py` | ManifestBackend protocol + LoggingManifestBackend |

### Dataset Preparation

| File | Purpose |
|------|---------|
| `trainer/prepare_dataset.py` | DatasetPreparer class -- frame extraction, splitting, hashing |
| `trainer/data_roots.py` | ResolvedDataRoots -- run-scoped data directory resolution |
| `trainer/fer_finetune/dataset.py` | EmotionDataset (PyTorch) -- data loading for training |
| `trainer/fer_finetune/config.py` | DataConfig, ModelConfig, TrainingConfig dataclasses |
| `apps/api/app/routers/ingest.py` | prepare-run-frames API endpoint (lines 1134-1286) |

### Web Application

| File | Purpose |
|------|---------|
| `apps/web/landing_page.py` | Luma AI video generation + upload |
| `apps/web/pages/02_Label.py` | Labeling / annotation UI |
| `apps/web/pages/03_Train.py` | Training launch + frame extraction UI |
| `apps/web/pages/05_Video_Management.py` | Batch promotion + video browsing UI |
| `apps/web/api_client.py` | API client functions (promote, upload, reject, etc.) |

### Training Pipeline

| File | Purpose |
|------|---------|
| `trainer/run_efficientnet_pipeline.py` | End-to-end training orchestrator |
| `apps/api/app/routers/training_control.py` | Training launch API endpoint |

### Utilities

| File | Purpose |
|------|---------|
| `scripts/reconcile_videos.py` | Rename manual videos + register in DB + cleanup orphans |
| `apps/api/app/config.py` | AppConfig -- all paths, service URLs, DB connection |
| `apps/api/app/db/models.py` | SQLAlchemy ORM models (Video, PromotionLog, ExtractedFrame, etc.) |

### n8n Agent Workflows

| File | Purpose |
|------|---------|
| `n8n/workflows/ml-agentic-ai_v.3/01_ingest_agent.json` | Video ingest automation |
| `n8n/workflows/ml-agentic-ai_v.3/02_labeling_agent.json` | Labeling automation |
| `n8n/workflows/ml-agentic-ai_v.3/03_promotion_agent.json` | Promotion automation |

### Face Detection Model Files

| File | Purpose |
|------|---------|
| `trainer/models/face_detector/deploy.prototxt` | SSD network definition |
| `trainer/models/face_detector/res10_300x300_ssd_iter_140000.caffemodel` | Pre-trained weights |

---

*End of document. This pipeline should be verified against the live filesystem and database before initiating the first training run.*
