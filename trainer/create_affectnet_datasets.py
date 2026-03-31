#!/usr/bin/env python3
"""
Create balanced train/test datasets from AffectNet+ annotations.

Filters for 3-class emotions (0=neutral, 1=happy, 2=sad), balances
classes, splits into train and test-pool, then creates a run-specific
test set.  Inserts DB records and generates manifests.

Usage:
    python -m trainer.create_affectnet_datasets \
        --run-id run_0300 \
        --train-per-class 20000 \
        --test-per-class 500 \
        --seed 42 \
        -v
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AffectNet label mapping (only the 3 classes we care about)
# ---------------------------------------------------------------------------
LABEL_MAP = {0: "neutral", 1: "happy", 2: "sad"}
TARGET_LABELS = set(LABEL_MAP.keys())

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
AFFECTNET_ROOT = Path(
    "/media/rusty_admin/project_data/reachy_emotion/affectnet/consolidated/AffectNet+"
)
TRAIN_IMAGES = AFFECTNET_ROOT / "human_annotated" / "train_set" / "images"
TRAIN_ANNOTS = AFFECTNET_ROOT / "human_annotated" / "train_set" / "annotations"
VAL_IMAGES = AFFECTNET_ROOT / "human_annotated" / "validation_set" / "images"
VAL_ANNOTS = AFFECTNET_ROOT / "human_annotated" / "validation_set" / "annotations"

VIDEOS_ROOT = Path("/media/rusty_admin/project_data/reachy_emotion/videos")

DB_DSN = "host=/var/run/postgresql dbname=reachy_emotion user=reachy_dev password=tweetwd4959"


# ===========================================================================
# Phase 1: Scan & Filter Annotations
# ===========================================================================

def scan_annotations(
    annot_dir: Path,
    image_dir: Path,
) -> Dict[int, List[Dict[str, Any]]]:
    """Scan annotation JSONs and return entries grouped by human-label.

    Only includes labels in TARGET_LABELS (0, 1, 2).
    Verifies that the corresponding image file exists.
    """
    by_label: Dict[int, List[Dict[str, Any]]] = {k: [] for k in TARGET_LABELS}
    files = sorted(annot_dir.iterdir())
    total = len(files)
    skipped = 0

    for i, annot_path in enumerate(files):
        if annot_path.suffix != ".json":
            continue
        stem = annot_path.stem
        img_path = image_dir / f"{stem}.jpg"
        if not img_path.exists():
            skipped += 1
            continue

        with open(annot_path) as fh:
            data = json.load(fh)

        label_code = data.get("human-label")
        if label_code not in TARGET_LABELS:
            continue

        entry = {
            "stem": stem,
            "image_path": str(img_path),
            "annot_path": str(annot_path),
            "label_code": label_code,
            "label_name": LABEL_MAP[label_code],
            "annotation": data,
        }
        by_label[label_code].append(entry)

        if (i + 1) % 50000 == 0:
            logger.info(f"  Scanned {i+1:,}/{total:,} annotations...")

    logger.info(f"Scan complete. Skipped {skipped:,} (missing image).")
    for code, entries in sorted(by_label.items()):
        logger.info(f"  {LABEL_MAP[code]}: {len(entries):,}")

    return by_label


# ===========================================================================
# Phase 2: Balance & Split
# ===========================================================================

def balance_and_split(
    by_label: Dict[int, List[Dict[str, Any]]],
    train_per_class: int,
    test_per_class: int,
    seed: int,
) -> Tuple[List[Dict], List[Dict]]:
    """Balance classes, then split into train and test-pool portions.

    Returns (train_entries, test_pool_entries).
    Both lists are shuffled.
    """
    rng = random.Random(seed)

    # Find the effective ceiling per class
    min_available = min(len(v) for v in by_label.values())
    needed = train_per_class + test_per_class
    if needed > min_available:
        logger.warning(
            f"Requested {needed:,} per class but smallest class has {min_available:,}. "
            f"Adjusting train_per_class to {min_available - test_per_class:,}."
        )
        train_per_class = min_available - test_per_class

    train_entries: List[Dict] = []
    test_pool_entries: List[Dict] = []

    for code in sorted(TARGET_LABELS):
        entries = by_label[code][:]
        rng.shuffle(entries)
        train_entries.extend(entries[:train_per_class])
        test_pool_entries.extend(entries[train_per_class : train_per_class + test_per_class])

    rng.shuffle(train_entries)
    rng.shuffle(test_pool_entries)

    logger.info(
        f"Split: {len(train_entries):,} train, {len(test_pool_entries):,} test "
        f"({train_per_class:,} + {test_per_class:,} per class)"
    )
    return train_entries, test_pool_entries


# ===========================================================================
# Phase 3: Copy Images to Disk
# ===========================================================================

def copy_train_images(
    entries: List[Dict],
    dest_root: Path,
) -> List[Dict]:
    """Copy training images into videos/train/{class_name}/ structure.

    Returns entries augmented with 'dest_path' and 'sha256'.
    """
    copied = 0
    for entry in entries:
        class_dir = dest_root / "train" / entry["label_name"]
        class_dir.mkdir(parents=True, exist_ok=True)

        src = Path(entry["image_path"])
        # Prefix with 'an_' (AffectNet) to avoid collision with existing synthetic videos
        dest = class_dir / f"an_{entry['stem']}.jpg"
        entry["dest_path"] = str(dest)

        if not dest.exists():
            shutil.copy2(src, dest)
            copied += 1

        # Compute SHA-256
        entry["sha256"] = _sha256(dest)
        entry["size_bytes"] = dest.stat().st_size

    logger.info(f"Training images: {copied:,} copied, {len(entries) - copied:,} already existed.")
    return entries


def copy_test_images(
    entries: List[Dict],
    dest_root: Path,
    run_id: str,
) -> List[Dict]:
    """Copy test images into videos/test/{class_name}/ for EmotionDataset.

    Also writes the label map to manifests/{run_id}_test_labels.jsonl.
    """
    copied = 0
    for entry in entries:
        class_dir = dest_root / "test" / entry["label_name"]
        class_dir.mkdir(parents=True, exist_ok=True)

        src = Path(entry["image_path"])
        dest = class_dir / f"an_{entry['stem']}.jpg"
        entry["dest_path"] = str(dest)

        if not dest.exists():
            shutil.copy2(src, dest)
            copied += 1

        entry["sha256"] = _sha256(dest)
        entry["size_bytes"] = dest.stat().st_size

    logger.info(f"Test images: {copied:,} copied for {run_id}.")
    return entries


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ===========================================================================
# Phase 4: Write Manifests
# ===========================================================================

def write_train_manifest(
    entries: List[Dict],
    dest_root: Path,
    run_id: str,
) -> Path:
    """Write a JSONL manifest for the training set."""
    manifest_dir = dest_root / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{run_id}_train.jsonl"

    with open(manifest_path, "w") as fh:
        for e in entries:
            record = {
                "path": e["dest_path"],
                "label": e["label_name"],
                "source": f"affectnet_train_{e['stem']}",
                "sha256": e["sha256"],
                "affectnet_label_code": e["label_code"],
            }
            fh.write(json.dumps(record) + "\n")

    logger.info(f"Train manifest: {manifest_path} ({len(entries):,} entries)")
    return manifest_path


def write_test_label_map(
    entries: List[Dict],
    dest_root: Path,
    run_id: str,
) -> Path:
    """Write a JSONL label map for the test set (ground truth kept separate)."""
    manifest_dir = dest_root / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    label_map_path = manifest_dir / f"{run_id}_test_labels.jsonl"

    with open(label_map_path, "w") as fh:
        for e in entries:
            annot = e["annotation"]
            meta = annot.get("meta-data", {})
            record = {
                "filename": Path(e["dest_path"]).name,
                "label": e["label_name"],
                "affectnet_label_code": e["label_code"],
                "soft_label": annot.get("soft-label", []),
                "subset": annot.get("subset"),
                "valence": meta.get("valence"),
                "arousal": meta.get("arousal"),
                "age": meta.get("age"),
                "gender": meta.get("gender"),
                "source_image": f"{e['stem']}.jpg",
                "sha256": e["sha256"],
            }
            fh.write(json.dumps(record) + "\n")

    logger.info(f"Test label map: {label_map_path} ({len(entries):,} entries)")
    return label_map_path


# ===========================================================================
# Phase 5: Database Records
# ===========================================================================

def insert_video_records(
    entries: List[Dict],
    split: str,
    batch_label: str,
) -> int:
    """Insert video records into the Postgres video table.

    For split='train', label is set from the entry.
    For split='test', label is NULL (per DB constraint).

    Uses ON CONFLICT DO NOTHING to handle re-runs safely.
    """
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False
    cur = conn.cursor()

    inserted = 0
    skipped = 0
    now = datetime.now(timezone.utc)

    for entry in entries:
        video_id = str(uuid4())
        file_path = entry["dest_path"]
        sha256 = entry["sha256"]
        size_bytes = entry["size_bytes"]
        label = entry["label_name"] if split == "train" else None

        try:
            cur.execute(
                """
                INSERT INTO video (video_id, file_path, split, label, size_bytes, sha256,
                                   metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT ON CONSTRAINT uq_video_sha DO NOTHING
                """,
                (
                    video_id,
                    file_path,
                    split,
                    label,
                    size_bytes,
                    sha256,
                    json.dumps({
                        "source": "affectnet",
                        "affectnet_stem": entry["stem"],
                        "affectnet_label_code": entry["label_code"],
                        "batch": batch_label,
                    }),
                    now,
                    now,
                ),
            )
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception:
            conn.rollback()
            raise

        # Commit in batches of 5000
        if (inserted + skipped) % 5000 == 0:
            conn.commit()
            logger.info(f"  DB {batch_label}: {inserted:,} inserted, {skipped:,} skipped...")

    conn.commit()
    cur.close()
    conn.close()

    logger.info(
        f"DB {batch_label}: {inserted:,} inserted, {skipped:,} skipped (duplicate sha256+size)."
    )
    return inserted


# ===========================================================================
# Phase 6: Validation Set Preparation
# ===========================================================================

def prepare_validation_set(
    dest_root: Path,
    run_id: str,
) -> Tuple[int, Path]:
    """Copy AffectNet validation images (labels 0,1,2) and create a label map.

    Validation images go to videos/test/validation/{class_name}/ as a reference
    set.  A label map manifest is also created.
    """
    logger.info("Preparing validation set from AffectNet validation data...")

    by_label = scan_annotations(VAL_ANNOTS, VAL_IMAGES)
    entries: List[Dict] = []
    for code in sorted(TARGET_LABELS):
        entries.extend(by_label[code])

    copied = 0
    for entry in entries:
        # Store in a separate validation directory to avoid mixing with test
        class_dir = dest_root / "test" / "validation" / entry["label_name"]
        class_dir.mkdir(parents=True, exist_ok=True)

        src = Path(entry["image_path"])
        dest = class_dir / f"an_val_{entry['stem']}.jpg"
        entry["dest_path"] = str(dest)

        if not dest.exists():
            shutil.copy2(src, dest)
            copied += 1

        entry["sha256"] = _sha256(dest)
        entry["size_bytes"] = dest.stat().st_size

    # Write validation label map manifest
    manifest_dir = dest_root / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    label_map_path = manifest_dir / f"{run_id}_validation_labels.jsonl"

    with open(label_map_path, "w") as fh:
        for e in entries:
            annot = e["annotation"]
            meta = annot.get("meta-data", {})
            record = {
                "filename": Path(e["dest_path"]).name,
                "label": e["label_name"],
                "affectnet_label_code": e["label_code"],
                "soft_label": annot.get("soft-label", []),
                "valence": meta.get("valence"),
                "arousal": meta.get("arousal"),
                "source_image": f"{e['stem']}.jpg",
                "sha256": e["sha256"],
            }
            fh.write(json.dumps(record) + "\n")

    logger.info(f"Validation: {copied:,} images copied, {len(entries):,} total. Manifest: {label_map_path}")
    return len(entries), label_map_path


# ===========================================================================
# Main
# ===========================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Create AffectNet datasets for Reachy")
    parser.add_argument("--run-id", default="run_0300", help="Run ID for this dataset creation")
    parser.add_argument("--train-per-class", type=int, default=20000, help="Training images per class")
    parser.add_argument("--test-per-class", type=int, default=500, help="Test images per class")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--skip-train", action="store_true", help="Skip training set creation")
    parser.add_argument("--skip-db", action="store_true", help="Skip database inserts")
    parser.add_argument("--skip-validation", action="store_true", help="Skip validation set")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
    )

    t0 = time.time()

    # ------------------------------------------------------------------
    # Step 1: Scan AffectNet training annotations
    # ------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("Step 1: Scanning AffectNet training annotations...")
    logger.info("=" * 60)
    by_label = scan_annotations(TRAIN_ANNOTS, TRAIN_IMAGES)

    # ------------------------------------------------------------------
    # Step 2: Balance and split
    # ------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("Step 2: Balancing classes and splitting train/test...")
    logger.info("=" * 60)
    train_entries, test_entries = balance_and_split(
        by_label,
        train_per_class=args.train_per_class,
        test_per_class=args.test_per_class,
        seed=args.seed,
    )

    # ------------------------------------------------------------------
    # Step 3: Copy training images
    # ------------------------------------------------------------------
    if not args.skip_train:
        logger.info("=" * 60)
        logger.info("Step 3: Copying training images...")
        logger.info("=" * 60)
        train_entries = copy_train_images(train_entries, VIDEOS_ROOT)
        write_train_manifest(train_entries, VIDEOS_ROOT, args.run_id)

        if not args.skip_db:
            logger.info("Inserting training records into DB...")
            insert_video_records(train_entries, "train", f"{args.run_id}_train")
    else:
        logger.info("Step 3: SKIPPED (--skip-train)")

    # ------------------------------------------------------------------
    # Step 4: Copy test images
    # ------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info(f"Step 4: Copying test images for {args.run_id}...")
    logger.info("=" * 60)
    test_entries = copy_test_images(test_entries, VIDEOS_ROOT, args.run_id)
    write_test_label_map(test_entries, VIDEOS_ROOT, args.run_id)

    if not args.skip_db:
        logger.info("Inserting test records into DB...")
        insert_video_records(test_entries, "test", f"{args.run_id}_test")

    # ------------------------------------------------------------------
    # Step 5: Validation set (AffectNet validation, labels 0/1/2)
    # ------------------------------------------------------------------
    if not args.skip_validation:
        logger.info("=" * 60)
        logger.info("Step 5: Preparing AffectNet validation set...")
        logger.info("=" * 60)
        val_count, val_manifest = prepare_validation_set(VIDEOS_ROOT, args.run_id)
    else:
        logger.info("Step 5: SKIPPED (--skip-validation)")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    elapsed = time.time() - t0
    logger.info("=" * 60)
    logger.info("DATASET CREATION COMPLETE")
    logger.info("=" * 60)
    if not args.skip_train:
        logger.info(f"  Training:   {len(train_entries):,} images in videos/train/{{happy,sad,neutral}}/")
    logger.info(f"  Test:       {len(test_entries):,} images in videos/test/{{happy,sad,neutral}}/")
    if not args.skip_validation:
        logger.info(f"  Validation: {val_count:,} images in videos/test/validation/{{happy,sad,neutral}}/")
    logger.info(f"  Run ID:     {args.run_id}")
    logger.info(f"  Elapsed:    {elapsed:.1f}s")
    logger.info("")
    logger.info("Next steps:")
    logger.info(f"  1. Run base model evaluation:")
    logger.info(f"     python -m trainer.run_efficientnet_pipeline \\")
    logger.info(f"       --skip-train --variant base --run-type test \\")
    logger.info(f"       --run-id {args.run_id} --no-contract-updates \\")
    logger.info(f"       --checkpoint /media/rusty_admin/project_data/reachy_emotion/checkpoints/efficientnet_b0_3cls/best_model.pth")
    logger.info(f"  2. After evaluation, archive test set:")
    logger.info(f"     mv videos/test/{{happy,sad,neutral}} videos/test/archive/{args.run_id}/")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
