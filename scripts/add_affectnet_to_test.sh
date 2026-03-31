#!/bin/bash
# Add AffectNet images to test dataset for a specific run
# Usage: ./scripts/add_affectnet_to_test.sh <run_id> <samples_per_class>
# Example: ./scripts/add_affectnet_to_test.sh run_0004 500

set -e

RUN_ID=$1
SAMPLES_PER_CLASS=${2:-390}
VIDEOS_ROOT="/media/rusty_admin/project_data/reachy_emotion/videos"

if [ -z "$RUN_ID" ]; then
    echo "Usage: $0 <run_id> [samples_per_class]"
    echo "Example: $0 run_0004 500"
    echo ""
    echo "Default samples per class: 390"
    exit 1
fi

echo "============================================"
echo "Add AffectNet Images to Test Dataset"
echo "============================================"
echo "Run ID: $RUN_ID"
echo "Samples per class: $SAMPLES_PER_CLASS"
echo "============================================"
echo ""

python << PYTHON_EOF
import sys
from pathlib import Path
import shutil
import random
import json
from datetime import datetime

sys.path.insert(0, '/home/rusty_admin/projects/reachy_08.4.2')

run_id = '$RUN_ID'
samples_per_class = $SAMPLES_PER_CLASS
videos_root = Path('$VIDEOS_ROOT')
seed = 42

# Test dataset directory
test_dir = videos_root / 'test' / run_id
test_dir.mkdir(parents=True, exist_ok=True)

# Ground truth manifest
manifest_path = videos_root / 'manifests' / f'{run_id}_test_labels.jsonl'
manifest_path.parent.mkdir(parents=True, exist_ok=True)

random.seed(seed)
ground_truth = []
total_added = 0

for label in ['happy', 'sad', 'neutral']:
    src_dir = videos_root / 'train' / label
    affectnet_images = sorted(src_dir.glob('affectnet_*.jpg'))
    
    # Use images not in training (offset by 3690 to avoid overlap)
    offset = 3690
    available = affectnet_images[offset:]
    
    if len(available) < samples_per_class:
        print(f"⚠ Warning: Only {len(available)} {label} images available (requested {samples_per_class})")
        selected = available
    else:
        selected = available[:samples_per_class]
    
    print(f"Adding {len(selected)} {label} test samples...")
    
    for idx, img in enumerate(selected):
        # Unlabeled filename for test set
        dst_name = f"test_{run_id}_{label[0]}_{idx:04d}.jpg"
        dest_path = test_dir / dst_name
        
        if dest_path.exists():
            print(f"  ⚠ Skipped (exists): {dst_name}")
            continue
        
        shutil.copy2(img, dest_path)
        
        # Ground truth entry (kept separate)
        ground_truth.append({
            "file_path": f"test/{run_id}/{dst_name}",
            "label": label,
            "source": "affectnet",
            "original_path": str(img),
            "added_at": datetime.now().isoformat()
        })
        
        total_added += 1

# Save ground truth manifest
with open(manifest_path, 'w') as f:
    for entry in ground_truth:
        f.write(json.dumps(entry) + '\\n')

print(f"\n✓ Test dataset created")
print(f"  Total samples: {total_added}")
print(f"  Location: {test_dir}")
print(f"  Ground truth: {manifest_path}")

PYTHON_EOF

echo ""
echo "✓ AffectNet test dataset created for: $RUN_ID"
echo ""
echo "Test dataset location:"
echo "  $VIDEOS_ROOT/test/$RUN_ID/"
echo ""
echo "Ground truth manifest:"
echo "  $VIDEOS_ROOT/manifests/${RUN_ID}_test_labels.jsonl"
