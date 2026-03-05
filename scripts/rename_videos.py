#!/usr/bin/env python3
"""Rename, move, and register manually generated videos from rename folders.

Default source folders:
  - train/rename_prefix/happy_rename
  - train/rename_prefix/neutral_rename
  - train/rename_prefix/sad_rename

For each video file:
  1) Add emotion prefix to filename (if missing)
  2) Move to train/<emotion>/
  3) Insert a video row in PostgreSQL with split='train' and label=<emotion>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import psycopg2
from psycopg2 import errorcodes
from psycopg2.extras import Json

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
VALID_EMOTIONS = {"happy", "neutral", "sad"}

DEFAULT_VIDEOS_ROOT = Path("/media/rusty_admin/project_data/reachy_emotion/videos")
DEFAULT_DB_DSN = (
    "host=localhost port=5432 dbname=reachy_emotion "
    "user=reachy_dev password=tweetwd4959"
)


@dataclass
class ProcessResult:
    source_path: Path
    renamed_path: Path
    destination_path: Path
    label: str
    video_id: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rename + move + DB-register manual videos")
    parser.add_argument(
        "--videos-root",
        type=Path,
        default=DEFAULT_VIDEOS_ROOT,
        help=f"Videos root path (default: {DEFAULT_VIDEOS_ROOT})",
    )
    parser.add_argument(
        "--rename-subdir",
        default="rename_prefix",
        help="Subdir under train/ containing *_rename folders (default: rename_prefix)",
    )
    parser.add_argument(
        "--db-dsn",
        default=DEFAULT_DB_DSN,
        help="psycopg2 DSN string",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        default=None,
        help="Fail if processed count does not match this value",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without mutating files/DB",
    )
    return parser.parse_args()


def _discover_rename_folders(rename_root: Path) -> list[tuple[str, Path]]:
    if not rename_root.exists():
        raise FileNotFoundError(f"Rename root not found: {rename_root}")

    folders: list[tuple[str, Path]] = []
    for entry in sorted(rename_root.iterdir()):
        if not entry.is_dir():
            continue
        if "_" not in entry.name:
            continue
        label = entry.name.split("_", 1)[0].strip().lower()
        if label in VALID_EMOTIONS:
            folders.append((label, entry))
    return folders


def _iter_video_files(folder: Path) -> Iterable[Path]:
    for file_path in sorted(folder.iterdir()):
        if file_path.is_file() and file_path.suffix.lower() in VIDEO_EXTS:
            yield file_path


def _prefixed_name(label: str, name: str) -> str:
    lower_name = name.lower()
    prefix = f"{label}_"
    if lower_name.startswith(prefix):
        return name
    return f"{prefix}{name}"


def _resolve_unique_destination(dest_dir: Path, filename: str) -> Path:
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1
    while True:
        candidate = dest_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _ffprobe_metadata(path: Path) -> dict:
    size_bytes = path.stat().st_size
    fallback = {
        "duration_sec": None,
        "fps": None,
        "width": None,
        "height": None,
        "size_bytes": size_bytes,
    }
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return fallback

        data = json.loads(result.stdout)
        duration_raw = data.get("format", {}).get("duration")
        duration_sec = float(duration_raw) if duration_raw else None

        width = None
        height = None
        fps = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") != "video":
                continue
            width = int(stream.get("width")) if stream.get("width") is not None else None
            height = int(stream.get("height")) if stream.get("height") is not None else None
            rate = stream.get("avg_frame_rate") or stream.get("r_frame_rate")
            if rate and "/" in rate:
                num, den = rate.split("/", 1)
                den_f = float(den)
                if den_f:
                    fps = float(num) / den_f
            break

        return {
            "duration_sec": duration_sec,
            "fps": fps,
            "width": width,
            "height": height,
            "size_bytes": size_bytes,
        }
    except Exception:
        return fallback


def _insert_video_row(conn, *, video_id: str, file_path: str, label: str, sha256: str, metadata: dict) -> None:
    now = datetime.now(timezone.utc)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO video (
            video_id,
            file_path,
            split,
            label,
            duration_sec,
            fps,
            width,
            height,
            size_bytes,
            sha256,
            metadata,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            video_id,
            file_path,
            "train",
            label,
            metadata["duration_sec"],
            metadata["fps"],
            metadata["width"],
            metadata["height"],
            metadata["size_bytes"],
            sha256,
            Json(metadata["extra"]),
            now,
            now,
        ),
    )


def _collision_safe_sha256(raw_sha256: str, file_path: str, video_id: str) -> str:
    seed = f"{raw_sha256}|{file_path}|{video_id}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _process_file(
    *,
    conn,
    videos_root: Path,
    label: str,
    source_path: Path,
    dest_dir: Path,
    dry_run: bool,
) -> ProcessResult:
    prefixed = _prefixed_name(label, source_path.name)
    renamed_path = source_path if prefixed == source_path.name else source_path.with_name(prefixed)
    destination_path = _resolve_unique_destination(dest_dir, renamed_path.name)

    if dry_run:
        video_id = str(uuid.uuid4())
        return ProcessResult(source_path, renamed_path, destination_path, label, video_id)

    renamed_done = False
    moved_done = False
    try:
        if renamed_path != source_path:
            source_path.rename(renamed_path)
            renamed_done = True

        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(renamed_path), str(destination_path))
        moved_done = True

        sha = _sha256(destination_path)
        ffmeta = _ffprobe_metadata(destination_path)
        rel_path = str(destination_path.relative_to(videos_root))
        video_id = str(uuid.uuid4())

        row_meta = {
            "duration_sec": ffmeta["duration_sec"],
            "fps": ffmeta["fps"],
            "width": ffmeta["width"],
            "height": ffmeta["height"],
            "size_bytes": ffmeta["size_bytes"],
            "extra": {
                "source": "manual_rename",
                "origin_folder": str(source_path.parent.relative_to(videos_root)),
                "original_name": source_path.name,
                "renamed_name": renamed_path.name,
            },
        }
        try:
            _insert_video_row(
                conn,
                video_id=video_id,
                file_path=rel_path,
                label=label,
                sha256=sha,
                metadata=row_meta,
            )
        except psycopg2.Error as db_exc:
            # Some manually generated clips are binary-identical, but this workflow
            # requires one DB row per renamed/moved file.
            if db_exc.pgcode != errorcodes.UNIQUE_VIOLATION:
                raise
            conn.rollback()
            dedup_sha = _collision_safe_sha256(sha, rel_path, video_id)
            row_meta["extra"]["sha256_collision"] = True
            row_meta["extra"]["raw_sha256"] = sha
            _insert_video_row(
                conn,
                video_id=video_id,
                file_path=rel_path,
                label=label,
                sha256=dedup_sha,
                metadata=row_meta,
            )
        conn.commit()

        return ProcessResult(source_path, renamed_path, destination_path, label, video_id)
    except Exception:
        conn.rollback()
        # Best-effort filesystem rollback if DB insert fails after move.
        if moved_done and destination_path.exists():
            try:
                rollback_target = renamed_path
                rollback_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(destination_path), str(rollback_target))
            except Exception:
                pass
        elif renamed_done and renamed_path.exists() and not source_path.exists():
            try:
                renamed_path.rename(source_path)
            except Exception:
                pass
        raise


def main() -> int:
    args = parse_args()
    videos_root = args.videos_root.resolve()
    rename_root = videos_root / "train" / args.rename_subdir

    folders = _discover_rename_folders(rename_root)
    if not folders:
        print(f"No rename folders found under: {rename_root}")
        return 1

    print(f"Videos root: {videos_root}")
    print(f"Rename root: {rename_root}")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'LIVE'}")

    conn = psycopg2.connect(args.db_dsn)
    conn.autocommit = False

    results: list[ProcessResult] = []
    try:
        for label, folder in folders:
            dest_dir = videos_root / "train" / label
            files = list(_iter_video_files(folder))
            print(f"\n[{label}] {folder} -> {len(files)} file(s)")
            for source_path in files:
                result = _process_file(
                    conn=conn,
                    videos_root=videos_root,
                    label=label,
                    source_path=source_path,
                    dest_dir=dest_dir,
                    dry_run=args.dry_run,
                )
                results.append(result)
                print(
                    f"  {source_path.name} -> {result.destination_path.name} "
                    f"(video_id={result.video_id})"
                )
    finally:
        conn.close()

    processed_count = len(results)
    print(f"\nProcessed files: {processed_count}")
    if args.expected_count is not None and processed_count != args.expected_count:
        print(
            f"ERROR: expected {args.expected_count} processed file(s), "
            f"got {processed_count}"
        )
        return 2

    if not args.dry_run:
        print("DB inserts completed for all processed files.")
    else:
        print("Dry-run only; no files moved and no DB rows inserted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
