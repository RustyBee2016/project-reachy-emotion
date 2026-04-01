# Video Ingestion Guide

Complete guide for adding videos to the Reachy Emotion Recognition system.

## Three Ingestion Methods

### 1. Manual Videos (Local Filesystem)

**Use case:** You have videos on your local machine that you want to add to the training dataset.

**Process:**

```bash
# Step 1: Copy videos to the staging directory (by emotion type)
cp /path/to/your/happy_videos/*.mp4 /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/happy_rename/

cp /path/to/your/sad_videos/*.mp4 /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/sad_rename/

cp /path/to/your/neutral_videos/*.mp4 /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/neutral_rename/

# Step 2: Run the ingest script to rename and move videos
./scripts/ingest_manual_videos.sh

# Step 3: Videos are now in the training source directory
# Locations:
# - Happy:   /media/rusty_admin/project_data/reachy_emotion/videos/train/happy/
# - Sad:     /media/rusty_admin/project_data/reachy_emotion/videos/train/sad/
# - Neutral: /media/rusty_admin/project_data/reachy_emotion/videos/train/neutral/

# Step 4: Register videos in database (one-time after manual copy)
python scripts/reconcile_videos.py --dry-run   # preview
python scripts/reconcile_videos.py              # apply
```

**Staging directories:**
- `train/rename_prefix/happy_rename/` -- temporary holding area for happy videos
- `train/rename_prefix/sad_rename/` -- temporary holding area for sad videos
- `train/rename_prefix/neutral_rename/` -- temporary holding area for neutral videos

**Final directories (after ingest script):**
- `train/happy/` -- finalized happy videos ready for frame extraction
- `train/sad/` -- finalized sad videos ready for frame extraction
- `train/neutral/` -- finalized neutral videos ready for frame extraction

**Naming convention (before):** Original filenames or any naming scheme
**Naming convention (after ingest):** `<emotion>_luma_<timestamp>.mp4` (standardized format)
- Example: `happy_luma_20260401_093015.mp4`, `sad_luma_20260331_145200.mp4`

**Supported formats:** `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`

**Database registration:**
- Videos are automatically registered during the `reconcile_videos.py` script execution
- Script extracts metadata: SHA256, duration, fps, width, height, size
- Only videos found in `train/<emotion>/` directories are registered with `split='train'` and the appropriate emotion label

---

### 2. Web App-Generated Videos (Luma API)

**Use case:** Generate synthetic videos through the web UI using Luma Dream Machine API.

**Process:**
```bash
# Step 1: Access web UI
# Navigate to: https://10.0.4.140/

# Step 2: Go to "Generate Videos" page
# - Enter prompt (e.g., "A person smiling happily")
# - Select emotion label (happy/sad/neutral)
# - Click "Generate"

# Step 3: Web app automatically:
# - Calls Luma API
# - Downloads generated video
# - Stores in /videos/temp/
# - Creates database record
# - Generates thumbnail

# Step 4: Review and promote
# - Go to "Label & Curate" page
# - Review generated video
# - Confirm emotion label
# - Click "Promote to Training"
```

**API Endpoint:** `POST /api/v1/ingest/pull`

**Naming convention:** `luma_<emotion>_<timestamp>_<generation_id>.mp4`

**Automatic processing:**
- SHA256 checksum computed
- Metadata extracted (duration, fps, resolution)
- Thumbnail generated
- Database record created
- Stored in `temp/` until promoted

---

### 3. AffectNet Images (Test Dataset)

**⚠️ IMPORTANT:** AffectNet images are **NOT** stored in `train/happy/`, `train/sad/`, or `train/neutral/`. Those directories are **exclusively for labeled VIDEOS**, from which 10 frames will be extracted for training.

**Use case:** Add AffectNet images to test dataset for evaluation (separate from video training source).

**Storage location:** Videos are the **only** source for the training frame extraction pipeline.
- AffectNet images (if used) are stored in the `test/` directory or a separate external location
- They are **not** extracted as frames from videos in the same way manual/web-app videos are

**Process:**
```bash
# Add 500 AffectNet images per class to test set
./scripts/add_affectnet_to_test.sh run_0004 500

# This creates:
# - Test dataset: /videos/test/run_0004/
# - Ground truth: /manifests/run_0004_test_labels.jsonl
```

**Naming convention:** `test_<run_id>_<label_initial>_<index>.jpg`
- Example: `test_run_0004_h_0042.jpg` (happy, index 42)

**Ground truth format (JSONL):**
```json
{
  "file_path": "test/run_0004/test_run_0004_h_0042.jpg",
  "label": "happy",
  "source": "affectnet",
  "added_at": "2026-04-01T09:30:00"
}
```

**Key distinction:**
- **Training source videos** (`train/happy/`, `train/sad/`, `train/neutral/`) → frames are extracted → frame dataset
- **Test images** (`test/run_XXXX/`) → used directly for evaluation (no frame extraction)

---

## Complete Workflow Examples

### Example 1: Manual Videos → Training

```bash
# 1. Copy videos to staging directories (by emotion type)
cp ~/Downloads/happy*.mp4 /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/happy_rename/
cp ~/Downloads/sad*.mp4 /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/sad_rename/
cp ~/Downloads/neutral*.mp4 /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/neutral_rename/

# 2. Ingest and rename all videos at once
./scripts/ingest_manual_videos.sh

# 3. Register videos in database
python scripts/reconcile_videos.py --dry-run   # preview changes
python scripts/reconcile_videos.py              # apply changes

# 4. Create training run with new videos and extract frames
# (Videos are now ready in train/happy/, train/sad/, train/neutral/)
./scripts/create_and_archive_run.sh run_0004 3690
```

**Expected result:**
- Happy videos: `train/happy/happy_luma_*.mp4` (renamed and standardized)
- Sad videos: `train/sad/sad_luma_*.mp4`
- Neutral videos: `train/neutral/neutral_luma_*.mp4`
- All registered in PostgreSQL with `split='train'` and appropriate emotion label
- Ready for frame extraction in Phase E

---

### Example 2: Web App Generation → Training

```bash
# 1. Generate videos via web UI
# - Navigate to https://10.0.4.140/
# - Generate 10 happy videos
# - Generate 10 sad videos
# - Generate 10 neutral videos

# 2. Videos are automatically in /videos/temp/

# 3. Review and promote via web UI
# - Go to "Label & Curate" page
# - Review each video
# - Promote to training dataset

# 4. Create training run
./scripts/create_and_archive_run.sh run_0004 3690
```

---

### Example 3: Mixed Sources → Training + Test

```bash
# 1. Add manual videos to staging directories
cp /path/to/happy/*.mp4 /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/happy_rename/
cp /path/to/sad/*.mp4 /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/sad_rename/
cp /path/to/neutral/*.mp4 /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/neutral_rename/

# 2. Ingest and register manual videos
./scripts/ingest_manual_videos.sh
python scripts/reconcile_videos.py

# 3. Generate additional videos via web UI (10 videos)
# - Navigate to https://10.0.4.140/
# - Generate and promote videos to training dataset

# 4. Create training dataset (includes manual + web app videos)
# Videos from train/happy/, train/sad/, train/neutral/ are extracted → run_0004
./scripts/create_and_archive_run.sh run_0004 3690

# 5. Add AffectNet test set (separate from video training source)
./scripts/add_affectnet_to_test.sh run_0004 500

# 6. Training will use:
#    - Train: 9,300 samples extracted from videos (manual + web app)
#    - Valid: 1,050 samples extracted from videos
#    - Test: 1,500 samples from AffectNet test set (500 per class)
```

**Key workflow:**
1. Manual videos → staging → rename + register
2. Web app videos → temp → promote to train
3. All videos in `train/<emotion>/` → extract frames → run dataset
4. Test images (AffectNet) stored separately in `test/<run_id>/`

---

## Dataset Organization

```
/media/rusty_admin/project_data/reachy_emotion/videos/
├── temp/                          # Unreviewed videos (web app only)
│   └── luma_happy_20260401_*.mp4  # Generated via Luma AI, awaiting label/promotion
│
├── train/
│   ├── rename_prefix/             # Staging area for manual videos (TEMPORARY)
│   │   ├── happy_rename/
│   │   │   └── my_video.mp4       # User copies videos here
│   │   ├── sad_rename/
│   │   │   └── another_video.mp4
│   │   └── neutral_rename/
│   │       └── more_videos.mp4
│   │
│   ├── happy/                     # FINAL: Labeled source videos (happy)
│   │   └── happy_luma_20260401_093015.mp4  # After ingest_manual_videos.sh
│   │
│   ├── sad/                       # FINAL: Labeled source videos (sad)
│   │   └── sad_luma_20260331_145200.mp4
│   │
│   ├── neutral/                   # FINAL: Labeled source videos (neutral)
│   │   └── neutral_luma_20260330_082030.mp4
│   │
│   └── run/                       # Per-run extracted frame datasets
│       └── run_0004/
│           ├── *.jpg              # Extracted frames (10 per source video)
│           ├── train_ds_run_0004/ # Training split frames
│           └── valid_ds_run_0004/ # Validation split frames
│
├── test/                          # Test datasets (NOT video source)
│   ├── run_0004/
│   │   └── test_run_0004_*.jpg    # Test images (e.g., from AffectNet)
│   └── affectnet_test_dataset/    # Fixed external test set (reference)
│
├── manifests/                     # JSONL manifest files
│   ├── run_0004_train.jsonl       # Canonical frame extraction manifest
│   ├── run_0004_train_ds.jsonl    # Training split manifest
│   ├── run_0004_valid_ds_labeled.jsonl      # Validation with labels
│   └── run_0004_valid_ds_unlabeled.jsonl    # Validation without labels
│
└── thumbs/                        # Video thumbnails (served by Nginx)
    └── <video_id>.jpg
```

**Key Points:**
- **`train/rename_prefix/`** is a temporary staging area where you place manually-generated videos by emotion type
- **`train/happy/`, `train/sad/`, `train/neutral/`** are the FINAL source directories containing labeled videos ready for frame extraction
- **These directories contain VIDEOS ONLY** -- no images (10 frames will be extracted from each video)
- **`train/run/<run_id>/`** contains extracted frames and splits created during frame extraction
- **`test/`** is separate and contains test images (not video source)

---

## Video Naming Conventions

### Manual Videos (Before & After Ingest)

| Stage | Pattern | Example |
|-------|---------|---------|
| **Staging** (in `rename_prefix/`) | Any name (original filename) | `my_video.mp4`, `2026-01-22T00-30-58_clip.mp4`, `happy_recording.mp4` |
| **Final** (in `train/<emotion>/`) | `<emotion>_luma_<YYYYMMDD_HHMMSS>.mp4` | `happy_luma_20260401_093015.mp4` |

The `ingest_manual_videos.sh` and `reconcile_videos.py` scripts standardize the naming.

### Web App Generated Videos

| Stage | Pattern | Example |
|--------|---------|---------|
| Staging (in `temp/`) | Generated by Luma API | `luma_20260401_120000_abcdef123.mp4` |
| Final (after promotion) | `<emotion>_luma_<timestamp>.mp4` | `sad_luma_20260331_145200.mp4` |

### Test Datasets

| Source | Pattern | Example |
|--------|---------|---------|
| AffectNet (Test) | `test_<run_id>_<label>_<index>.jpg` | `test_run_0004_h_0042.jpg` |

**Note:** AffectNet images are stored in `test/` directories, NOT in `train/happy/`, `train/sad/`, or `train/neutral/`. The training source directories contain **videos only**.

---

## Database Integration

All ingested videos are registered in PostgreSQL:

```sql
-- Check ingested videos by source
SELECT 
    CASE 
        WHEN file_path LIKE '%manual%' THEN 'Manual'
        WHEN file_path LIKE '%luma%' THEN 'Web App'
        WHEN file_path LIKE '%affectnet%' THEN 'AffectNet'
        ELSE 'Other'
    END as source,
    label,
    COUNT(*) as count
FROM video
WHERE split = 'train'
GROUP BY source, label
ORDER BY source, label;
```

---

## Troubleshooting

### Issue: "File already exists"
**Solution:** Video with same hash already ingested. This is normal for duplicates.

### Issue: "Invalid emotion label"
**Solution:** Only `happy`, `sad`, `neutral` are supported. Check spelling.

### Issue: "No videos found"
**Solution:** Check source directory path and file extensions (`.mp4`, `.avi`, etc.)

### Issue: "Web app videos not appearing"
**Solution:** Check `/videos/temp/` directory and database records:
```bash
ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/temp/
psql -h /var/run/postgresql -U reachy_dev -d reachy_emotion -c "SELECT * FROM video WHERE split='temp' LIMIT 10;"
```

---

## Next Steps

After ingesting videos:

1. **Create training run:**
   ```bash
   ./scripts/create_and_archive_run.sh run_0004 3690
   ```

2. **Monitor training:**
   ```bash
   watch -n 2 nvidia-smi
   ```

3. **Review results:**
   ```bash
   cat stats/results/base_model/training/run_0004/gate_a.json
   ```

4. **Archive datasets:**
   ```bash
   # Automatic with create_and_archive_run.sh
   # Or manual: ./scripts/archive_existing_run.sh run_0004
   ```
