#!/usr/bin/env python3
"""
Register all renamed videos in the database.
This script scans the train directories and registers videos that were
renamed but failed database registration due to authentication issues.
"""

import asyncio
import hashlib
import os
import sys
from pathlib import Path
from datetime import datetime

import cv2
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.api.app.db.models import Video

# Database connection - use correct password
DB_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://reachy_dev:tweetwd4959@/reachy_emotion?host=/var/run/postgresql'
)

VIDEOS_ROOT = Path('/media/rusty_admin/project_data/reachy_emotion/videos')
TRAIN_DIR = VIDEOS_ROOT / 'train'

engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_video_metadata(video_path: Path) -> dict:
    """Extract metadata from video file."""
    try:
        cap = cv2.VideoCapture(str(video_path))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        cap.release()
        
        # Compute SHA256 hash
        sha256_hash = hashlib.sha256()
        with open(video_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256_hash.update(chunk)
        sha256 = sha256_hash.hexdigest()
        
        # Get file size
        size_bytes = video_path.stat().st_size
        
        return {
            'width': width,
            'height': height,
            'fps': fps,
            'duration': duration,
            'sha256': sha256,
            'size_bytes': size_bytes
        }
    except Exception as e:
        print(f"  ✗ Error extracting metadata: {e}")
        return None


async def register_video_in_db(file_path: str, emotion: str, metadata: dict) -> str:
    """Register video in database with metadata."""
    async with AsyncSessionLocal() as session:
        try:
            # Check if video already exists by sha256 + size
            result = await session.execute(
                select(Video).where(
                    Video.sha256 == metadata['sha256'],
                    Video.size_bytes == metadata['size_bytes']
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                return f"EXISTS:{existing.video_id}"
            
            # Insert new video record
            now = datetime.now()
            video_data = {
                'file_path': file_path,
                'split': 'train',
                'label': emotion,
                'duration_sec': metadata['duration'],
                'fps': metadata['fps'],
                'width': metadata['width'],
                'height': metadata['height'],
                'size_bytes': metadata['size_bytes'],
                'sha256': metadata['sha256'],
                'created_at': now,
                'updated_at': now,
                'extra_data': {
                    'source': 'manual_luma',
                    'ingested_at': now.isoformat()
                }
            }
            
            result = await session.execute(
                insert(Video).values(**video_data).returning(Video.video_id)
            )
            video_id = result.scalar_one()
            await session.commit()
            return f"NEW:{video_id}"
            
        except Exception as e:
            await session.rollback()
            return f"ERROR:{str(e)}"


async def process_emotion_directory(emotion: str):
    """Process all videos in an emotion directory."""
    emotion_dir = TRAIN_DIR / emotion
    
    if not emotion_dir.exists():
        print(f"⚠ Directory not found: {emotion_dir}")
        return
    
    # Find all video files
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
    video_files = sorted([
        f for f in emotion_dir.glob('*')
        if f.suffix.lower() in video_extensions
    ])
    
    if not video_files:
        print(f"  No video files found in {emotion_dir}")
        return
    
    print(f"\nProcessing: {emotion}")
    print(f"  Found {len(video_files)} video files")
    print("----------------------------------------")
    
    registered = 0
    already_exists = 0
    errors = 0
    
    for i, video_path in enumerate(video_files, 1):
        try:
            # Extract metadata
            metadata = await get_video_metadata(video_path)
            if not metadata:
                errors += 1
                continue
            
            # Register in database
            rel_path = f"train/{emotion}/{video_path.name}"
            result = await register_video_in_db(rel_path, emotion, metadata)
            
            if result.startswith("NEW:"):
                video_id = result.split(":", 1)[1]
                print(f"  [{i}/{len(video_files)}] ✓ Registered: {video_path.name[:50]}... → {video_id}")
                registered += 1
            elif result.startswith("EXISTS:"):
                video_id = result.split(":", 1)[1]
                already_exists += 1
                if already_exists <= 5:  # Only show first 5
                    print(f"  [{i}/{len(video_files)}] ⚠ Already exists: {video_path.name[:50]}... → {video_id}")
            else:  # ERROR
                error_msg = result.split(":", 1)[1]
                print(f"  [{i}/{len(video_files)}] ✗ Error: {video_path.name[:50]}... → {error_msg}")
                errors += 1
            
            # Progress update every 100 videos
            if i % 100 == 0:
                print(f"  Progress: {i}/{len(video_files)} ({i*100//len(video_files)}%)")
        
        except Exception as e:
            print(f"  [{i}/{len(video_files)}] ✗ Exception: {video_path.name[:50]}... → {e}")
            errors += 1
    
    print("")
    print(f"  Summary for {emotion}:")
    print(f"    New registrations: {registered}")
    print(f"    Already existed: {already_exists}")
    print(f"    Errors: {errors}")
    print(f"    Total processed: {len(video_files)}")
    print("")


async def main():
    """Main entry point."""
    print("=" * 60)
    print("Register Renamed Videos in Database")
    print("=" * 60)
    print(f"Database: {DB_URL.split('@')[1]}")  # Hide password
    print(f"Videos root: {VIDEOS_ROOT}")
    print("")
    
    # Test database connection
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Video).limit(1))
            print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("\nPlease check:")
        print("  1. PostgreSQL is running")
        print("  2. Database credentials are correct")
        print("  3. Database 'reachy_emotion' exists")
        return 1
    
    print("")
    
    # Process each emotion directory
    for emotion in ['happy', 'sad', 'neutral']:
        await process_emotion_directory(emotion)
    
    print("=" * 60)
    print("✓ Registration complete")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
