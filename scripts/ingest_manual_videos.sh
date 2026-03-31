#!/bin/bash
# Ingest manually-copied videos from a source directory
# Usage: ./scripts/ingest_manual_videos.sh <source_dir> <emotion_label>
# Example: ./scripts/ingest_manual_videos.sh /tmp/my_videos happy

set -e

SOURCE_DIR=$1
EMOTION=$2
VIDEOS_ROOT="/media/rusty_admin/project_data/reachy_emotion/videos"

if [ -z "$SOURCE_DIR" ] || [ -z "$EMOTION" ]; then
    echo "Usage: $0 <source_dir> <emotion_label>"
    echo "Example: $0 /tmp/my_videos happy"
    echo ""
    echo "Valid emotions: happy, sad, neutral"
    exit 1
fi

if [[ ! "$EMOTION" =~ ^(happy|sad|neutral)$ ]]; then
    echo "Error: Invalid emotion. Must be: happy, sad, or neutral"
    exit 1
fi

echo "============================================"
echo "Manual Video Ingestion"
echo "============================================"
echo "Source: $SOURCE_DIR"
echo "Emotion: $EMOTION"
echo "============================================"
echo ""

python << PYTHON_EOF
import sys
from pathlib import Path
import shutil
from datetime import datetime
import hashlib

sys.path.insert(0, '/home/rusty_admin/projects/reachy_08.4.2')

source_dir = Path('$SOURCE_DIR')
emotion = '$EMOTION'
videos_root = Path('$VIDEOS_ROOT')
train_dir = videos_root / 'train' / emotion

train_dir.mkdir(parents=True, exist_ok=True)

# Find all video files
video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
video_files = [f for f in source_dir.glob('*') if f.suffix.lower() in video_extensions]

print(f"Found {len(video_files)} video files")

copied = 0
skipped = 0

for video in video_files:
    # Generate SHA256 hash
    sha256 = hashlib.sha256()
    with open(video, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    
    file_hash = sha256.hexdigest()[:16]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # New filename: manual_<emotion>_<timestamp>_<hash>.mp4
    new_name = f"manual_{emotion}_{timestamp}_{file_hash}{video.suffix}"
    dest_path = train_dir / new_name
    
    if dest_path.exists():
        print(f"  ⚠ Skipped (exists): {video.name}")
        skipped += 1
        continue
    
    # Copy file
    shutil.copy2(video, dest_path)
    print(f"  ✓ Copied: {video.name} → {new_name}")
    copied += 1

print(f"\n✓ Ingestion complete")
print(f"  Copied: {copied}")
print(f"  Skipped: {skipped}")
print(f"  Destination: {train_dir}")

PYTHON_EOF

echo ""
echo "✓ Manual videos ingested to: $VIDEOS_ROOT/train/$EMOTION/"
echo ""
echo "Next steps:"
echo "  1. Videos are ready for next training run"
echo "  2. Or register in database: python scripts/register_videos.py"
