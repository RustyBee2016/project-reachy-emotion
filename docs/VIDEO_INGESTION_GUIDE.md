# Video Ingestion Guide

Complete guide for adding videos to the Reachy Emotion Recognition system.

## Three Ingestion Methods

### 1. Manual Videos (Local Filesystem)

**Use case:** You have videos on your local machine that you want to add to the training dataset.

**Process:**
```bash
# Step 1: Copy videos to a temporary directory
mkdir -p /tmp/my_videos
cp /path/to/your/videos/*.mp4 /tmp/my_videos/

# Step 2: Ingest with emotion label
./scripts/ingest_manual_videos.sh /tmp/my_videos happy

# Step 3: Videos are now in training dataset
# Location: /media/rusty_admin/project_data/reachy_emotion/videos/train/happy/
```

**Naming convention:** `manual_<emotion>_<timestamp>_<hash>.mp4`

**Supported formats:** `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`

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

**Use case:** Add AffectNet images to test dataset for evaluation.

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
  "original_path": "/media/.../train/happy/affectnet_12345.jpg",
  "added_at": "2026-03-30T21:45:00"
}
```

---

## Complete Workflow Examples

### Example 1: Manual Videos → Training

```bash
# 1. Prepare videos
mkdir -p /tmp/happy_videos /tmp/sad_videos /tmp/neutral_videos
cp ~/Downloads/happy*.mp4 /tmp/happy_videos/
cp ~/Downloads/sad*.mp4 /tmp/sad_videos/
cp ~/Downloads/neutral*.mp4 /tmp/neutral_videos/

# 2. Ingest all three emotions
./scripts/ingest_manual_videos.sh /tmp/happy_videos happy
./scripts/ingest_manual_videos.sh /tmp/sad_videos sad
./scripts/ingest_manual_videos.sh /tmp/neutral_videos neutral

# 3. Create training run with new videos
./scripts/create_and_archive_run.sh run_0004 3690
```

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
# 1. Add manual videos
./scripts/ingest_manual_videos.sh /tmp/my_videos happy

# 2. Generate videos via web UI (10 videos)

# 3. Create training dataset (includes manual + web app videos)
./scripts/create_and_archive_run.sh run_0004 3690

# 4. Add AffectNet test set
./scripts/add_affectnet_to_test.sh run_0004 500

# 5. Training will use:
#    - Train: 9,963 samples (manual + web app + AffectNet)
#    - Valid: 1,107 samples
#    - Test: 1,500 samples (500 per class from AffectNet)
```

---

## Dataset Organization

```
/media/rusty_admin/project_data/reachy_emotion/videos/
├── temp/                          # Unreviewed videos (web app)
│   └── luma_happy_20260330_*.mp4
│
├── train/                         # Training dataset
│   ├── happy/
│   │   ├── manual_happy_*.mp4     # Manual videos
│   │   ├── luma_happy_*.mp4       # Web app videos
│   │   └── affectnet_*.jpg        # AffectNet images
│   ├── sad/
│   └── neutral/
│
├── train/run/                     # Per-run datasets
│   └── run_0004/
│       ├── train_ds_run_0004/     # Training split
│       └── valid_ds_run_0004/     # Validation split
│
├── test/                          # Test datasets
│   └── run_0004/
│       └── test_run_0004_*.jpg    # Unlabeled test images
│
├── train/archive/                 # Archived training datasets
├── validation/archive/            # Archived validation datasets
└── test/archive/                  # Archived test datasets
```

---

## Video Naming Conventions

| Source | Pattern | Example |
|--------|---------|---------|
| Manual | `manual_<emotion>_<timestamp>_<hash>.mp4` | `manual_happy_20260330_214500_a1b2c3d4.mp4` |
| Web App (Luma) | `luma_<emotion>_<timestamp>_<gen_id>.mp4` | `luma_sad_20260330_214500_abc123.mp4` |
| AffectNet (Train) | `affectnet_<id>.jpg` | `affectnet_12345.jpg` |
| AffectNet (Test) | `test_<run_id>_<label>_<index>.jpg` | `test_run_0004_h_0042.jpg` |

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
