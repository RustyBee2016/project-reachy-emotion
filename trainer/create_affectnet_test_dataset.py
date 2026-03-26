"""
Create an unlabeled test dataset from the AffectNet+ dataset.

This script:
1. Reads AffectNet+ annotation JSONs and filters for happy/sad images
2. Applies quality filters (complexity, soft-label confidence, balance)
3. Wraps each selected image into a short synthetic MP4 video
4. Outputs an unlabeled test directory (no labels in filenames or structure)
5. Generates a separate JSONL label map for post-evaluation scoring

Usage:
    python -m trainer.create_affectnet_test_dataset \
        --affectnet-root /path/to/AffectNetPlus \
        --output-root /media/project_data/reachy_emotion/videos \
        --samples-per-class 250 \
        --min-confidence 0.6 \
        --max-complexity 1 \
        --seed 42

Directory layout produced:
    <output-root>/
    ├── test/
    │   └── affectnet_test_dataset/
    │       ├── affectnet_00001.mp4      # unlabeled synthetic video
    │       ├── affectnet_00002.mp4
    │       └── ...
    └── manifests/
        └── affectnet_test_labels.jsonl  # ground-truth label map (separate)
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AffectNet+ emotion code mapping (from AffectNet+ documentation)
# ---------------------------------------------------------------------------
AFFECTNET_EMOTION_CODES: Dict[int, str] = {
    0: "neutral",
    1: "happy",
    2: "sad",
    3: "surprise",
    4: "fear",
    5: "disgust",
    6: "anger",
    7: "contempt",
    8: "none",
    9: "uncertain",
    10: "non-face",
}

# Project-relevant classes (binary: happy vs sad)
TARGET_CLASSES: Dict[int, str] = {
    1: "happy",
    2: "sad",
}

# AffectNet+ complexity levels
COMPLEXITY_LABELS: Dict[int, str] = {
    0: "easy",
    1: "challenging",
    2: "difficult",
}

# Synthetic video parameters
VIDEO_FPS = 25
VIDEO_FRAMES = 20  # ~0.8 seconds
VIDEO_FOURCC = "mp4v"


# ---------------------------------------------------------------------------
# Annotation loading
# ---------------------------------------------------------------------------

def load_affectnet_annotations(
    affectnet_root: Path,
) -> List[Dict[str, Any]]:
    """Load all AffectNet+ annotation JSONs from the dataset.

    AffectNet+ stores one JSON per image. The JSON contains:
    - Human-Label: int (0-10)
    - Soft-Label: list of 8 floats
    - Subset: int (0=easy, 1=challenging, 2=difficult)
    - Metadata: dict with age, gender, race, pose, landmarks, valence, arousal

    Args:
        affectnet_root: Root directory of extracted AffectNet+ dataset.

    Returns:
        List of annotation dicts, each augmented with ``image_path``.
    """
    annotations: List[Dict[str, Any]] = []

    # AffectNet+ stores annotations as individual JSON files alongside images,
    # or in a combined annotations directory. Support both layouts.
    json_paths: List[Path] = []

    # Layout 1: annotations/ directory with JSON files
    annotations_dir = affectnet_root / "annotations"
    if annotations_dir.is_dir():
        json_paths.extend(sorted(annotations_dir.glob("**/*.json")))

    # Layout 2: JSON files alongside images in train/validation dirs
    for subdir_name in ("train", "validation", "Train", "Validation"):
        subdir = affectnet_root / subdir_name
        if subdir.is_dir():
            json_paths.extend(sorted(subdir.glob("**/*.json")))

    # Layout 3: flat structure with images and JSONs in root
    if not json_paths:
        json_paths.extend(sorted(affectnet_root.glob("*.json")))

    logger.info(f"Found {len(json_paths)} annotation JSON files")

    for json_path in json_paths:
        try:
            with open(json_path, "r") as f:
                ann = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(f"Skipping invalid JSON {json_path}: {exc}")
            continue

        # Resolve the matching image path (same stem, image extension)
        image_path = _resolve_image_path(json_path, affectnet_root)
        if image_path is None:
            continue

        ann["_json_path"] = str(json_path)
        ann["_image_path"] = str(image_path)
        annotations.append(ann)

    logger.info(f"Loaded {len(annotations)} valid annotations with images")
    return annotations


def _resolve_image_path(json_path: Path, root: Path) -> Optional[Path]:
    """Find the image file corresponding to a JSON annotation.

    Checks common image extensions in the same directory as the JSON and
    also in parallel image directories (e.g., images/ vs annotations/).
    """
    stem = json_path.stem
    image_exts = (".jpg", ".jpeg", ".png", ".bmp")

    # Check same directory
    for ext in image_exts:
        candidate = json_path.with_suffix(ext)
        if candidate.exists():
            return candidate

    # Check parallel images/ directory
    for images_dir_name in ("images", "Images"):
        images_dir = root / images_dir_name
        if images_dir.is_dir():
            for ext in image_exts:
                candidate = images_dir / f"{stem}{ext}"
                if candidate.exists():
                    return candidate
            # Try preserving subdirectory structure
            relative = json_path.relative_to(json_path.parent)
            parent_relative = json_path.parent.relative_to(root)
            for ext in image_exts:
                candidate = images_dir / parent_relative.name / f"{stem}{ext}"
                if candidate.exists():
                    return candidate

    # Check train/validation image directories
    for subdir_name in ("train", "validation", "Train", "Validation"):
        subdir = root / subdir_name
        if subdir.is_dir():
            for ext in image_exts:
                candidate = subdir / f"{stem}{ext}"
                if candidate.exists():
                    return candidate

    return None


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def filter_annotations(
    annotations: List[Dict[str, Any]],
    target_codes: Dict[int, str],
    max_complexity: int = 1,
    min_confidence: float = 0.6,
) -> Dict[str, List[Dict[str, Any]]]:
    """Filter annotations for target emotion classes with quality thresholds.

    Args:
        annotations: Raw annotation list from ``load_affectnet_annotations``.
        target_codes: Mapping of AffectNet emotion codes to class names.
        max_complexity: Maximum complexity subset to include (0=easy, 1=challenging).
        min_confidence: Minimum dominant soft-label probability required.

    Returns:
        Dict mapping class names to lists of qualifying annotations.
    """
    filtered: Dict[str, List[Dict[str, Any]]] = {name: [] for name in target_codes.values()}

    for ann in annotations:
        # Extract human label
        human_label = ann.get("Human-Label", ann.get("human_label", ann.get("label")))
        if human_label is None:
            continue
        human_label = int(human_label)

        if human_label not in target_codes:
            continue

        class_name = target_codes[human_label]

        # Complexity filter
        subset = ann.get("Subset", ann.get("subset"))
        if subset is not None and int(subset) > max_complexity:
            continue

        # Soft-label confidence filter
        soft_label = ann.get("Soft-Label", ann.get("soft_label", ann.get("soft-label")))
        if soft_label is not None:
            soft_label = [float(x) for x in soft_label]
            # The target class index in the 8-dim soft-label vector corresponds
            # to the AffectNet emotion code (0=neutral, 1=happy, 2=sad, ...)
            target_prob = soft_label[human_label] if human_label < len(soft_label) else 0.0
            if target_prob < min_confidence:
                continue

        filtered[class_name].append(ann)

    for name, items in filtered.items():
        logger.info(f"  {name}: {len(items)} samples after filtering")

    return filtered


def sample_balanced(
    filtered: Dict[str, List[Dict[str, Any]]],
    samples_per_class: int,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Sample a balanced subset from each class.

    Args:
        filtered: Dict mapping class names to annotation lists.
        samples_per_class: Number of samples to draw per class.
        seed: Random seed for reproducibility.

    Returns:
        Combined list of sampled annotations (with ``_assigned_class`` key).
    """
    rng = random.Random(seed)
    sampled: List[Dict[str, Any]] = []

    for class_name, items in filtered.items():
        available = len(items)
        n = min(samples_per_class, available)
        if n < samples_per_class:
            logger.warning(
                f"Class '{class_name}' has only {available} samples "
                f"(requested {samples_per_class}). Using all {available}."
            )
        chosen = rng.sample(items, n)
        for ann in chosen:
            ann["_assigned_class"] = class_name
        sampled.extend(chosen)

    rng.shuffle(sampled)
    logger.info(f"Sampled {len(sampled)} total test images (balanced)")
    return sampled


# ---------------------------------------------------------------------------
# Synthetic video creation
# ---------------------------------------------------------------------------

def image_to_video(
    image_path: Path,
    output_path: Path,
    fps: int = VIDEO_FPS,
    num_frames: int = VIDEO_FRAMES,
) -> bool:
    """Convert a static image to a short synthetic MP4 video.

    The image is resized to 224x224 (AffectNet+ native) and repeated for
    ``num_frames`` frames to produce a valid MP4 that the Reachy pipeline
    can process through its normal video-based inference path.

    Args:
        image_path: Source image file.
        output_path: Destination MP4 path.
        fps: Video frame rate.
        num_frames: Number of repeated frames.

    Returns:
        True on success, False on failure.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        logger.warning(f"Cannot read image: {image_path}")
        return False

    # Resize to 224x224 (model input size, AffectNet+ native)
    img = cv2.resize(img, (224, 224), interpolation=cv2.INTER_AREA)

    fourcc = cv2.VideoWriter_fourcc(*VIDEO_FOURCC)
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (224, 224))

    if not writer.isOpened():
        logger.warning(f"Cannot create video writer for: {output_path}")
        return False

    for _ in range(num_frames):
        writer.write(img)

    writer.release()
    return True


# ---------------------------------------------------------------------------
# Dataset assembly
# ---------------------------------------------------------------------------

def create_test_dataset(
    affectnet_root: Path,
    output_root: Path,
    samples_per_class: int = 250,
    min_confidence: float = 0.6,
    max_complexity: int = 1,
    seed: int = 42,
) -> Dict[str, Any]:
    """Create the full unlabeled test dataset and label map.

    Args:
        affectnet_root: Root of extracted AffectNet+ data.
        output_root: Video storage root (e.g., /media/project_data/reachy_emotion/videos).
        samples_per_class: Target samples per emotion class.
        min_confidence: Minimum soft-label confidence for target emotion.
        max_complexity: Maximum complexity subset to include.
        seed: Random seed for reproducibility.

    Returns:
        Summary dict with counts, paths, and any warnings.
    """
    # Output directories
    test_dir = output_root / "test" / "affectnet_test_dataset"
    manifests_dir = output_root / "manifests"
    test_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    label_map_path = manifests_dir / "affectnet_test_labels.jsonl"

    # Step 1: Load annotations
    logger.info("Loading AffectNet+ annotations...")
    annotations = load_affectnet_annotations(affectnet_root)
    if not annotations:
        logger.error("No annotations found. Check --affectnet-root path and dataset structure.")
        return {"error": "No annotations found", "success": False}

    # Step 2: Filter
    logger.info("Filtering for target classes (happy, sad)...")
    filtered = filter_annotations(
        annotations,
        target_codes=TARGET_CLASSES,
        max_complexity=max_complexity,
        min_confidence=min_confidence,
    )

    # Step 3: Balanced sampling
    logger.info("Sampling balanced test set...")
    sampled = sample_balanced(filtered, samples_per_class=samples_per_class, seed=seed)

    # Step 4: Generate videos + label map
    logger.info("Creating synthetic videos and label map...")
    created = 0
    skipped = 0
    label_entries: List[Dict[str, Any]] = []

    with open(label_map_path, "w") as label_file:
        for idx, ann in enumerate(sampled, start=1):
            video_name = f"affectnet_{idx:05d}.mp4"
            video_path = test_dir / video_name
            image_path = Path(ann["_image_path"])

            if not image_to_video(image_path, video_path):
                skipped += 1
                continue

            created += 1

            # Build label map entry (ground truth kept SEPARATE from test data)
            soft_label = ann.get("Soft-Label", ann.get("soft_label", ann.get("soft-label")))
            metadata = ann.get("Metadata", ann.get("metadata", {}))
            human_label_code = int(
                ann.get("Human-Label", ann.get("human_label", ann.get("label", -1)))
            )
            subset_code = ann.get("Subset", ann.get("subset"))

            entry = {
                "video_filename": video_name,
                "label": ann["_assigned_class"],
                "affectnet_emotion_code": human_label_code,
                "soft_label": soft_label,
                "complexity": COMPLEXITY_LABELS.get(int(subset_code), "unknown")
                if subset_code is not None
                else None,
                "source_image": image_path.name,
                "valence": metadata.get("Valence", metadata.get("valence")),
                "arousal": metadata.get("Arousal", metadata.get("arousal")),
                "age": metadata.get("Age", metadata.get("age")),
                "gender": metadata.get("Gender", metadata.get("gender")),
            }
            label_file.write(json.dumps(entry) + "\n")
            label_entries.append(entry)

    # Summary
    class_counts = {}
    for entry in label_entries:
        lbl = entry["label"]
        class_counts[lbl] = class_counts.get(lbl, 0) + 1

    summary = {
        "success": True,
        "test_dir": str(test_dir),
        "label_map_path": str(label_map_path),
        "total_created": created,
        "total_skipped": skipped,
        "class_counts": class_counts,
        "samples_per_class_requested": samples_per_class,
        "min_confidence": min_confidence,
        "max_complexity": max_complexity,
        "seed": seed,
    }

    logger.info("=" * 60)
    logger.info("Test dataset creation complete!")
    logger.info(f"  Videos created: {created}")
    logger.info(f"  Videos skipped: {skipped}")
    logger.info(f"  Class distribution: {class_counts}")
    logger.info(f"  Test directory: {test_dir}")
    logger.info(f"  Label map: {label_map_path}")
    logger.info("=" * 60)
    logger.info(
        "IMPORTANT: The label map is for post-evaluation scoring ONLY. "
        "Do NOT place it in the test directory."
    )

    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create unlabeled test dataset from AffectNet+ for Reachy emotion pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--affectnet-root",
        type=Path,
        required=True,
        help="Root directory of extracted AffectNet+ dataset.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="Video storage root (e.g., /media/project_data/reachy_emotion/videos).",
    )
    parser.add_argument(
        "--samples-per-class",
        type=int,
        default=250,
        help="Number of samples per class (default: 250).",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.6,
        help="Minimum soft-label confidence for target emotion (default: 0.6).",
    )
    parser.add_argument(
        "--max-complexity",
        type=int,
        choices=[0, 1, 2],
        default=1,
        help="Max complexity subset: 0=easy, 1=challenging, 2=difficult (default: 1).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    summary = create_test_dataset(
        affectnet_root=args.affectnet_root,
        output_root=args.output_root,
        samples_per_class=args.samples_per_class,
        min_confidence=args.min_confidence,
        max_complexity=args.max_complexity,
        seed=args.seed,
    )

    if not summary.get("success"):
        logger.error(f"Failed: {summary.get('error', 'unknown error')}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
