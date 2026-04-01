# AffectNet Database Query Examples

Quick reference for querying registered AffectNet images.

## Connection

```bash
# PostgreSQL command line
psql -h /var/run/postgresql -U reachy_dev -d reachy_emotion
```

```python
# Python SQLAlchemy
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from apps.api.app.db.models import Video

engine = create_engine("postgresql://reachy_dev:tweetwd4959@/reachy_emotion?host=/var/run/postgresql")
Session = sessionmaker(bind=engine)
session = Session()
```

---

## Basic Queries

### Count All Registered AffectNet Images

```sql
SELECT COUNT(*) as total
FROM video
WHERE file_path LIKE '%AffectNet%'
  AND split = 'train';
```

```python
count = session.query(Video).filter(
    Video.file_path.like('%AffectNet%'),
    Video.split == 'train'
).count()
print(f"Total AffectNet images: {count}")
```

### Count by Dataset and Emotion

```sql
SELECT 
    CASE 
        WHEN file_path LIKE '%train_set%' THEN 'train_set'
        WHEN file_path LIKE '%validation_set%' THEN 'validation_set'
    END as dataset,
    label,
    COUNT(*) as count
FROM video
WHERE file_path LIKE '%AffectNet%'
  AND split = 'train'
GROUP BY dataset, label
ORDER BY dataset, label;
```

```python
from sqlalchemy import case

dataset_col = case(
    (Video.file_path.like('%train_set%'), 'train_set'),
    (Video.file_path.like('%validation_set%'), 'validation_set'),
    else_='other'
)

results = session.query(
    dataset_col.label('dataset'),
    Video.label,
    func.count().label('count')
).filter(
    Video.file_path.like('%AffectNet%'),
    Video.split == 'train'
).group_by('dataset', Video.label).all()

for dataset, label, count in results:
    print(f"{dataset}/{label}: {count}")
```

---

## Training Dataset Queries

### Get Balanced Training Samples

```sql
-- Get 3000 random images per class from train_set
(SELECT * FROM video 
 WHERE split = 'train' 
   AND label = 'happy' 
   AND file_path LIKE '%train_set%' 
 ORDER BY RANDOM() LIMIT 3000)
UNION ALL
(SELECT * FROM video 
 WHERE split = 'train' 
   AND label = 'sad' 
   AND file_path LIKE '%train_set%' 
 ORDER BY RANDOM() LIMIT 3000)
UNION ALL
(SELECT * FROM video 
 WHERE split = 'train' 
   AND label = 'neutral' 
   AND file_path LIKE '%train_set%' 
 ORDER BY RANDOM() LIMIT 3000);
```

```python
samples_per_class = 3000
training_samples = []

for label in ['happy', 'sad', 'neutral']:
    samples = session.query(Video).filter(
        Video.split == 'train',
        Video.label == label,
        Video.file_path.like('%train_set%')
    ).order_by(func.random()).limit(samples_per_class).all()
    
    training_samples.extend(samples)

print(f"Total training samples: {len(training_samples)}")
```

### Get Training Samples with Metadata Filters

```python
# High-arousal happy images
high_arousal_happy = session.query(Video).filter(
    Video.split == 'train',
    Video.label == 'happy',
    Video.file_path.like('%train_set%'),
    Video.extra_data['arousal'].astext.cast(Float) > 0.7
).limit(1000).all()

# Young adults (age 20-30)
young_adults = session.query(Video).filter(
    Video.split == 'train',
    Video.file_path.like('%train_set%'),
    Video.extra_data['age'].astext.cast(Integer).between(20, 30)
).limit(1000).all()

# Female subjects
female_subjects = session.query(Video).filter(
    Video.split == 'train',
    Video.file_path.like('%train_set%'),
    Video.extra_data['gender'].astext == '1'
).limit(1000).all()
```

---

## Test Dataset Queries

### Sample Test Images from Validation Set

```sql
-- Get 500 random images per class from validation_set for test
SELECT file_path, label, sha256, extra_data
FROM video
WHERE split = 'train'
  AND file_path LIKE '%validation_set%'
  AND label = 'happy'
ORDER BY RANDOM()
LIMIT 500;

-- Repeat for 'sad' and 'neutral'
```

```python
test_samples = []

for label in ['happy', 'sad', 'neutral']:
    samples = session.query(Video).filter(
        Video.split == 'train',
        Video.label == label,
        Video.file_path.like('%validation_set%')
    ).order_by(func.random()).limit(500).all()
    
    test_samples.extend(samples)

print(f"Total test samples: {len(test_samples)}")

# Create ground truth manifest
import json
from pathlib import Path

manifest_path = Path('/media/rusty_admin/project_data/reachy_emotion/videos/manifests/run_0004_test_labels.jsonl')
manifest_path.parent.mkdir(parents=True, exist_ok=True)

with open(manifest_path, 'w') as f:
    for sample in test_samples:
        entry = {
            'file_path': sample.file_path,
            'label': sample.label,
            'sha256': sample.sha256,
            'source': 'affectnet_validation',
            'extra_data': sample.extra_data
        }
        f.write(json.dumps(entry) + '\n')

print(f"Ground truth manifest: {manifest_path}")
```

---

## Advanced Metadata Queries

### Emotion Distribution by Age

```sql
SELECT 
    CASE 
        WHEN (extra_data->>'age')::int < 20 THEN 'under_20'
        WHEN (extra_data->>'age')::int BETWEEN 20 AND 30 THEN '20-30'
        WHEN (extra_data->>'age')::int BETWEEN 31 AND 40 THEN '31-40'
        WHEN (extra_data->>'age')::int > 40 THEN 'over_40'
    END as age_group,
    label,
    COUNT(*) as count
FROM video
WHERE split = 'train'
  AND file_path LIKE '%AffectNet%'
  AND extra_data->>'age' IS NOT NULL
GROUP BY age_group, label
ORDER BY age_group, label;
```

### Average Valence and Arousal by Emotion

```sql
SELECT 
    label,
    ROUND(AVG((extra_data->>'valence')::float)::numeric, 3) as avg_valence,
    ROUND(AVG((extra_data->>'arousal')::float)::numeric, 3) as avg_arousal,
    COUNT(*) as count
FROM video
WHERE split = 'train'
  AND file_path LIKE '%AffectNet%'
  AND extra_data->>'valence' IS NOT NULL
  AND extra_data->>'arousal' IS NOT NULL
GROUP BY label
ORDER BY label;
```

### Soft-Label Confidence Analysis

```sql
-- Get images with high confidence in primary emotion
-- (soft-label array index 0=neutral, 1=happy, 2=sad)
SELECT 
    file_path,
    label,
    extra_data->'soft-label' as soft_label
FROM video
WHERE split = 'train'
  AND label = 'happy'
  AND file_path LIKE '%train_set%'
  AND (extra_data->'soft-label'->>1)::float > 0.8  -- High confidence happy
LIMIT 100;
```

---

## Dataset Building Workflow

### Complete Example: Create run_0004 Dataset

```python
import shutil
from pathlib import Path
from datetime import datetime

run_id = 'run_0004'
samples_per_class = 3690  # Maximum balanced
videos_root = Path('/media/rusty_admin/project_data/reachy_emotion/videos')

# 1. Create run directory
run_dir = videos_root / 'train' / 'run' / run_id
run_dir.mkdir(parents=True, exist_ok=True)

# 2. Sample and copy training images
for label in ['happy', 'sad', 'neutral']:
    samples = session.query(Video).filter(
        Video.split == 'train',
        Video.label == label,
        Video.file_path.like('%train_set%')
    ).order_by(func.random()).limit(samples_per_class).all()
    
    print(f"Copying {len(samples)} {label} images...")
    
    for idx, sample in enumerate(samples):
        src = Path(sample.file_path)
        dst = run_dir / f"{label}_{src.stem}.jpg"
        shutil.copy2(src, dst)

print(f"✓ Copied {samples_per_class * 3} images to {run_dir}")

# 3. Split into train/valid (90/10)
from trainer.prepare_dataset import DatasetPreparer

preparer = DatasetPreparer(videos_root)
result = preparer.split_run_dataset(
    run_id=run_id,
    train_ratio=0.9,
    seed=42,
    strip_valid_labels=True
)

print(f"✓ Train: {result['train_count']} samples")
print(f"✓ Valid: {result['valid_count']} samples")

# 4. Create test dataset from validation_set
test_dir = videos_root / 'test' / run_id
test_dir.mkdir(parents=True, exist_ok=True)

test_samples = []
for label in ['happy', 'sad', 'neutral']:
    samples = session.query(Video).filter(
        Video.split == 'train',
        Video.label == label,
        Video.file_path.like('%validation_set%')
    ).order_by(func.random()).limit(390).all()
    
    for idx, sample in enumerate(samples):
        src = Path(sample.file_path)
        # Unlabeled filename for test
        dst = test_dir / f"test_{run_id}_{label[0]}_{idx:04d}.jpg"
        shutil.copy2(src, dst)
        
        test_samples.append({
            'file_path': str(dst),
            'label': label,
            'sha256': sample.sha256,
            'source': 'affectnet_validation',
            'extra_data': sample.extra_data
        })

# 5. Save ground truth manifest
manifest_path = videos_root / 'manifests' / f'{run_id}_test_labels.jsonl'
manifest_path.parent.mkdir(parents=True, exist_ok=True)

with open(manifest_path, 'w') as f:
    for entry in test_samples:
        f.write(json.dumps(entry) + '\n')

print(f"✓ Test: {len(test_samples)} samples")
print(f"✓ Ground truth: {manifest_path}")
```

---

## Verification Queries

### Check for Duplicates

```sql
-- Find duplicate SHA256 hashes
SELECT sha256, COUNT(*) as count
FROM video
WHERE file_path LIKE '%AffectNet%'
GROUP BY sha256
HAVING COUNT(*) > 1
LIMIT 10;
```

### Verify Annotation Completeness

```sql
-- Check which annotation fields are populated
SELECT 
    COUNT(*) FILTER (WHERE extra_data->>'valence' IS NOT NULL) as has_valence,
    COUNT(*) FILTER (WHERE extra_data->>'arousal' IS NOT NULL) as has_arousal,
    COUNT(*) FILTER (WHERE extra_data->>'age' IS NOT NULL) as has_age,
    COUNT(*) FILTER (WHERE extra_data->>'gender' IS NOT NULL) as has_gender,
    COUNT(*) FILTER (WHERE extra_data->>'soft-label' IS NOT NULL) as has_soft_label
FROM video
WHERE file_path LIKE '%AffectNet%';
```

### Check Image Dimensions

```sql
SELECT 
    width,
    height,
    COUNT(*) as count
FROM video
WHERE file_path LIKE '%AffectNet%'
GROUP BY width, height
ORDER BY count DESC;
```

---

## Export to CSV/JSON

### Export Sample Dataset

```sql
-- Export to CSV
COPY (
    SELECT file_path, label, width, height, 
           extra_data->>'valence' as valence,
           extra_data->>'arousal' as arousal
    FROM video
    WHERE split = 'train'
      AND label = 'happy'
      AND file_path LIKE '%train_set%'
    LIMIT 1000
) TO '/tmp/affectnet_happy_sample.csv' WITH CSV HEADER;
```

```python
# Export to JSON
import json

samples = session.query(Video).filter(
    Video.split == 'train',
    Video.label == 'happy',
    Video.file_path.like('%train_set%')
).limit(1000).all()

data = []
for sample in samples:
    data.append({
        'file_path': sample.file_path,
        'label': sample.label,
        'sha256': sample.sha256,
        'width': sample.width,
        'height': sample.height,
        'extra_data': sample.extra_data
    })

with open('/tmp/affectnet_happy_sample.json', 'w') as f:
    json.dump(data, f, indent=2)
```

---

## Performance Tips

1. **Use indexes**: The database already has indexes on `split`, `label`, `sha256`, and `file_path`
2. **Batch queries**: Use `LIMIT` to avoid loading too many records at once
3. **Use `func.random()`**: For random sampling in SQLAlchemy
4. **Cache results**: Store sampled datasets to avoid re-querying
5. **Use JSONB operators**: Efficiently query `extra_data` fields

## Related Scripts

- `scripts/register_all_affectnet.py` - Registration script
- `scripts/create_and_archive_run.sh` - Automated training pipeline
- `trainer/prepare_dataset.py` - Dataset preparation utilities
