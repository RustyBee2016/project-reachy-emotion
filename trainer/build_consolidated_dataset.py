#!/usr/bin/env python3
"""
Consolidated dataset builder for Reachy emotion classification.

This module merges multiple data sources (Luma videos + AffectNet images) into
unified training/validation datasets for model training.

Architecture:
    Data Sources:
    1. Luma Videos: Synthetic videos generated via web app
       - Location: train/<label>/luma_*.mp4
       - Processing: Extract N frames per video
       - Contribution: ~5,000 frames per class (500 videos × 10 frames)
    
    2. AffectNet Images: Static face images from AffectNet+
       - Location: train/<label>/affectnet_*.jpg
       - Processing: Copy directly (already 224×224)
       - Contribution: ~10,000 images per class

    Output Structure:
    /videos/train/run/<run_id>/
    ├── happy_luma_20260330_f00_idx00123.jpg
    ├── happy_affectnet_47983.jpg
    ├── sad_luma_20260331_f01_idx00456.jpg
    ├── sad_affectnet_11274.jpg
    └── ...
    
    After splitting (90/10):
    /videos/train/run/<run_id>/
    ├── train_ds_<run_id>/  # 90% of samples
    └── valid_ds_<run_id>/  # 10% of samples

Usage:
    python -m trainer.build_consolidated_dataset \
        --run-id run_0100 \
        --luma-videos-per-class 500 \
        --affectnet-images-per-class 10000 \
        --frames-per-video 10 \
        --seed 42
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from trainer.prepare_dataset import DatasetPreparer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

EMOTIONS = ("happy", "sad", "neutral")


class ConsolidatedDatasetBuilder:
    """Build unified datasets from Luma videos + AffectNet images."""

    def __init__(self, videos_root: Path):
        """
        Initialize dataset builder.

        Args:
            videos_root: Root directory containing train/ and manifests/
        """
        self.videos_root = Path(videos_root)
        self.train_path = self.videos_root / "train"
        self.manifests_path = self.videos_root / "manifests"
        
        if not self.train_path.exists():
            raise ValueError(f"Training directory not found: {self.train_path}")
        
        self.manifests_path.mkdir(parents=True, exist_ok=True)
        self.preparer = DatasetPreparer(str(self.videos_root))

    def _collect_source_videos(
        self,
        luma_videos_per_class: Optional[int] = None,
    ) -> Dict[str, List[Path]]:
        """
        Collect Luma video files from train/<label>/ directories.

        Args:
            luma_videos_per_class: Maximum videos per class (None = all)

        Returns:
            Dictionary mapping emotion labels to video paths
        """
        videos: Dict[str, List[Path]] = {}
        
        for label in EMOTIONS:
            label_dir = self.train_path / label
            if not label_dir.exists():
                logger.warning(f"Label directory not found: {label_dir}")
                videos[label] = []
                continue
            
            # Collect Luma videos (*.mp4 files)
            all_videos = sorted(label_dir.glob("luma_*.mp4"))
            
            if luma_videos_per_class is not None and len(all_videos) > luma_videos_per_class:
                videos[label] = all_videos[:luma_videos_per_class]
            else:
                videos[label] = all_videos
            
            logger.info(f"Found {len(videos[label])} Luma videos for {label}")
        
        return videos

    def _collect_affectnet_images(
        self,
        affectnet_images_per_class: Optional[int] = None,
    ) -> Dict[str, List[Path]]:
        """
        Collect AffectNet image files from train/<label>/ directories.

        Args:
            affectnet_images_per_class: Maximum images per class (None = all)

        Returns:
            Dictionary mapping emotion labels to image paths
        """
        images: Dict[str, List[Path]] = {}
        
        for label in EMOTIONS:
            label_dir = self.train_path / label
            if not label_dir.exists():
                logger.warning(f"Label directory not found: {label_dir}")
                images[label] = []
                continue
            
            # Collect AffectNet images
            all_images = sorted(label_dir.glob("affectnet_*.jpg"))
            
            if affectnet_images_per_class is not None and len(all_images) > affectnet_images_per_class:
                images[label] = all_images[:affectnet_images_per_class]
            else:
                images[label] = all_images
            
            logger.info(f"Found {len(images[label])} AffectNet images for {label}")
        
        return images

    def build_training_dataset(
        self,
        *,
        run_id: str,
        luma_videos_per_class: int = 500,
        affectnet_images_per_class: int = 10000,
        frames_per_video: int = 10,
        seed: int = 42,
        split_ratio: float = 0.9,
        face_crop: bool = False,
        face_target_size: int = 224,
        face_confidence: float = 0.6,
    ) -> Dict[str, Any]:
        """
        Build consolidated training dataset from Luma videos + AffectNet images.

        Process:
        1. Collect Luma videos from train/<label>/luma_*.mp4
        2. Extract frames using DatasetPreparer → train/run/<run_id>/
        3. Collect AffectNet images from train/<label>/affectnet_*.jpg
        4. Copy AffectNet images to train/run/<run_id>/
        5. Generate unified manifest
        6. Split into train_ds/valid_ds (90/10)

        Args:
            run_id: Run identifier (e.g., 'run_0100')
            luma_videos_per_class: Number of Luma videos per emotion class
            affectnet_images_per_class: Number of AffectNet images per emotion class
            frames_per_video: Frames to extract from each Luma video
            seed: Random seed for reproducibility
            split_ratio: Train/valid split ratio (default: 0.9)
            face_crop: Enable face detection and cropping
            face_target_size: Face crop output size
            face_confidence: Minimum face detection confidence

        Returns:
            Summary statistics
        """
        logger.info("=" * 60)
        logger.info(f"Building Consolidated Dataset: {run_id}")
        logger.info("=" * 60)
        logger.info(f"Luma videos per class: {luma_videos_per_class}")
        logger.info(f"AffectNet images per class: {affectnet_images_per_class}")
        logger.info(f"Frames per video: {frames_per_video}")
        logger.info(f"Split ratio: {split_ratio:.1%} train / {1-split_ratio:.1%} valid")
        
        # Step 1: Collect Luma videos
        logger.info("\n--- Step 1: Collecting Luma Videos ---")
        luma_videos = self._collect_source_videos(luma_videos_per_class)
        total_luma = sum(len(vids) for vids in luma_videos.values())
        logger.info(f"Total Luma videos: {total_luma}")
        
        # Step 2: Extract frames from Luma videos
        logger.info("\n--- Step 2: Extracting Frames from Luma Videos ---")
        
        # Temporarily override DatasetPreparer's source collection
        # to use only our selected Luma videos
        original_collect = self.preparer._collect_source_videos
        
        def _custom_collect():
            return luma_videos
        
        self.preparer._collect_source_videos = _custom_collect
        
        try:
            frame_result = self.preparer.prepare_training_dataset(
                run_id=run_id,
                seed=seed,
                face_crop=face_crop,
                target_size=face_target_size,
                face_confidence=face_confidence,
            )
            logger.info(f"Extracted {frame_result['train_count']} frames from Luma videos")
        finally:
            # Restore original method
            self.preparer._collect_source_videos = original_collect
        
        # Step 3: Collect AffectNet images
        logger.info("\n--- Step 3: Collecting AffectNet Images ---")
        affectnet_images = self._collect_affectnet_images(affectnet_images_per_class)
        total_affectnet = sum(len(imgs) for imgs in affectnet_images.values())
        logger.info(f"Total AffectNet images: {total_affectnet}")
        
        # Step 4: Copy AffectNet images to run directory
        logger.info("\n--- Step 4: Copying AffectNet Images to Run Directory ---")
        run_root = self.videos_root / "train" / "run" / run_id
        
        affectnet_count = 0
        for label, images in affectnet_images.items():
            for img_path in images:
                dst_name = f"{label}_{img_path.name}"
                dst_path = run_root / dst_name
                
                # Copy image
                import shutil
                shutil.copy2(img_path, dst_path)
                affectnet_count += 1
        
        logger.info(f"Copied {affectnet_count} AffectNet images")
        
        # Step 5: Update manifest to include AffectNet images
        logger.info("\n--- Step 5: Updating Manifest ---")
        manifest_path = self.manifests_path / f"{run_id}_train.jsonl"
        
        # Append AffectNet entries to existing manifest
        with open(manifest_path, 'a') as f:
            for label, images in affectnet_images.items():
                for img_path in images:
                    dst_name = f"{label}_{img_path.name}"
                    dst_path = run_root / dst_name
                    
                    entry = {
                        "video_id": img_path.stem,
                        "path": str(dst_path),
                        "label": label,
                        "source_video": None,
                        "source_type": "affectnet_image",
                    }
                    f.write(json.dumps(entry) + '\n')
        
        logger.info(f"Updated manifest: {manifest_path}")
        
        # Step 6: Split into train_ds/valid_ds
        logger.info("\n--- Step 6: Splitting into Train/Valid Datasets ---")
        split_result = self.preparer.split_run_dataset(
            run_id=run_id,
            train_ratio=split_ratio,
            seed=seed,
            strip_valid_labels=True,
        )
        
        logger.info(f"Train dataset: {split_result['train_count']} samples")
        logger.info(f"Valid dataset: {split_result['valid_count']} samples")
        
        # Summary
        total_samples = frame_result['train_count'] + affectnet_count
        
        summary = {
            "run_id": run_id,
            "luma_videos": total_luma,
            "luma_frames": frame_result['train_count'],
            "affectnet_images": affectnet_count,
            "total_samples": total_samples,
            "train_samples": split_result['train_count'],
            "valid_samples": split_result['valid_count'],
            "train_ds_dir": split_result['train_ds_dir'],
            "valid_ds_dir": split_result['valid_ds_dir'],
            "train_manifest": split_result['train_manifest'],
            "valid_labeled_manifest": split_result['valid_labeled_manifest'],
            "valid_unlabeled_manifest": split_result['valid_unlabeled_manifest'],
            "dataset_hash": frame_result['dataset_hash'],
            "seed": seed,
        }
        
        logger.info("\n" + "=" * 60)
        logger.info("CONSOLIDATED DATASET BUILD COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total samples: {total_samples}")
        logger.info(f"  Luma frames: {frame_result['train_count']}")
        logger.info(f"  AffectNet images: {affectnet_count}")
        logger.info(f"Train/Valid split: {split_result['train_count']}/{split_result['valid_count']}")
        logger.info("=" * 60)
        
        return summary


def main():
    """CLI entry point for consolidated dataset building."""
    parser = argparse.ArgumentParser(
        description="Build consolidated training dataset from Luma videos + AffectNet images"
    )
    
    parser.add_argument(
        "--run-id",
        type=str,
        required=True,
        help="Run identifier (e.g., run_0100)"
    )
    parser.add_argument(
        "--luma-videos-per-class",
        type=int,
        default=500,
        help="Number of Luma videos per emotion class (default: 500)"
    )
    parser.add_argument(
        "--affectnet-images-per-class",
        type=int,
        default=10000,
        help="Number of AffectNet images per emotion class (default: 10000)"
    )
    parser.add_argument(
        "--frames-per-video",
        type=int,
        default=10,
        help="Frames to extract from each Luma video (default: 10)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    parser.add_argument(
        "--split-ratio",
        type=float,
        default=0.9,
        help="Train/valid split ratio (default: 0.9)"
    )
    parser.add_argument(
        "--face-crop",
        action="store_true",
        help="Enable face detection and cropping"
    )
    parser.add_argument(
        "--face-target-size",
        type=int,
        default=224,
        help="Face crop output size (default: 224)"
    )
    parser.add_argument(
        "--face-confidence",
        type=float,
        default=0.6,
        help="Minimum face detection confidence (default: 0.6)"
    )
    parser.add_argument(
        "--videos-root",
        type=str,
        default="/media/rusty_admin/project_data/reachy_emotion/videos",
        help="Videos root directory"
    )
    
    args = parser.parse_args()
    
    try:
        builder = ConsolidatedDatasetBuilder(Path(args.videos_root))
        
        result = builder.build_training_dataset(
            run_id=args.run_id,
            luma_videos_per_class=args.luma_videos_per_class,
            affectnet_images_per_class=args.affectnet_images_per_class,
            frames_per_video=args.frames_per_video,
            seed=args.seed,
            split_ratio=args.split_ratio,
            face_crop=args.face_crop,
            face_target_size=args.face_target_size,
            face_confidence=args.face_confidence,
        )
        
        print("\n" + "=" * 60)
        print("BUILD SUMMARY")
        print("=" * 60)
        print(json.dumps(result, indent=2))
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.exception(f"Dataset build failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
