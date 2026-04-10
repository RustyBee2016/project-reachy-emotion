#!/usr/bin/env python3
"""
One-time setup: create the AffectNet validation pool and fixed test dataset.

This script runs ONCE to:
  1. Scan AffectNet validation_set annotations for human-label 0/1/2
  2. Copy matching images into a class-structured pool:
       /videos/validation/affectnet_pool/{happy,sad,neutral}/
  3. Move 25% per class into the fixed test dataset:
       /videos/test/affectnet_test_dataset/{happy,sad,neutral}/

After this script runs:
  - The pool (75% per class) is the source for per-run validation sampling.
  - The test dataset (25% per class) is fixed and used for ALL model evaluations.
  - No image appears in both pool and test.

Usage:
    python -m trainer.setup_affectnet_pool
    python -m trainer.setup_affectnet_pool --test-fraction 0.25 --seed 42 --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import shutil
import sys
from pathlib import Path
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AffectNet paths (Ubuntu 1)
# ---------------------------------------------------------------------------
AFFECTNET_VAL_ROOT = Path(
    "/media/rusty_admin/project_data/reachy_emotion/affectnet/"
    "consolidated/AffectNet+/human_annotated/validation_set"
)
AFFECTNET_IMAGES = AFFECTNET_VAL_ROOT / "images"
AFFECTNET_ANNOTATIONS = AFFECTNET_VAL_ROOT / "annotations"

# Output paths
VIDEOS_ROOT = Path("/media/rusty_admin/project_data/reachy_emotion/videos")
POOL_DIR = VIDEOS_ROOT / "validation" / "affectnet_pool"
TEST_DIR = VIDEOS_ROOT / "test" / "affectnet_test_dataset"

# Label mapping
LABEL_MAP: Dict[int, str] = {0: "neutral", 1: "happy", 2: "sad"}
CLASS_NAMES = ["happy", "sad", "neutral"]


def scan_and_filter(
    annotations_dir: Path,
    images_dir: Path,
) -> Dict[str, List[Path]]:
    """Scan annotation JSONs, filter to 3-class, return image paths by class."""
    by_class: Dict[str, List[Path]] = {name: [] for name in CLASS_NAMES}

    annotation_files = sorted(annotations_dir.glob("*.json"))
    logger.info("Scanning %d annotation files...", len(annotation_files))

    for ann_path in annotation_files:
        with open(ann_path) as f:
            data = json.load(f)

        label_code = data.get("human-label")
        if label_code not in LABEL_MAP:
            continue

        class_name = LABEL_MAP[label_code]
        img_path = images_dir / f"{ann_path.stem}.jpg"
        if not img_path.exists():
            continue

        by_class[class_name].append(img_path)

    for name in CLASS_NAMES:
        logger.info("  %s: %d images", name, len(by_class[name]))

    return by_class


def copy_to_pool(
    by_class: Dict[str, List[Path]],
    pool_dir: Path,
) -> Dict[str, List[Path]]:
    """Copy filtered images into pool/{happy,sad,neutral}/. Returns pool paths."""
    pool_paths: Dict[str, List[Path]] = {name: [] for name in CLASS_NAMES}

    for class_name, src_paths in by_class.items():
        class_dir = pool_dir / class_name
        class_dir.mkdir(parents=True, exist_ok=True)

        copied = 0
        for src in src_paths:
            dest = class_dir / src.name
            if not dest.exists():
                shutil.copy2(src, dest)
                copied += 1
            pool_paths[class_name].append(dest)

        logger.info("  %s: %d copied (%d already existed)", class_name, copied, len(src_paths) - copied)

    return pool_paths


def move_test_split(
    pool_paths: Dict[str, List[Path]],
    test_dir: Path,
    test_fraction: float,
    seed: int,
) -> Dict[str, int]:
    """Move test_fraction of each class from pool to test dir. Returns counts."""
    rng = random.Random(seed)
    counts: Dict[str, int] = {}

    for class_name in CLASS_NAMES:
        paths = pool_paths[class_name]
        n_test = int(len(paths) * test_fraction)

        # Shuffle and pick test split
        shuffled = paths[:]
        rng.shuffle(shuffled)
        test_paths = shuffled[:n_test]

        class_test_dir = test_dir / class_name
        class_test_dir.mkdir(parents=True, exist_ok=True)

        moved = 0
        for src in test_paths:
            dest = class_test_dir / src.name
            if not dest.exists():
                shutil.move(str(src), str(dest))
                moved += 1
            elif src.exists():
                # dest already in test dir, remove from pool
                src.unlink()
                moved += 1

        counts[class_name] = moved
        remaining = len(paths) - n_test
        logger.info("  %s: %d moved to test, %d remain in pool", class_name, moved, remaining)

    return counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="One-time setup: create AffectNet validation pool + fixed test dataset"
    )
    parser.add_argument(
        "--test-fraction",
        type=float,
        default=0.25,
        help="Fraction of each class to move to test dataset (default: 0.25)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for test split selection (default: 42)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and report counts without copying or moving files",
    )
    args = parser.parse_args()

    # ── Validate paths ────────────────────────────────────────────────────
    if not AFFECTNET_ANNOTATIONS.exists():
        logger.error("AffectNet annotations not found: %s", AFFECTNET_ANNOTATIONS)
        return 1
    if not AFFECTNET_IMAGES.exists():
        logger.error("AffectNet images not found: %s", AFFECTNET_IMAGES)
        return 1

    # ── Guard: refuse to overwrite existing test dataset ──────────────────
    test_has_images = TEST_DIR.exists() and any(TEST_DIR.rglob("*.jpg"))
    if test_has_images:
        logger.error(
            "Test dataset already contains images at %s. "
            "This script should only run once. "
            "Delete the test dataset manually if you intend to recreate it.",
            TEST_DIR,
        )
        return 1

    # ── Step 1: Scan & filter ─────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("Step 1: Scanning AffectNet validation_set annotations")
    logger.info("=" * 60)
    by_class = scan_and_filter(AFFECTNET_ANNOTATIONS, AFFECTNET_IMAGES)

    total = sum(len(v) for v in by_class.values())
    if total == 0:
        logger.error("No images matched filter criteria.")
        return 1

    n_test_total = sum(int(len(v) * args.test_fraction) for v in by_class.values())
    n_pool_total = total - n_test_total
    logger.info("Total filtered: %d  →  test: %d (%.0f%%)  pool: %d (%.0f%%)",
                total, n_test_total, args.test_fraction * 100,
                n_pool_total, (1 - args.test_fraction) * 100)

    if args.dry_run:
        logger.info("DRY RUN — no files copied or moved.")
        return 0

    # ── Step 2: Copy to pool ──────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("Step 2: Copying filtered images to pool")
    logger.info("  %s", POOL_DIR)
    logger.info("=" * 60)
    pool_paths = copy_to_pool(by_class, POOL_DIR)

    # ── Step 3: Move test split ───────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("Step 3: Moving 25%% per class to test dataset")
    logger.info("  %s", TEST_DIR)
    logger.info("=" * 60)
    test_counts = move_test_split(pool_paths, TEST_DIR, args.test_fraction, args.seed)

    # ── Summary ───────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("SETUP COMPLETE")
    logger.info("=" * 60)
    for name in CLASS_NAMES:
        pool_remaining = len(list((POOL_DIR / name).glob("*.jpg")))
        test_count = len(list((TEST_DIR / name).glob("*.jpg")))
        logger.info("  %s:  pool=%d  test=%d", name, pool_remaining, test_count)

    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Create a per-run validation dataset:")
    logger.info("     python -m trainer.ingest_affectnet validation-run --run-id run_0103")
    logger.info("  2. Train Variant 1:")
    logger.info("     python -m trainer.train_variant1 --run-id run_0103")

    return 0


if __name__ == "__main__":
    sys.exit(main())
