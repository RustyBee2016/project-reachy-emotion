#!/bin/bash
# Archive existing datasets for a completed run
# Usage: ./scripts/archive_existing_run.sh <run_id>
# Example: ./scripts/archive_existing_run.sh run_0002

set -e

RUN_ID=$1

if [ -z "$RUN_ID" ]; then
    echo "Usage: $0 <run_id>"
    echo "Example: $0 run_0002"
    exit 1
fi

echo "============================================"
echo "Archiving Datasets for: $RUN_ID"
echo "============================================"
echo ""

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

archived_count = 0

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
    archived_count += 1
else:
    print(f"⚠ Training dataset not found: {train_ds_dir}")

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
    archived_count += 1
else:
    print(f"⚠ Validation dataset not found: {valid_ds_dir}")

# Archive test dataset
if test_ds_dir.exists():
    archive_test_path = test_archive / f'{run_id}_test_{timestamp}'
    shutil.copytree(test_ds_dir, archive_test_path)
    
    # Copy ground truth manifest if exists
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
        'ground_truth_manifest': str(archive_test_path / 'ground_truth.jsonl') if manifest_src.exists() else None
    }
    
    with open(archive_test_path / 'manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"✓ Archived test dataset: {archive_test_path}")
    print(f"  Samples: {manifest['sample_count']}")
    archived_count += 1
else:
    print(f"⚠ Test dataset not found: {test_ds_dir}")

print(f"\n✓ Archived {archived_count} dataset(s)")

PYTHON_EOF

echo ""
echo "============================================"
echo "Archive Complete: $RUN_ID"
echo "============================================"
echo ""
echo "View archives:"
echo "  ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/train/archive/"
echo "  ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/validation/archive/"
echo "  ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/test/archive/"
