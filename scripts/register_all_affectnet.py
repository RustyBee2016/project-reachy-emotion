#!/usr/bin/env python3
"""
Comprehensive AffectNet Database Registration Script

Registers ALL AffectNet training and validation images with their annotations
in the PostgreSQL database. Filters for human-label values 0, 1, 2 only.

Usage:
    # Test mode (first 100 images)
    python scripts/register_all_affectnet.py --test

    # Full registration (train_set)
    python scripts/register_all_affectnet.py --dataset train

    # Full registration (validation_set)
    python scripts/register_all_affectnet.py --dataset validation

    # Full registration (both)
    python scripts/register_all_affectnet.py --dataset both

    # Overwrite existing records
    python scripts/register_all_affectnet.py --dataset both --overwrite
"""

import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import argparse

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from PIL import Image

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.api.app.db.models import Video

# AffectNet paths
AFFECTNET_ROOT = Path("/media/rusty_admin/project_data/reachy_emotion/affectnet/consolidated/AffectNet+/human_annotated")
TRAIN_IMAGES = AFFECTNET_ROOT / "train_set" / "images"
TRAIN_ANNOTATIONS = AFFECTNET_ROOT / "train_set" / "annotations"
VALIDATION_IMAGES = AFFECTNET_ROOT / "validation_set" / "images"
VALIDATION_ANNOTATIONS = AFFECTNET_ROOT / "validation_set" / "annotations"

# Database connection
DB_URL = "postgresql://reachy_dev:tweetwd4959@/reachy_emotion?host=/var/run/postgresql"

# Emotion mapping (AffectNet human-label to our 3-class system)
EMOTION_MAP = {
    0: "neutral",
    1: "happy",
    2: "sad"
}


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def get_image_dimensions(image_path: Path) -> Tuple[int, int]:
    """Get image width and height."""
    try:
        with Image.open(image_path) as img:
            return img.size  # (width, height)
    except Exception as e:
        print(f"Warning: Could not read image dimensions for {image_path}: {e}")
        return (0, 0)


def parse_annotation(annotation_path: Path) -> Optional[Dict]:
    """
    Parse AffectNet annotation JSON file.
    
    Returns None if:
    - File doesn't exist
    - JSON is invalid
    - human-label is not 0, 1, or 2
    """
    if not annotation_path.exists():
        return None
    
    try:
        with open(annotation_path, 'r') as f:
            data = json.load(f)
        
        # Extract human-label
        human_label = data.get('human-label')
        
        # Filter: only accept 0, 1, 2
        if human_label not in [0, 1, 2]:
            return None
        
        # Parse all annotation fields
        annotation = {
            'human_label': human_label,
            'emotion': EMOTION_MAP[human_label],
            'valence': data.get('valence'),
            'arousal': data.get('arousal'),
            'expression': data.get('expression'),
            'age': data.get('age'),
            'gender': data.get('gender'),
            'ethnicity': data.get('ethnicity'),
            'pose': data.get('pose'),
            'soft_label': data.get('soft-label'),
            'face_x': data.get('face_x'),
            'face_y': data.get('face_y'),
            'face_width': data.get('face_width'),
            'face_height': data.get('face_height'),
            'facial_landmarks': data.get('facial_landmarks')
        }
        
        return annotation
        
    except Exception as e:
        print(f"Warning: Failed to parse {annotation_path}: {e}")
        return None


def create_video_record(
    image_path: Path,
    annotation: Dict,
    split: str,
    session,
    sha256: Optional[str] = None,
    file_size: Optional[int] = None
) -> Optional[Video]:
    """
    Create a Video database record for an AffectNet image.
    
    Args:
        image_path: Path to image file
        annotation: Parsed annotation dict
        split: 'train' or 'validation'
        session: SQLAlchemy session
        sha256: Pre-computed hash (optional)
        file_size: Pre-computed file size (optional)
    
    Returns:
        Video record or None if creation failed
    """
    try:
        # Compute hash if not provided
        if sha256 is None:
            sha256 = compute_sha256(image_path)
        
        # Get image dimensions
        width, height = get_image_dimensions(image_path)
        
        # Get file size if not provided
        if file_size is None:
            file_size = image_path.stat().st_size
        
        # Create record
        now = datetime.utcnow()
        
        record = Video(
            file_path=str(image_path),
            sha256=sha256,
            split=split,
            label=annotation['emotion'],
            duration_sec=None,  # Images don't have duration
            fps=None,  # Images don't have fps
            width=width,
            height=height,
            size_bytes=file_size,
            extra_data=annotation,  # Store all annotation metadata
            created_at=now,
            updated_at=now
        )
        
        return record
        
    except Exception as e:
        print(f"Error creating record for {image_path}: {e}")
        return None


def register_dataset(
    images_dir: Path,
    annotations_dir: Path,
    dataset_name: str,
    session,
    limit: Optional[int] = None,
    overwrite: bool = False
) -> Dict[str, int]:
    """
    Register all images from a dataset (train or validation).
    
    Args:
        images_dir: Directory containing images
        annotations_dir: Directory containing annotations
        dataset_name: 'train' or 'validation' (for logging only)
        session: SQLAlchemy session
        limit: Optional limit for testing (e.g., 100)
        overwrite: If True, delete existing records first
    
    Returns:
        Dict with statistics
    """
    # All AffectNet images go into 'train' split
    # (validation_set images are part of training pool, can be sampled for test later)
    split = 'train'
    stats = {
        'total_images': 0,
        'valid_annotations': 0,
        'invalid_annotations': 0,
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    # Get all image files
    image_files = sorted(images_dir.glob('*.jpg'))
    stats['total_images'] = len(image_files)
    
    if limit:
        image_files = image_files[:limit]
        print(f"Test mode: Processing first {limit} images")
    
    print(f"\nProcessing {len(image_files)} images from {dataset_name} set...")
    print(f"Images dir: {images_dir}")
    print(f"Annotations dir: {annotations_dir}")
    print(f"Database split: {split}")
    
    # Overwrite mode: delete existing records
    if overwrite:
        print(f"\nOverwrite mode: Deleting existing {dataset_name}_set records...")
        deleted = session.execute(
            text("DELETE FROM video WHERE file_path LIKE :pattern"),
            {"pattern": f"%{dataset_name}_set%"}
        ).rowcount
        session.commit()
        print(f"Deleted {deleted} existing records")
    
    # Process each image
    batch_size = 100
    batch = []
    
    for idx, image_path in enumerate(image_files, 1):
        # Find matching annotation
        annotation_path = annotations_dir / f"{image_path.stem}.json"
        
        # Parse annotation
        annotation = parse_annotation(annotation_path)
        
        if annotation is None:
            stats['invalid_annotations'] += 1
            continue
        
        stats['valid_annotations'] += 1
        
        # Compute hash and size once
        sha256 = compute_sha256(image_path)
        file_size = image_path.stat().st_size
        
        # Check if record exists (by file_path OR sha256+size)
        existing = session.query(Video).filter(
            (Video.file_path == str(image_path)) |
            ((Video.sha256 == sha256) & (Video.size_bytes == file_size))
        ).first()
        
        # Skip if exists and not overwriting
        if existing and not overwrite:
            stats['skipped'] += 1
            continue
        
        # Skip if existing record is in 'test' split (cannot update labels)
        if existing and existing.split == 'test':
            stats['skipped'] += 1
            continue
        
        # Create record (pass pre-computed hash and size)
        record = create_video_record(
            image_path, annotation, split, session, 
            sha256=sha256, file_size=file_size
        )
        
        if record is None:
            stats['errors'] += 1
            continue
        
        if existing:
            # Update existing
            existing.sha256 = record.sha256
            existing.label = record.label
            existing.width = record.width
            existing.height = record.height
            existing.size_bytes = record.size_bytes
            existing.extra_data = record.extra_data
            existing.updated_at = datetime.utcnow()
            stats['updated'] += 1
        else:
            # Add new
            batch.append(record)
            stats['created'] += 1
        
        # Commit in batches
        if len(batch) >= batch_size:
            session.add_all(batch)
            session.commit()
            batch = []
            print(f"  Processed {idx}/{len(image_files)} images... "
                  f"(created: {stats['created']}, updated: {stats['updated']}, "
                  f"skipped: {stats['skipped']}, errors: {stats['errors']})")
    
    # Commit remaining
    if batch:
        session.add_all(batch)
        session.commit()
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='Register AffectNet images in database')
    parser.add_argument(
        '--dataset',
        choices=['train', 'validation', 'both'],
        default='both',
        help='Which dataset to register'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: only process first 100 images'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing records'
    )
    parser.add_argument(
        '--db-url',
        default=DB_URL,
        help='Database connection URL'
    )
    
    args = parser.parse_args()
    
    # Create database session
    engine = create_engine(args.db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("=" * 60)
    print("AffectNet Database Registration")
    print("=" * 60)
    print(f"Dataset: {args.dataset}")
    print(f"Test mode: {args.test}")
    print(f"Overwrite: {args.overwrite}")
    print(f"Database: {args.db_url.split('@')[1] if '@' in args.db_url else args.db_url}")
    print("=" * 60)
    
    limit = 100 if args.test else None
    
    total_stats = {
        'total_images': 0,
        'valid_annotations': 0,
        'invalid_annotations': 0,
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    try:
        # Register training set
        if args.dataset in ['train', 'both']:
            print("\n" + "=" * 60)
            print("TRAINING SET")
            print("=" * 60)
            stats = register_dataset(
                TRAIN_IMAGES,
                TRAIN_ANNOTATIONS,
                'train',  # dataset_name
                session,
                limit=limit,
                overwrite=args.overwrite
            )
            
            for key in total_stats:
                total_stats[key] += stats[key]
            
            print("\nTraining set statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        # Register validation set
        if args.dataset in ['validation', 'both']:
            print("\n" + "=" * 60)
            print("VALIDATION SET")
            print("=" * 60)
            stats = register_dataset(
                VALIDATION_IMAGES,
                VALIDATION_ANNOTATIONS,
                'validation',  # dataset_name
                session,
                limit=limit,
                overwrite=args.overwrite
            )
            
            for key in total_stats:
                total_stats[key] += stats[key]
            
            print("\nValidation set statistics:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
        
        # Print total statistics
        print("\n" + "=" * 60)
        print("TOTAL STATISTICS")
        print("=" * 60)
        for key, value in total_stats.items():
            print(f"  {key}: {value}")
        
        # Query final counts
        print("\n" + "=" * 60)
        print("DATABASE VERIFICATION")
        print("=" * 60)
        
        for dataset in ['train', 'validation']:
            for label in ['happy', 'sad', 'neutral']:
                count = session.query(Video).filter_by(
                    split='train',  # All AffectNet images are in 'train' split
                    label=label
                ).filter(
                    Video.file_path.like(f'%{dataset}_set%')
                ).count()
                print(f"  {dataset}_set/{label}: {count} records")
        
        print("\n✓ Registration complete!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return 1
    
    finally:
        session.close()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
