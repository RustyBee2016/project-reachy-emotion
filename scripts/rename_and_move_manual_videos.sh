#!/bin/bash
# Rename and move manually-generated videos from rename_prefix directories
# This script processes videos from:
#   /videos/train/rename_prefix/happy_rename/
#   /videos/train/rename_prefix/sad_rename/
#   /videos/train/rename_prefix/neutral_rename/
# 
# Videos are renamed with emotion prefix and moved to:
#   /videos/train/happy/
#   /videos/train/sad/
#   /videos/train/neutral/

set -e

VIDEOS_ROOT="/media/rusty_admin/project_data/reachy_emotion/videos"
RENAME_PREFIX_DIR="$VIDEOS_ROOT/train/rename_prefix"
PROJECT_ROOT="/home/rusty_admin/projects/reachy_08.4.2"

echo "============================================"
echo "Manual Video Rename and Move"
echo "============================================"
echo "Processing videos from rename_prefix directories"
echo "============================================"
echo ""

# Check if rename_prefix directory exists
if [ ! -d "$RENAME_PREFIX_DIR" ]; then
    echo "Error: rename_prefix directory not found: $RENAME_PREFIX_DIR"
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
    
    # Run Python script to rename, move, and register videos in database
    python3 << PYTHON_EOF
import sys
from pathlib import Path
import shutil
from datetime import datetime
import hashlib
import cv2
import asyncio
import os

sys.path.insert(0, '$PROJECT_ROOT')

# Database registration
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import insert, select
from apps.api.app.db.models import Video

# Database connection
DB_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://reachy_dev:tweetwd4959@/reachy_emotion?host=/var/run/postgresql')
engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def register_video_in_db(file_path: str, emotion: str, sha256: str, size_bytes: int, width: int, height: int, duration: float, fps: float):
    """Register video in database with metadata."""
    async with AsyncSessionLocal() as session:
        try:
            # Check if video already exists by sha256 + size
            result = await session.execute(
                select(Video).where(
                    Video.sha256 == sha256,
                    Video.size_bytes == size_bytes
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"    ⚠ Video already in DB: {existing.video_id}")
                return existing.video_id
            
            # Insert new video record
            video_data = {
                'file_path': file_path,
                'split': 'train',
                'label': emotion,
                'duration_sec': duration,
                'fps': fps,
                'width': width,
                'height': height,
                'size_bytes': size_bytes,
                'sha256': sha256,
                'extra_data': {'source': 'manual_luma', 'ingested_at': datetime.now().isoformat()}
            }
            
            result = await session.execute(insert(Video).values(**video_data).returning(Video.video_id))
            video_id = result.scalar_one()
            await session.commit()
            print(f"    ✓ Registered in DB: {video_id}")
            return video_id
            
        except Exception as e:
            print(f"    ✗ DB registration failed: {e}")
            await session.rollback()
            return None

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
        print(f"  ✓ Moved: {video.name} → {new_name}")
        
        # Register in database
        rel_path = f"train/{emotion}/{new_name}"
        video_id = asyncio.run(register_video_in_db(
            file_path=rel_path,
            emotion=emotion,
            sha256=sha256,
            size_bytes=size_bytes,
            width=width,
            height=height,
            duration=duration,
            fps=fps
        ))
        
        if video_id:
            moved += 1
        else:
            skipped += 1
        
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
echo "✓ All manual videos processed"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Verify videos in train/<emotion>/ directories"
echo "  2. Run: python -m trainer.ingest_affectnet train"
echo "  3. Run: python -m trainer.build_consolidated_dataset --run-id run_0001"
echo ""
