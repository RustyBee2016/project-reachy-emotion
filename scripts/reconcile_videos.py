#!/usr/bin/env python3
"""One-time reconciliation script for video DB ↔ filesystem drift.

Actions:
  1. Rename manually-placed videos in train/{emotion}/ to {emotion}_luma_*.mp4
  2. Register renamed videos in the DB (video table)
  3. Delete orphaned DB rows whose files no longer exist on disk

Usage:
    python scripts/reconcile_videos.py --dry-run   # preview only
    python scripts/reconcile_videos.py              # apply changes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
VIDEOS_ROOT = Path("/media/rusty_admin/project_data/reachy_emotion/videos")
TRAIN_DIR = VIDEOS_ROOT / "train"
EMOTIONS = ["happy", "sad", "neutral"]
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv"}

DB_DSN = "host=localhost port=5432 dbname=reachy_emotion user=reachy_dev password=tweetwd4959"

_conn = None


def _get_conn():
    """Return a shared psycopg2 connection."""
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(DB_DSN)
        _conn.autocommit = True
    return _conn


def _query(sql: str, params: tuple = ()) -> list:
    """Execute a SQL query and return rows."""
    cur = _get_conn().cursor()
    cur.execute(sql, params)
    try:
        return cur.fetchall()
    except psycopg2.ProgrammingError:
        return []


def _execute(sql: str, params: tuple = ()) -> None:
    """Execute a SQL statement (no return)."""
    cur = _get_conn().cursor()
    cur.execute(sql, params)


def _sha256(path: Path) -> str:
    """Compute SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_video_metadata(path: Path) -> dict:
    """Extract duration, fps, width, height, size_bytes via ffprobe."""
    size_bytes = path.stat().st_size
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                str(path),
            ],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(result.stdout)
        fmt = data.get("format", {})
        duration = float(fmt.get("duration", 0))

        # Find video stream
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                w = int(stream.get("width", 0))
                h = int(stream.get("height", 0))
                r_str = stream.get("r_frame_rate", "30/1")
                num, den = r_str.split("/")
                fps = float(num) / float(den) if float(den) > 0 else 30.0
                return {"duration": duration, "fps": fps, "width": w, "height": h, "size_bytes": size_bytes}

        return {"duration": duration, "fps": 30.0, "width": 0, "height": 0, "size_bytes": size_bytes}
    except Exception as e:
        print(f"  [WARN] ffprobe failed for {path.name}: {e}")
        return {"duration": 0.0, "fps": 30.0, "width": 0, "height": 0, "size_bytes": size_bytes}


def _make_luma_name(emotion: str, original: str) -> str:
    """Convert a manually-named file to {emotion}_luma_{original_stem}.mp4

    Input:  2026-01-22T00-30-58_create_a.mp4
    Output: happy_luma_20260122_003058.mp4
    """
    stem = Path(original).stem
    # Try to extract timestamp from ISO-like format: 2026-01-22T00-30-58
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2})-(\d{2})-(\d{2})", stem)
    if m:
        ts = "".join(m.groups()[:3]) + "_" + "".join(m.groups()[3:])
        return f"{emotion}_luma_{ts}.mp4"

    # Already has emotion prefix? Return as-is
    for emo in EMOTIONS:
        if stem.startswith(f"{emo}_"):
            return original

    # Fallback: just prefix
    return f"{emotion}_luma_{stem}.mp4"


def step1_rename_videos(dry_run: bool) -> list[tuple[Path, Path]]:
    """Rename manually-placed videos to standardized names."""
    renames: list[tuple[Path, Path]] = []

    for emotion in EMOTIONS:
        emotion_dir = TRAIN_DIR / emotion
        if not emotion_dir.is_dir():
            continue

        for f in sorted(emotion_dir.iterdir()):
            if f.suffix.lower() not in VIDEO_EXTS:
                continue
            # Skip files that already have the correct prefix
            if f.name.startswith(f"{emotion}_"):
                print(f"  [SKIP] {f.name} (already prefixed)")
                continue

            new_name = _make_luma_name(emotion, f.name)
            new_path = emotion_dir / new_name

            if new_path.exists() and new_path != f:
                print(f"  [CONFLICT] {new_name} already exists, skipping {f.name}")
                continue

            print(f"  [RENAME] {emotion}/{f.name} → {emotion}/{new_name}")
            renames.append((f, new_path))

            if not dry_run:
                f.rename(new_path)

    return renames


def step2_register_videos(dry_run: bool) -> int:
    """Register all videos in train/{emotion}/ that are missing from the DB."""
    registered = 0

    for emotion in EMOTIONS:
        emotion_dir = TRAIN_DIR / emotion
        if not emotion_dir.is_dir():
            continue

        for f in sorted(emotion_dir.iterdir()):
            if f.suffix.lower() not in VIDEO_EXTS:
                continue

            rel_path = f"train/{emotion}/{f.name}"
            # Check if already in DB (always check, even in dry-run)
            rows = _query(
                "SELECT count(*) FROM video WHERE file_path = %s;",
                (rel_path,),
            )
            if rows and rows[0][0] > 0:
                print(f"  [EXISTS] {rel_path} already in DB")
                continue

            # Compute metadata
            sha = _sha256(f)
            meta = _get_video_metadata(f)
            video_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            print(f"  [INSERT] {rel_path}  id={video_id[:8]}  sha={sha[:12]}  "
                  f"{meta['duration']:.1f}s {meta['width']}x{meta['height']}")

            if not dry_run:
                _execute(
                    "INSERT INTO video "
                    "(video_id, file_path, sha256, split, label, "
                    "duration_sec, fps, width, height, size_bytes, "
                    "created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
                    (video_id, rel_path, sha, "train", emotion,
                     round(meta["duration"], 2), round(meta["fps"], 1),
                     meta["width"], meta["height"], meta["size_bytes"],
                     now, now),
                )

            registered += 1

    return registered


def step3_cleanup_orphans(dry_run: bool) -> int:
    """Delete DB rows whose files no longer exist on disk."""
    rows = _query("SELECT video_id, file_path FROM video WHERE split = 'train';")
    if not rows:
        print("  [INFO] No train videos in DB to check")
        return 0

    deleted = 0
    for vid, rel_path in rows:
        full_path = VIDEOS_ROOT / rel_path
        if not full_path.exists():
            print(f"  [DELETE] {rel_path}  id={vid[:8]}  (file missing)")
            if not dry_run:
                _execute("DELETE FROM video WHERE video_id = %s;", (vid,))
            deleted += 1

    return deleted


def main():
    parser = argparse.ArgumentParser(description="Reconcile video DB with filesystem")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without applying them")
    args = parser.parse_args()

    mode = "DRY-RUN" if args.dry_run else "LIVE"
    print(f"\n{'='*60}")
    print(f"  Video Reconciliation Script [{mode}]")
    print(f"{'='*60}\n")

    # Step 1: Rename
    print("Step 1: Rename manually-placed videos to standard naming")
    print("-" * 50)
    renames = step1_rename_videos(args.dry_run)
    print(f"  → {len(renames)} files renamed\n")

    # Step 2: Register
    print("Step 2: Register filesystem videos in DB")
    print("-" * 50)
    registered = step2_register_videos(args.dry_run)
    print(f"  → {registered} videos registered\n")

    # Step 3: Cleanup orphans
    print("Step 3: Remove orphaned DB rows (file missing)")
    print("-" * 50)
    deleted = step3_cleanup_orphans(args.dry_run)
    print(f"  → {deleted} orphaned rows deleted\n")

    # Summary
    print(f"{'='*60}")
    print(f"  Summary: {len(renames)} renamed, {registered} registered, {deleted} orphans deleted")
    if args.dry_run:
        print(f"  Re-run without --dry-run to apply changes")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
