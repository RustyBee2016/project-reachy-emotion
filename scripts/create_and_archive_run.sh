#!/bin/bash
# Complete Dataset Creation, Training, and Archiving Workflow
# Usage: ./scripts/create_and_archive_run.sh <run_id> <samples_per_class>
# Example: ./scripts/create_and_archive_run.sh run_0003 3690

set -e  # Exit on error

RUN_ID=$1
SAMPLES_PER_CLASS=$2
TRAIN_RATIO=0.9
TEST_SAMPLES_PER_CLASS=390  # Separate test set
SEED=42

if [ -z "$RUN_ID" ] || [ -z "$SAMPLES_PER_CLASS" ]; then
    echo "Usage: $0 <run_id> <samples_per_class>"
    echo "Example: $0 run_0003 3690"
    echo ""
    echo "Available samples per class:"
    echo "  - Neutral: 5,000"
    echo "  - Happy: 5,000"
    echo "  - Sad: 3,690 (limiting factor)"
    echo ""
    echo "Recommended sizes: 1000, 2000, 3300, 3690"
    exit 1
fi

echo "============================================"
echo "Dataset Creation & Training Pipeline"
echo "============================================"
echo "Run ID: $RUN_ID"
echo "Samples per class: $SAMPLES_PER_CLASS"
echo "Train/Valid ratio: ${TRAIN_RATIO}/${1-$TRAIN_RATIO}"
echo "Test samples: $TEST_SAMPLES_PER_CLASS per class"
echo "============================================"
echo ""

# ============================================
# STEP 1: Create Train/Valid Dataset
# ============================================
echo "STEP 1: Creating train/valid dataset..."

python << PYTHON_EOF
import sys
from pathlib import Path
sys.path.insert(0, '/home/rusty_admin/projects/reachy_08.4.2')

from trainer.prepare_dataset import DatasetPreparer
import shutil
import random

run_id = '$RUN_ID'
samples_per_class = $SAMPLES_PER_CLASS
train_ratio = $TRAIN_RATIO
seed = $SEED

preparer = DatasetPreparer('/media/rusty_admin/project_data/reachy_emotion/videos')
run_root = Path(f'/media/rusty_admin/project_data/reachy_emotion/videos/train/run/{run_id}')
run_root.mkdir(parents=True, exist_ok=True)

random.seed(seed)
total_copied = 0

for label in ['happy', 'sad', 'neutral']:
    src_dir = Path(f'/media/rusty_admin/project_data/reachy_emotion/videos/train/{label}')
    affectnet_images = sorted(src_dir.glob('affectnet_*.jpg'))
    
    selected = affectnet_images[:samples_per_class]
    
    print(f"  Copying {len(selected)} {label} images...")
    for img in selected:
        dst_name = f"{label}_{img.name}"
        shutil.copy2(img, run_root / dst_name)
        total_copied += 1

print(f"\n✓ Total files copied: {total_copied}")

# Split into train/valid
result = preparer.split_run_dataset(
    run_id=run_id,
    train_ratio=train_ratio,
    seed=seed,
    strip_valid_labels=True
)

print(f"✓ Train: {result['train_count']} samples")
print(f"✓ Valid: {result['valid_count']} samples")

PYTHON_EOF

echo ""

# ============================================
# STEP 2: Create Test Dataset
# ============================================
echo "STEP 2: Creating test dataset..."

python << PYTHON_EOF
import sys
from pathlib import Path
sys.path.insert(0, '/home/rusty_admin/projects/reachy_08.4.2')
import shutil
import random
import json
from datetime import datetime

run_id = '$RUN_ID'
test_samples = $TEST_SAMPLES_PER_CLASS
seed = $SEED + 1  # Different seed for test

test_dir = Path('/media/rusty_admin/project_data/reachy_emotion/videos/test') / run_id
test_dir.mkdir(parents=True, exist_ok=True)

manifest_path = Path('/media/rusty_admin/project_data/reachy_emotion/videos/manifests') / f'{run_id}_test_labels.jsonl'
manifest_path.parent.mkdir(parents=True, exist_ok=True)

random.seed(seed)
ground_truth = []

for label in ['happy', 'sad', 'neutral']:
    src_dir = Path(f'/media/rusty_admin/project_data/reachy_emotion/videos/train/{label}')
    affectnet_images = sorted(src_dir.glob('affectnet_*.jpg'))
    
    # Use different samples than train/valid (offset by samples_per_class)
    offset = $SAMPLES_PER_CLASS
    test_images = affectnet_images[offset:offset+test_samples]
    
    print(f"  Creating {len(test_images)} {label} test samples...")
    for idx, img in enumerate(test_images):
        # Unlabeled filename
        dst_name = f"test_{run_id}_{label[0]}_{idx:04d}.jpg"
        shutil.copy2(img, test_dir / dst_name)
        
        # Ground truth entry
        ground_truth.append({
            "file_path": f"test/{run_id}/{dst_name}",
            "label": label,
            "source": "affectnet",
            "original_path": str(img)
        })

# Save ground truth manifest
with open(manifest_path, 'w') as f:
    for entry in ground_truth:
        f.write(json.dumps(entry) + '\n')

print(f"\n✓ Test dataset: {len(ground_truth)} samples")
print(f"✓ Manifest: {manifest_path}")

PYTHON_EOF

echo ""

# ============================================
# STEP 3: Train Model
# ============================================
echo "STEP 3: Training model..."
echo "This will take 2-4 hours depending on dataset size..."
echo ""

python -m trainer.run_efficientnet_pipeline \
    --run-id $RUN_ID \
    --config trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml \
    --variant base_model \
    --run-type training

echo ""

# ============================================
# STEP 4: Archive All Datasets
# ============================================
echo "STEP 4: Archiving datasets..."

python << PYTHON_EOF
import sys
from pathlib import Path
from datetime import datetime
import shutil
import json

run_id = '$RUN_ID'
videos_root = Path('/media/rusty_admin/project_data/reachy_emotion/videos')
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

# Archive directories
train_archive = videos_root / 'train' / 'archive'
valid_archive = videos_root / 'validation' / 'archive'
test_archive = videos_root / 'test' / 'archive'

train_archive.mkdir(parents=True, exist_ok=True)
valid_archive.mkdir(parents=True, exist_ok=True)
test_archive.mkdir(parents=True, exist_ok=True)

# Source directories
run_root = videos_root / 'train' / 'run' / run_id
train_ds_dir = run_root / f'train_ds_{run_id}'
valid_ds_dir = run_root / f'valid_ds_{run_id}'
test_ds_dir = videos_root / 'test' / run_id

# Archive training dataset
if train_ds_dir.exists():
    archive_train_path = train_archive / f'{run_id}_train_{timestamp}'
    shutil.copytree(train_ds_dir, archive_train_path)
    
    manifest = {
        'run_id': run_id,
        'split': 'train',
        'archived_at': timestamp,
        'sample_count': len(list(train_ds_dir.glob('**/*.jpg'))),
        'source_path': str(train_ds_dir),
        'archive_path': str(archive_train_path)
    }
    
    with open(archive_train_path / 'manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"✓ Archived training dataset: {archive_train_path}")
    print(f"  Samples: {manifest['sample_count']}")

# Archive validation dataset
if valid_ds_dir.exists():
    archive_valid_path = valid_archive / f'{run_id}_valid_{timestamp}'
    shutil.copytree(valid_ds_dir, archive_valid_path)
    
    manifest = {
        'run_id': run_id,
        'split': 'validation',
        'archived_at': timestamp,
        'sample_count': len(list(valid_ds_dir.glob('**/*.jpg'))),
        'source_path': str(valid_ds_dir),
        'archive_path': str(archive_valid_path)
    }
    
    with open(archive_valid_path / 'manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"✓ Archived validation dataset: {archive_valid_path}")
    print(f"  Samples: {manifest['sample_count']}")

# Archive test dataset
if test_ds_dir.exists():
    archive_test_path = test_archive / f'{run_id}_test_{timestamp}'
    shutil.copytree(test_ds_dir, archive_test_path)
    
    # Copy ground truth manifest
    manifest_src = videos_root / 'manifests' / f'{run_id}_test_labels.jsonl'
    if manifest_src.exists():
        shutil.copy2(manifest_src, archive_test_path / 'ground_truth.jsonl')
    
    manifest = {
        'run_id': run_id,
        'split': 'test',
        'archived_at': timestamp,
        'sample_count': len(list(test_ds_dir.glob('**/*.jpg'))),
        'source_path': str(test_ds_dir),
        'archive_path': str(archive_test_path),
        'ground_truth_manifest': str(archive_test_path / 'ground_truth.jsonl')
    }
    
    with open(archive_test_path / 'manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"✓ Archived test dataset: {archive_test_path}")
    print(f"  Samples: {manifest['sample_count']}")

print(f"\n✓ All datasets archived")

PYTHON_EOF

echo ""

# ============================================
# STEP 5: Summary
# ============================================
echo "============================================"
echo "Pipeline Complete: $RUN_ID"
echo "============================================"
echo ""
echo "Archives created:"
echo "  Training:   /media/rusty_admin/project_data/reachy_emotion/videos/train/archive/"
echo "  Validation: /media/rusty_admin/project_data/reachy_emotion/videos/validation/archive/"
echo "  Test:       /media/rusty_admin/project_data/reachy_emotion/videos/test/archive/"
echo ""
echo "Results:"
echo "  Gate A:     stats/results/base_model/training/$RUN_ID/gate_a.json"
echo "  Dashboard:  stats/results/dashboard_runs/base_model/training/$RUN_ID.json"
echo ""
echo "✓ Complete"
