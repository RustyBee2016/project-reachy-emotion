#!/usr/bin/env python3
"""Register AffectNet images in database from manifest."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from apps.api.app.db.models import Video


def utcnow():
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def register_images(manifest_path: Path, db_url: str):
    """Register images from manifest."""
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    created = 0
    skipped = 0
    
    try:
        with open(manifest_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                
                try:
                    record = json.loads(line)
                    
                    # Check if exists
                    if session.query(Video).filter_by(sha256=record['sha256']).first():
                        skipped += 1
                        continue
                    
                    # Create record with explicit timestamps
                    now = utcnow()
                    video = Video(
                        file_path=record['file_path'],
                        split='train',
                        label=record['label'],
                        sha256=record['sha256'],
                        size_bytes=record['size_bytes'],
                        width=record['width'],
                        height=record['height'],
                        duration_sec=None,
                        fps=None,
                        extra_data=record.get('metadata', {}),
                        created_at=now,
                        updated_at=now,
                    )
                    
                    session.add(video)
                    created += 1
                    
                    if created % 50 == 0:
                        print(f"Processed {created} records...")
                        
                except Exception as e:
                    print(f"Error on line {line_num}: {e}")
        
        session.commit()
        print(f"\n✓ Created {created} records, skipped {skipped}")
        
    except Exception as e:
        session.rollback()
        print(f"Failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--db-url", default="postgresql://reachy_dev:tweetwd4959@/reachy_emotion?host=/var/run/postgresql")
    args = parser.parse_args()
    
    register_images(Path(args.manifest), args.db_url)
