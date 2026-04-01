#!/bin/bash
# TEST VERSION - Rename and move manual videos from /tmp/test_rename directories
# This is for testing before running on production data

set -e

VIDEOS_ROOT="/tmp/test_output"
RENAME_PREFIX_DIR="/tmp/test_rename"
PROJECT_ROOT="/home/rusty_admin/projects/reachy_08.4.2"

echo "============================================"
echo "TEST: Manual Video Rename and Move"
echo "============================================"
echo "Processing videos from TEST directories"
echo "Output to: $VIDEOS_ROOT"
echo "============================================"
echo ""

# Create output directories
mkdir -p "$VIDEOS_ROOT/train/happy"
mkdir -p "$VIDEOS_ROOT/train/sad"
mkdir -p "$VIDEOS_ROOT/train/neutral"

# Check if rename_prefix directory exists
if [ ! -d "$RENAME_PREFIX_DIR" ]; then
    echo "Error: test directory not found: $RENAME_PREFIX_DIR"
    exit 1
fi

# Process each emotion class
for emotion_dir in "$RENAME_PREFIX_DIR"/*_rename; do
    if [ ! -d "$emotion_dir" ]; then
        continue
    fi
    
    # Extract emotion from directory name (e.g., happy_rename -> happy)
    dir_name=$(basename "$emotion_dir")
    emotion="${dir_name%_rename}"
    
    # Validate emotion
    if [[ ! "$emotion" =~ ^(happy|sad|neutral)$ ]]; then
        echo "⚠ Skipping invalid emotion directory: $dir_name"
        continue
    fi
    
    echo "Processing: $emotion (from $dir_name)"
    echo "----------------------------------------"
    
    # Run Python script to rename and move videos (NO DATABASE for testing)
    python3 << PYTHON_EOF
import sys
from pathlib import Path
import shutil
from datetime import datetime
import hashlib
import cv2

sys.path.insert(0, '$PROJECT_ROOT')

emotion = '$emotion'
source_dir = Path('$emotion_dir')
videos_root = Path('$VIDEOS_ROOT')
dest_dir = videos_root / 'train' / emotion

# Create destination directory
dest_dir.mkdir(parents=True, exist_ok=True)

# Find all video files
video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
video_files = sorted([f for f in source_dir.glob('*') if f.suffix.lower() in video_extensions])

if not video_files:
    print(f"  No video files found in {source_dir}")
    sys.exit(0)

print(f"  Found {len(video_files)} video files")
print("")

moved = 0
skipped = 0

for video in video_files:
    try:
        # Generate timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:19]  # Include microseconds for uniqueness
        
        # New filename: <emotion>_luma_<timestamp>.mp4
        new_name = f"{emotion}_luma_{timestamp}{video.suffix}"
        dest_path = dest_dir / new_name
        
        # Check if destination already exists
        if dest_path.exists():
            print(f"  ⚠ Skipped (exists): {video.name} → {new_name}")
            skipped += 1
            continue
        
        # Get video metadata using cv2
        cap = cv2.VideoCapture(str(video))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        cap.release()
        
        # Compute SHA256 hash
        sha256_hash = hashlib.sha256()
        with open(video, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256_hash.update(chunk)
        sha256 = sha256_hash.hexdigest()
        
        # Get file size
        size_bytes = video.stat().st_size
        
        # Move file (rename operation)
        shutil.move(str(video), str(dest_path))
        
        # Display metadata
        print(f"  ✓ Moved: {video.name}")
        print(f"    → {new_name}")
        print(f"    Metadata: {width}x{height}, {fps:.1f}fps, {duration:.1f}s, {size_bytes/1024:.0f}KB")
        print(f"    SHA256: {sha256[:16]}...")
        
        moved += 1
        
    except Exception as e:
        print(f"  ✗ Error processing {video.name}: {e}")
        skipped += 1

print("")
print(f"  Summary for {emotion}:")
print(f"    Moved: {moved}")
print(f"    Skipped: {skipped}")
print(f"    Destination: {dest_dir}")
print("")

PYTHON_EOF

    echo ""
done

echo "============================================"
echo "✓ TEST complete - Review results in:"
echo "  $VIDEOS_ROOT/train/"
echo "============================================"
echo ""
echo "If results look good, run the production script:"
echo "  ./scripts/rename_and_move_manual_videos.sh"
echo ""
