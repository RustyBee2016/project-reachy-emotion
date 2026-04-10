#!/usr/bin/env python3
"""
AffectNet batch ingestion utility for emotion classification.

This module handles filtering, sampling, and ingesting AffectNet images into
the Reachy emotion classification system. It supports:
- 3-class filtering (neutral=0, happy=1, sad=2)
- Quality filtering (subset, soft-label confidence)
- Balanced sampling across emotion classes
- Batch database registration
- Metadata preservation (valence, arousal, age, gender, pose, landmarks)

Usage:
    # Ingest training images
    python -m trainer.ingest_affectnet train \
        --samples-per-class 10000 \
        --min-confidence 0.6 \
        --max-subset 1

    # Create run-scoped validation dataset
    python -m trainer.ingest_affectnet validation-run \
        --run-id run_0001 \
        --samples-per-class 500

    # Create test dataset for a specific run
    python -m trainer.ingest_affectnet test \
        --run-id run_0001 \
        --samples-per-class 250 \
        --source no_human

Architecture:
    AffectNet+ Directory Structure:
    /affectnet/consolidated/AffectNet+/
    ├── human_annotated/
    │   ├── train_set/
    │   │   ├── images/          # 414,799 JPG files
    │   │   └── annotations/     # 414,799 JSON files
    │   └── validation_set/
    │       ├── images/          # 5,500 JPG files
    │       └── annotations/     # 5,500 JSON files
    └── no_human_annotated/
        ├── images/              # 539,607 JPG files
        └── annotations/         # 539,607 JSON files

Output Structure:
    /videos/
    ├── train/
    │   ├── happy/affectnet_*.jpg
    │   ├── sad/affectnet_*.jpg
    │   └── neutral/affectnet_*.jpg
    ├── validation/run/<run_id>/affectnet_*.jpg  # unlabeled filenames
    └── test/run/<run_id>/affectnet_*.jpg  # unlabeled filenames

Database Integration:
    - Inserts records into Video table (duration/fps=NULL for images)
    - Stores AffectNet metadata in extra_data JSONB column
    - Respects split='test' → label=NULL constraint
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import random
import shutil
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Emotion label mapping (AffectNet → Reachy 3-class)
AFFECTNET_TO_REACHY = {
    0: "neutral",
    1: "happy",
    2: "sad",
}

REACHY_EMOTIONS = {"neutral", "happy", "sad"}


@dataclass
class AffectNetAnnotation:
    """Parsed AffectNet annotation with metadata."""
    image_id: str  # Filename without extension (e.g., "47983")
    human_label: int  # 0-7 emotion code
    soft_label: List[float]  # 8-class probability distribution
    subset: int  # 0=easy, 1=challenging, 2=difficult
    age: Optional[int] = None
    valence: Optional[float] = None
    arousal: Optional[float] = None
    gender: Optional[Dict[str, float]] = None
    race: Optional[Dict[str, float]] = None
    pose: Optional[Dict[str, float]] = None
    landmark_68: Optional[List[int]] = None
    landmark_29: Optional[List[int]] = None

    @property
    def reachy_label(self) -> Optional[str]:
        """Map AffectNet label to Reachy 3-class label."""
        return AFFECTNET_TO_REACHY.get(self.human_label)

    @property
    def confidence(self) -> float:
        """Confidence score for the human-labeled emotion."""
        if 0 <= self.human_label < len(self.soft_label):
            return float(self.soft_label[self.human_label])
        return 0.0

    def to_metadata_dict(self) -> Dict[str, Any]:
        """Convert to metadata dict for Video.extra_data storage."""
        return {
            "source": "affectnet",
            "affectnet_id": self.image_id,
            "human_label": self.human_label,
            "soft_label": self.soft_label,
            "subset": self.subset,
            "confidence": self.confidence,
            "age": self.age,
            "valence": self.valence,
            "arousal": self.arousal,
            "gender": self.gender,
            "race": self.race,
            "pose": self.pose,
        }


class AffectNetIngester:
    """Batch ingest AffectNet images with filtering and balanced sampling."""

    def __init__(
        self,
        *,
        affectnet_root: Path,
        videos_root: Path,
        manifests_root: Path,
    ):
        """
        Initialize AffectNet ingester.

        Args:
            affectnet_root: Root directory of AffectNet+ dataset
            videos_root: Root directory for video/image storage
            manifests_root: Root directory for manifest files
        """
        self.affectnet_root = Path(affectnet_root)
        self.videos_root = Path(videos_root)
        self.manifests_root = Path(manifests_root)

        # Validate paths
        if not self.affectnet_root.exists():
            raise ValueError(f"AffectNet root not found: {affectnet_root}")

        self.videos_root.mkdir(parents=True, exist_ok=True)
        self.manifests_root.mkdir(parents=True, exist_ok=True)

    def _load_annotation(self, annotation_path: Path) -> Optional[AffectNetAnnotation]:
        """Load and parse a single AffectNet annotation JSON file."""
        try:
            with open(annotation_path, 'r') as f:
                data = json.load(f)

            metadata = data.get("meta-data", {})
            return AffectNetAnnotation(
                image_id=annotation_path.stem,
                human_label=int(data.get("human-label", -1)),
                soft_label=data.get("soft-label", []),
                subset=int(data.get("subset", 2)),
                age=metadata.get("age"),
                valence=metadata.get("valence"),
                arousal=metadata.get("arousal"),
                gender=metadata.get("gender"),
                race=metadata.get("race"),
                pose=metadata.get("pose"),
                landmark_68=metadata.get("landmark-68"),
                landmark_29=metadata.get("landmark-29"),
            )
        except Exception as e:
            logger.warning(f"Failed to parse annotation {annotation_path}: {e}")
            return None

    def _filter_annotations(
        self,
        annotations_dir: Path,
        *,
        min_confidence: float = 0.6,
        max_subset: int = 1,
    ) -> Dict[str, List[AffectNetAnnotation]]:
        """
        Filter annotations by 3-class labels, confidence, and subset.

        Args:
            annotations_dir: Directory containing annotation JSON files
            min_confidence: Minimum soft-label confidence for target emotion
            max_subset: Maximum subset difficulty (0=easy, 1=challenging, 2=difficult)

        Returns:
            Dictionary mapping emotion labels to lists of annotations
        """
        filtered: Dict[str, List[AffectNetAnnotation]] = {
            "neutral": [],
            "happy": [],
            "sad": [],
        }

        annotation_files = sorted(annotations_dir.glob("*.json"))
        logger.info(f"Scanning {len(annotation_files)} annotation files...")

        for i, ann_path in enumerate(annotation_files):
            if (i + 1) % 10000 == 0:
                logger.info(f"Processed {i + 1}/{len(annotation_files)} annotations...")

            ann = self._load_annotation(ann_path)
            if ann is None:
                continue

            # Filter by 3-class labels
            if ann.reachy_label is None:
                continue

            # Filter by subset difficulty
            if ann.subset > max_subset:
                continue

            # Filter by confidence
            if ann.confidence < min_confidence:
                continue

            filtered[ann.reachy_label].append(ann)

        logger.info("Filtering complete:")
        for label, anns in filtered.items():
            logger.info(f"  {label}: {len(anns)} samples")

        return filtered

    def _balanced_sample(
        self,
        filtered: Dict[str, List[AffectNetAnnotation]],
        *,
        samples_per_class: int,
        seed: int = 42,
    ) -> Dict[str, List[AffectNetAnnotation]]:
        """
        Sample balanced counts from filtered annotations.

        Args:
            filtered: Filtered annotations by emotion label
            samples_per_class: Target number of samples per class
            seed: Random seed for reproducibility

        Returns:
            Sampled annotations (up to samples_per_class per emotion)
        """
        rng = random.Random(seed)
        sampled: Dict[str, List[AffectNetAnnotation]] = {}

        for label, anns in filtered.items():
            if len(anns) < samples_per_class:
                logger.warning(
                    f"Only {len(anns)} samples available for {label} "
                    f"(requested {samples_per_class})"
                )
                sampled[label] = anns
            else:
                sampled[label] = rng.sample(anns, samples_per_class)

        logger.info("Balanced sampling complete:")
        for label, anns in sampled.items():
            logger.info(f"  {label}: {len(anns)} samples")

        return sampled

    def _copy_images_to_train(
        self,
        sampled: Dict[str, List[AffectNetAnnotation]],
        images_dir: Path,
    ) -> List[Dict[str, Any]]:
        """
        Copy sampled images to train/<label>/ directories.

        Args:
            sampled: Sampled annotations by emotion label
            images_dir: Source directory containing AffectNet images

        Returns:
            List of ingestion records for manifest
        """
        records: List[Dict[str, Any]] = []

        for label, anns in sampled.items():
            label_dir = self.videos_root / "train" / label
            label_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Copying {len(anns)} images to train/{label}/...")

            for ann in anns:
                src_path = images_dir / f"{ann.image_id}.jpg"
                if not src_path.exists():
                    logger.warning(f"Image not found: {src_path}")
                    continue

                dst_name = f"affectnet_{ann.image_id}.jpg"
                dst_path = label_dir / dst_name
                rel_path = f"train/{label}/{dst_name}"

                # Copy image (not move - source files remain in AffectNet directory)
                shutil.copy2(src_path, dst_path)

                # Read image for metadata
                img = cv2.imread(str(dst_path))
                if img is None:
                    logger.warning(f"Failed to read copied image: {dst_path}")
                    continue

                height, width = img.shape[:2]
                file_size = dst_path.stat().st_size

                # Compute SHA256
                sha256 = hashlib.sha256(dst_path.read_bytes()).hexdigest()

                records.append({
                    "file_path": rel_path,
                    "label": label,
                    "sha256": sha256,
                    "size_bytes": file_size,
                    "width": width,
                    "height": height,
                    "metadata": ann.to_metadata_dict(),
                })

        logger.info(f"Copied {len(records)} images total")
        return records

    def _copy_images_to_test(
        self,
        sampled: Dict[str, List[AffectNetAnnotation]],
        images_dir: Path,
        run_id: str,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Copy sampled images to test/run/<run_id>/ with unlabeled filenames.

        Args:
            sampled: Sampled annotations by emotion label
            images_dir: Source directory containing AffectNet images
            run_id: Run identifier for test dataset

        Returns:
            Tuple of (db_records, ground_truth_records)
        """
        test_dir = self.videos_root / "test" / run_id
        test_dir.mkdir(parents=True, exist_ok=True)

        db_records: List[Dict[str, Any]] = []
        ground_truth: List[Dict[str, Any]] = []

        # Flatten all samples and shuffle for unlabeled ordering
        all_samples: List[Tuple[str, AffectNetAnnotation]] = []
        for label, anns in sampled.items():
            for ann in anns:
                all_samples.append((label, ann))

        rng = random.Random(42)  # Fixed seed for consistent ordering
        rng.shuffle(all_samples)

        logger.info(f"Copying {len(all_samples)} images to test/affectnet_test_dataset/run{run_id}/...")

        for idx, (label, ann) in enumerate(all_samples):
            src_path = images_dir / f"{ann.image_id}.jpg"
            if not src_path.exists():
                logger.warning(f"Image not found: {src_path}")
                continue

            # Unlabeled filename (no emotion prefix)
            dst_name = f"affectnet_{idx:05d}.jpg"
            dst_path = test_dir / dst_name
            rel_path = f"test/{run_id}/{dst_name}"

            # Copy image (not move - source files remain in AffectNet directory)
            shutil.copy2(src_path, dst_path)

            # Read image for metadata
            img = cv2.imread(str(dst_path))
            if img is None:
                logger.warning(f"Failed to read copied image: {dst_path}")
                continue

            height, width = img.shape[:2]
            file_size = dst_path.stat().st_size
            sha256 = hashlib.sha256(dst_path.read_bytes()).hexdigest()

            # DB record (split='test', label=NULL)
            db_records.append({
                "file_path": rel_path,
                "label": None,  # NULL for test split
                "sha256": sha256,
                "size_bytes": file_size,
                "width": width,
                "height": height,
                "metadata": ann.to_metadata_dict(),
            })

            # Ground truth record (separate manifest)
            ground_truth.append({
                "file_path": rel_path,
                "label": label,
                "affectnet_id": ann.image_id,
                "soft_label": ann.soft_label,
                "confidence": ann.confidence,
                "subset": ann.subset,
                "valence": ann.valence,
                "arousal": ann.arousal,
                "age": ann.age,
                "gender": ann.gender,
            })

        logger.info(f"Copied {len(db_records)} test images")
        return db_records, ground_truth

    def _write_manifest(
        self,
        records: List[Dict[str, Any]],
        manifest_path: Path,
    ):
        """Write ingestion records to JSONL manifest."""
        with open(manifest_path, 'w') as f:
            for record in records:
                f.write(json.dumps(record) + '\n')
        logger.info(f"Wrote manifest: {manifest_path} ({len(records)} records)")

    def ingest_training_set(
        self,
        *,
        samples_per_class: int = 10000,
        min_confidence: float = 0.6,
        max_subset: int = 1,
        seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Ingest AffectNet human-annotated training images.

        Args:
            samples_per_class: Target samples per emotion class
            min_confidence: Minimum soft-label confidence
            max_subset: Maximum subset difficulty (0=easy, 1=challenging, 2=difficult)
            seed: Random seed for sampling

        Returns:
            Summary statistics
        """
        logger.info("=== Ingesting AffectNet Training Set ===")
        logger.info(f"Samples per class: {samples_per_class}")
        logger.info(f"Min confidence: {min_confidence}")
        logger.info(f"Max subset: {max_subset}")

        annotations_dir = self.affectnet_root / "human_annotated" / "train_set" / "annotations"
        images_dir = self.affectnet_root / "human_annotated" / "train_set" / "images"

        if not annotations_dir.exists():
            raise ValueError(f"Annotations directory not found: {annotations_dir}")
        if not images_dir.exists():
            raise ValueError(f"Images directory not found: {images_dir}")

        # Filter annotations
        filtered = self._filter_annotations(
            annotations_dir,
            min_confidence=min_confidence,
            max_subset=max_subset,
        )

        # Balanced sampling
        sampled = self._balanced_sample(
            filtered,
            samples_per_class=samples_per_class,
            seed=seed,
        )

        # Copy images to train/<label>/
        records = self._copy_images_to_train(sampled, images_dir)

        # Write manifest
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        manifest_path = self.manifests_root / f"affectnet_train_ingestion_{timestamp}.jsonl"
        self._write_manifest(records, manifest_path)

        return {
            "split": "train",
            "total_samples": len(records),
            "samples_per_class": {label: len(anns) for label, anns in sampled.items()},
            "manifest_path": str(manifest_path),
            "timestamp": timestamp,
        }

    def ingest_validation_set(
        self,
        *,
        samples_per_class: int = 500,
        min_confidence: float = 0.6,
        max_subset: int = 1,
        seed: int = 42,
    ) -> Dict[str, Any]:
        """
        DEPRECATED: Legacy validation set ingestion that copies to train/<label>/.
        
        This method is deprecated and should not be used. It incorrectly copies
        validation images to the training directory instead of a run-scoped
        validation directory.
        
        Use create_validation_dataset() instead, which creates run-scoped
        validation datasets at /videos/validation/run/<run_id>/.

        Args:
            samples_per_class: Target samples per emotion class
            min_confidence: Minimum soft-label confidence
            max_subset: Maximum subset difficulty
            seed: Random seed for sampling

        Returns:
            Summary statistics
        """
        logger.warning(
            "DEPRECATED: ingest_validation_set() copies to train/<label>/ which is incorrect. "
            "Use create_validation_dataset() instead for run-scoped validation datasets."
        )
        logger.info("=== Ingesting AffectNet Validation Set (LEGACY) ===")
        logger.info(f"Samples per class: {samples_per_class}")

        annotations_dir = self.affectnet_root / "human_annotated" / "validation_set" / "annotations"
        images_dir = self.affectnet_root / "human_annotated" / "validation_set" / "images"

        if not annotations_dir.exists():
            raise ValueError(f"Annotations directory not found: {annotations_dir}")
        if not images_dir.exists():
            raise ValueError(f"Images directory not found: {images_dir}")

        filtered = self._filter_annotations(
            annotations_dir,
            min_confidence=min_confidence,
            max_subset=max_subset,
        )

        sampled = self._balanced_sample(
            filtered,
            samples_per_class=samples_per_class,
            seed=seed,
        )

        records = self._copy_images_to_train(sampled, images_dir)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        manifest_path = self.manifests_root / f"affectnet_validation_ingestion_{timestamp}.jsonl"
        self._write_manifest(records, manifest_path)

        return {
            "split": "validation",
            "total_samples": len(records),
            "samples_per_class": {label: len(anns) for label, anns in sampled.items()},
            "manifest_path": str(manifest_path),
            "timestamp": timestamp,
        }

    def _copy_images_from_pool(
        self,
        sampled_paths: Dict[str, List[Path]],
        run_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Copy sampled images from pool into validation/run/<run_id>/{class}/.

        Images are copied (not moved) so the pool remains intact for future runs.

        Args:
            sampled_paths: Image paths by class, sampled from the pool
            run_id: Run identifier for validation dataset

        Returns:
            List of records for the manifest
        """
        records: List[Dict[str, Any]] = []

        for class_name, paths in sampled_paths.items():
            class_dir = self.videos_root / "validation" / "run" / run_id / class_name
            class_dir.mkdir(parents=True, exist_ok=True)

            for src_path in paths:
                dst_path = class_dir / src_path.name
                if not dst_path.exists():
                    shutil.copy2(src_path, dst_path)

                file_size = dst_path.stat().st_size
                sha256 = hashlib.sha256(dst_path.read_bytes()).hexdigest()
                rel_path = f"validation/run/{run_id}/{class_name}/{src_path.name}"

                records.append({
                    "file_path": rel_path,
                    "label": class_name,
                    "sha256": sha256,
                    "size_bytes": file_size,
                    "source": "affectnet_pool",
                })

            logger.info(f"  {class_name}: {len(paths)} images copied")

        return records

    def create_validation_dataset(
        self,
        *,
        run_id: str,
        samples_per_class: int = 200,
        seed: Optional[int] = None,
        pool_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create run-scoped validation dataset by sampling from the pool.

        Copies a random sample of images from the pre-built pool
        (validation/affectnet_pool/{happy,sad,neutral}/) into a run-scoped
        directory (validation/run/<run_id>/{happy,sad,neutral}/).

        The pool must be created first by running setup_affectnet_pool.py.

        Args:
            run_id: Run identifier (e.g., 'run_0103')
            samples_per_class: Target samples per emotion class
            seed: Random seed (auto-generated from run_id if omitted)
            pool_dir: Override path to pool directory

        Returns:
            Summary statistics
        """
        logger.info(f"=== Creating Validation Dataset for {run_id} ===")
        logger.info(f"Samples per class: {samples_per_class}")

        # Auto-generate seed from run_id if not provided
        if seed is None:
            try:
                run_num = int(run_id.split('_')[1])
                seed = 142 + run_num
            except (IndexError, ValueError):
                seed = 142

        logger.info(f"Random seed: {seed}")

        # Resolve pool directory
        pool_root = Path(pool_dir) if pool_dir else self.videos_root / "validation" / "affectnet_pool"
        class_names = ["happy", "sad", "neutral"]

        # Collect available images from pool
        available: Dict[str, List[Path]] = {}
        for class_name in class_names:
            class_pool = pool_root / class_name
            if not class_pool.exists():
                raise ValueError(
                    f"Pool directory not found: {class_pool}. "
                    "Run 'python -m trainer.setup_affectnet_pool' first."
                )
            available[class_name] = sorted(class_pool.glob("*.jpg"))
            logger.info(f"  Pool {class_name}: {len(available[class_name])} images available")

        # Balanced random sample from pool
        rng = random.Random(seed)
        sampled_paths: Dict[str, List[Path]] = {}
        for class_name in class_names:
            pool_images = available[class_name]
            n = min(samples_per_class, len(pool_images))
            if n < samples_per_class:
                logger.warning(
                    f"Only {len(pool_images)} images available for {class_name} "
                    f"(requested {samples_per_class})"
                )
            sampled_paths[class_name] = rng.sample(pool_images, n)

        # Copy into run-scoped class subdirectories
        logger.info(f"Copying to validation/run/{run_id}/...")
        records = self._copy_images_from_pool(sampled_paths, run_id)

        # Write manifest for audit/reproducibility
        manifest_path = self.manifests_root / f"{run_id}_validation.jsonl"
        self._write_manifest(records, manifest_path)

        return {
            "run_id": run_id,
            "split": "validation",
            "source": "affectnet_pool",
            "total_samples": len(records),
            "samples_per_class": {name: len(sampled_paths[name]) for name in class_names},
            "manifest_path": str(manifest_path),
            "seed": seed,
        }

    def create_test_dataset(
        self,
        *,
        run_id: str,
        samples_per_class: int = 250,
        min_confidence: float = 0.5,
        max_subset: int = 2,
        source: str = "no_human",
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create run-scoped test dataset from AffectNet.

        Args:
            run_id: Run identifier (e.g., 'run_0001')
            samples_per_class: Target samples per emotion class
            min_confidence: Minimum soft-label confidence
            max_subset: Maximum subset difficulty
            source: 'no_human' or 'validation'
            seed: Random seed (defaults to 42 + run_number)

        Returns:
            Summary statistics
        """
        logger.info(f"=== Creating Test Dataset for {run_id} ===")
        logger.info(f"Source: {source}")
        logger.info(f"Samples per class: {samples_per_class}")

        # Auto-generate seed from run_id if not provided
        if seed is None:
            try:
                run_num = int(run_id.split('_')[1])
                seed = 42 + run_num
            except (IndexError, ValueError):
                seed = 42

        logger.info(f"Random seed: {seed}")

        if source == "no_human":
            annotations_dir = self.affectnet_root / "no_human_annotated" / "annotations"
            images_dir = self.affectnet_root / "no_human_annotated" / "images"
        elif source == "validation":
            annotations_dir = self.affectnet_root / "human_annotated" / "validation_set" / "annotations"
            images_dir = self.affectnet_root / "human_annotated" / "validation_set" / "images"
        else:
            raise ValueError(f"Invalid source: {source}. Must be 'no_human' or 'validation'")

        if not annotations_dir.exists():
            raise ValueError(f"Annotations directory not found: {annotations_dir}")
        if not images_dir.exists():
            raise ValueError(f"Images directory not found: {images_dir}")

        filtered = self._filter_annotations(
            annotations_dir,
            min_confidence=min_confidence,
            max_subset=max_subset,
        )

        sampled = self._balanced_sample(
            filtered,
            samples_per_class=samples_per_class,
            seed=seed,
        )

        # Copy to test/<run_id>/ with unlabeled filenames
        db_records, ground_truth = self._copy_images_to_test(
            sampled,
            images_dir,
            run_id,
        )

        # Write DB ingestion manifest
        db_manifest_path = self.manifests_root / f"{run_id}_test_ingestion.jsonl"
        self._write_manifest(db_records, db_manifest_path)

        # Write ground truth manifest (separate from DB)
        gt_manifest_path = self.manifests_root / f"{run_id}_test_labels.jsonl"
        self._write_manifest(ground_truth, gt_manifest_path)

        return {
            "run_id": run_id,
            "split": "test",
            "source": source,
            "total_samples": len(db_records),
            "samples_per_class": {label: len(anns) for label, anns in sampled.items()},
            "db_manifest_path": str(db_manifest_path),
            "ground_truth_path": str(gt_manifest_path),
            "seed": seed,
        }


def main():
    """CLI entry point for AffectNet ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest AffectNet images into Reachy emotion classification system"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Ingestion mode")
    
    # Training set ingestion
    train_parser = subparsers.add_parser("train", help="Ingest training set")
    train_parser.add_argument(
        "--samples-per-class",
        type=int,
        default=10000,
        help="Target samples per emotion class (default: 10000)"
    )
    train_parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.6,
        help="Minimum soft-label confidence (default: 0.6)"
    )
    train_parser.add_argument(
        "--max-subset",
        type=int,
        default=1,
        choices=[0, 1, 2],
        help="Maximum subset difficulty: 0=easy, 1=challenging, 2=difficult (default: 1)"
    )
    train_parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    # Validation set ingestion (legacy - outputs to train/<label>/)
    val_parser = subparsers.add_parser("validation", help="Ingest validation set (legacy)")
    val_parser.add_argument("--samples-per-class", type=int, default=500)
    val_parser.add_argument("--min-confidence", type=float, default=0.6)
    val_parser.add_argument("--max-subset", type=int, default=1, choices=[0, 1, 2])
    val_parser.add_argument("--seed", type=int, default=42)
    
    # Run-scoped validation dataset creation
    val_run_parser = subparsers.add_parser("validation-run", help="Create run-scoped validation dataset")
    val_run_parser.add_argument(
        "--run-id",
        type=str,
        required=True,
        help="Run identifier (e.g., run_0001)"
    )
    val_run_parser.add_argument("--samples-per-class", type=int, default=500)
    val_run_parser.add_argument("--seed", type=int, help="Random seed (auto-generated if omitted)")
    
    # Test set creation
    test_parser = subparsers.add_parser("test", help="Create test dataset")
    test_parser.add_argument(
        "--run-id",
        type=str,
        required=True,
        help="Run identifier (e.g., run_0001)"
    )
    test_parser.add_argument("--samples-per-class", type=int, default=250)
    test_parser.add_argument("--min-confidence", type=float, default=0.5)
    test_parser.add_argument("--max-subset", type=int, default=2, choices=[0, 1, 2])
    test_parser.add_argument(
        "--source",
        type=str,
        default="no_human",
        choices=["no_human", "validation"],
        help="Source dataset (default: no_human)"
    )
    test_parser.add_argument("--seed", type=int, help="Random seed (auto-generated if omitted)")
    
    # Common arguments
    parser.add_argument(
        "--affectnet-root",
        type=str,
        default="/media/rusty_admin/project_data/reachy_emotion/affectnet/consolidated/AffectNet+",
        help="AffectNet+ root directory"
    )
    parser.add_argument(
        "--videos-root",
        type=str,
        default="/media/rusty_admin/project_data/reachy_emotion/videos",
        help="Videos root directory"
    )
    parser.add_argument(
        "--manifests-root",
        type=str,
        default="/media/rusty_admin/project_data/reachy_emotion/videos/manifests",
        help="Manifests root directory"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize ingester
    ingester = AffectNetIngester(
        affectnet_root=Path(args.affectnet_root),
        videos_root=Path(args.videos_root),
        manifests_root=Path(args.manifests_root),
    )
    
    # Execute command
    try:
        if args.command == "train":
            result = ingester.ingest_training_set(
                samples_per_class=args.samples_per_class,
                min_confidence=args.min_confidence,
                max_subset=args.max_subset,
                seed=args.seed,
            )
        elif args.command == "validation":
            result = ingester.ingest_validation_set(
                samples_per_class=args.samples_per_class,
                min_confidence=args.min_confidence,
                max_subset=args.max_subset,
                seed=args.seed,
            )
        elif args.command == "validation-run":
            result = ingester.create_validation_dataset(
                run_id=args.run_id,
                samples_per_class=args.samples_per_class,
                seed=args.seed,
            )
        elif args.command == "test":
            result = ingester.create_test_dataset(
                run_id=args.run_id,
                samples_per_class=args.samples_per_class,
                min_confidence=args.min_confidence,
                max_subset=args.max_subset,
                source=args.source,
                seed=args.seed,
            )
        else:
            parser.print_help()
            return 1
        
        # Print summary
        print("\n" + "=" * 60)
        print("INGESTION COMPLETE")
        print("=" * 60)
        print(json.dumps(result, indent=2))
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.exception(f"Ingestion failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
