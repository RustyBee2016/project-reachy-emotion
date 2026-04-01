# AffectNet Database Registration Guide

Complete guide for registering AffectNet training and validation images with annotations in the PostgreSQL database.

## Overview

The AffectNet dataset contains ~87,000 training images and ~4,000 validation images with rich annotation metadata. This guide explains how to register these images in the database for use in training, validation, and test datasets.

## Database Schema

All AffectNet images are stored in the `video` table with the following key fields:

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | TEXT | Full path to image file |
| `sha256` | TEXT | SHA256 hash of file |
| `split` | ENUM | Always `'train'` for AffectNet images |
| `label` | TEXT | Emotion label: `happy`, `sad`, or `neutral` |
| `width` | INTEGER | Image width in pixels |
| `height` | INTEGER | Image height in pixels |
| `size_bytes` | BIGINT | File size in bytes |
| `extra_data` | JSON | Full annotation metadata |
| `duration_sec` | FLOAT | NULL for images |
| `fps` | FLOAT | NULL for images |

**Important:** All AffectNet images use `split='train'` regardless of whether they come from `train_set` or `validation_set`. The `validation_set` images are part of the training pool and can be sampled for test datasets later.

## Annotation Filtering

**Only images with the following annotation values are registered:**

| Annotation Field | Valid Values | Emotion Mapping |
|-----------------|--------------|-----------------|
| `human-label` | 0 | neutral |
| `human-label` | 1 | happy |
| `human-label` | 2 | sad |

All other images (human-label 3-7) are **ignored** and not registered in the database.

## File System Structure

```
/media/rusty_admin/project_data/reachy_emotion/affectnet/consolidated/AffectNet+/human_annotated/
├── train_set/
│   ├── images/
│   │   ├── 0.jpg
│   │   ├── 1.jpg
│   │   └── ... (~87,000 images)
│   └── annotations/
│       ├── 0.json
│       ├── 1.json
│       └── ... (~87,000 annotations)
└── validation_set/
    ├── images/
    │   ├── 0.jpg
    │   ├── 1.jpg
    │   └── ... (~4,000 images)
    └── annotations/
        ├── 0.json
        ├── 1.json
        └── ... (~4,000 annotations)
```

## Annotation Metadata

Each annotation JSON file contains:

```json
{
  "human-label": 1,
  "valence": 0.5,
  "arousal": 0.3,
  "expression": 1,
  "age": 25,
  "gender": 0,
  "ethnicity": 2,
  "pose": 0,
  "soft-label": [0.05, 0.85, 0.02, 0.01, 0.03, 0.02, 0.01, 0.01],
  "face_x": 50,
  "face_y": 60,
  "face_width": 120,
  "face_height": 140,
  "facial_landmarks": [[x1, y1], [x2, y2], ...]
}
```

All of this metadata is stored in the `extra_data` JSON field for future use.

## Registration Script Usage

### Test Mode (First 100 Images)

```bash
# Test on training set only
python scripts/register_all_affectnet.py --dataset train --test

# Test on validation set only
python scripts/register_all_affectnet.py --dataset validation --test

# Test on both
python scripts/register_all_affectnet.py --dataset both --test
```

### Full Registration

```bash
# Register training set only (~87K images, ~30-45 minutes)
python scripts/register_all_affectnet.py --dataset train

# Register validation set only (~4K images, ~2-3 minutes)
python scripts/register_all_affectnet.py --dataset validation

# Register both (recommended, ~35-50 minutes)
python scripts/register_all_affectnet.py --dataset both
```

### Overwrite Existing Records

```bash
# Clean registration - deletes existing AffectNet records first
python scripts/register_all_affectnet.py --dataset both --overwrite
```

## Expected Output

```
============================================================
AffectNet Database Registration
============================================================
Dataset: both
Test mode: False
Overwrite: True
Database: /reachy_emotion?host=/var/run/postgresql
============================================================

============================================================
TRAINING SET
============================================================
Processing 414799 images from train set...
Images dir: /media/.../train_set/images
Annotations dir: /media/.../train_set/annotations
Database split: train

Overwrite mode: Deleting existing train_set records...
Deleted 41 existing records
  Processed 100/414799 images... (created: 85, updated: 0, skipped: 15, errors: 0)
  Processed 200/414799 images... (created: 170, updated: 0, skipped: 30, errors: 0)
  ...

Training set statistics:
  total_images: 414799
  valid_annotations: 74123
  invalid_annotations: 340676
  created: 74123
  updated: 0
  skipped: 0
  errors: 0

============================================================
VALIDATION SET
============================================================
Processing 3999 images from validation set...
Images dir: /media/.../validation_set/images
Annotations dir: /media/.../validation_set/annotations
Database split: train

Overwrite mode: Deleting existing validation_set records...
Deleted 0 existing records
  Processed 100/3999 images... (created: 18, updated: 0, skipped: 0, errors: 0)
  ...

Validation set statistics:
  total_images: 3999
  valid_annotations: 500
  invalid_annotations: 3499
  created: 500
  updated: 0
  skipped: 0
  errors: 0

============================================================
TOTAL STATISTICS
============================================================
  total_images: 418798
  valid_annotations: 74623
  invalid_annotations: 344175
  created: 74623
  updated: 0
  skipped: 0
  errors: 0

============================================================
DATABASE VERIFICATION
============================================================
  train_set/happy: 24841 records
  train_set/sad: 24641 records
  train_set/neutral: 24641 records
  validation_set/happy: 167 records
  validation_set/sad: 166 records
  validation_set/neutral: 167 records

✓ Registration complete!
```

**Note:** The exact numbers will vary based on the actual distribution of human-label values in the dataset.

## Querying Registered Images

### Count by Emotion and Dataset

```sql
-- Training set images by emotion
SELECT 
    label,
    COUNT(*) as count
FROM video
WHERE split = 'train'
  AND file_path LIKE '%train_set%'
GROUP BY label
ORDER BY label;

-- Validation set images by emotion
SELECT 
    label,
    COUNT(*) as count
FROM video
WHERE split = 'train'
  AND file_path LIKE '%validation_set%'
GROUP BY label
ORDER BY label;
```

### Sample Images for Training

```sql
-- Get 1000 random happy images from training set
SELECT file_path, extra_data
FROM video
WHERE split = 'train'
  AND label = 'happy'
  AND file_path LIKE '%train_set%'
ORDER BY RANDOM()
LIMIT 1000;
```

### Sample Images for Test Dataset

```sql
-- Get 500 random images per class from validation set for test
-- (These will be used to create unlabeled test datasets)
SELECT file_path, label, extra_data
FROM video
WHERE split = 'train'
  AND file_path LIKE '%validation_set%'
  AND label IN ('happy', 'sad', 'neutral')
ORDER BY label, RANDOM()
LIMIT 1500;  -- 500 per class
```

### Query by Annotation Metadata

```sql
-- Find high-arousal happy images
SELECT file_path, extra_data->>'arousal' as arousal
FROM video
WHERE split = 'train'
  AND label = 'happy'
  AND (extra_data->>'arousal')::float > 0.7
LIMIT 100;

-- Find images by age range
SELECT file_path, extra_data->>'age' as age
FROM video
WHERE split = 'train'
  AND (extra_data->>'age')::int BETWEEN 20 AND 30
LIMIT 100;

-- Find images by gender (0=male, 1=female)
SELECT file_path, extra_data->>'gender' as gender, label
FROM video
WHERE split = 'train'
  AND extra_data->>'gender' = '0'
LIMIT 100;
```

## Integration with Training Pipeline

### Creating Training Datasets

Once registered, you can create training datasets by querying the database:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from apps.api.app.db.models import Video

# Connect to database
engine = create_engine("postgresql://reachy_dev:tweetwd4959@/reachy_emotion?host=/var/run/postgresql")
Session = sessionmaker(bind=engine)
session = Session()

# Get balanced training samples (3000 per class from train_set)
samples = []
for label in ['happy', 'sad', 'neutral']:
    records = session.query(Video).filter(
        Video.split == 'train',
        Video.label == label,
        Video.file_path.like('%train_set%')
    ).order_by(func.random()).limit(3000).all()
    
    samples.extend(records)

print(f"Total training samples: {len(samples)}")
```

### Creating Test Datasets

```python
# Get test samples from validation_set (500 per class)
test_samples = []
for label in ['happy', 'sad', 'neutral']:
    records = session.query(Video).filter(
        Video.split == 'train',
        Video.label == label,
        Video.file_path.like('%validation_set%')
    ).order_by(func.random()).limit(500).all()
    
    test_samples.extend(records)

# Create unlabeled test dataset
# (Copy images to test directory with unlabeled filenames)
# (Store ground truth separately in manifest)
```

## Troubleshooting

### Issue: "duplicate key value violates unique constraint"

**Cause:** Image already registered with same SHA256 hash and file size.

**Solution:** Use `--overwrite` flag to delete and re-register, or skip duplicates (default behavior).

### Issue: "'validation' is not among the defined enum values"

**Cause:** Trying to use `split='validation'` which doesn't exist in the database.

**Solution:** Script automatically uses `split='train'` for all AffectNet images. This is correct behavior.

### Issue: "new row violates check constraint chk_video_split_label_policy"

**Cause:** Trying to update a record with `split='test'` to have a label.

**Solution:** Script automatically skips records with `split='test'` to avoid this constraint violation.

### Issue: Registration is slow

**Expected:** Processing ~87K images takes 30-50 minutes due to:
- SHA256 hash computation for each image
- Image dimension reading
- Database insertion in batches of 100

**Optimization:** The script already uses batch inserts. Further optimization would require parallel processing.

## Verification

After registration, verify the database state:

```bash
# Connect to database
psql -h /var/run/postgresql -U reachy_dev -d reachy_emotion

# Check total counts
SELECT 
    CASE 
        WHEN file_path LIKE '%train_set%' THEN 'train_set'
        WHEN file_path LIKE '%validation_set%' THEN 'validation_set'
        ELSE 'other'
    END as dataset,
    label,
    COUNT(*) as count
FROM video
WHERE split = 'train'
  AND file_path LIKE '%AffectNet%'
GROUP BY dataset, label
ORDER BY dataset, label;

# Check annotation metadata
SELECT 
    label,
    AVG((extra_data->>'valence')::float) as avg_valence,
    AVG((extra_data->>'arousal')::float) as avg_arousal
FROM video
WHERE split = 'train'
  AND file_path LIKE '%AffectNet%'
  AND extra_data->>'valence' IS NOT NULL
GROUP BY label;
```

## Next Steps

After successful registration:

1. **Create training datasets** using database queries
2. **Sample test datasets** from validation_set images
3. **Use annotation metadata** for advanced filtering (age, gender, pose, etc.)
4. **Run training pipeline** with registered images
5. **Track dataset provenance** using `extra_data` metadata

## Related Documentation

- `VIDEO_INGESTION_GUIDE.md` - Complete video ingestion workflows
- `scripts/create_and_archive_run.sh` - Automated training pipeline
- `AGENTS.md` - Agent 2 (Labeling) and Agent 3 (Promotion) details
