#!/usr/bin/env python3
"""
Test dataset management for Reachy emotion classification.

This module manages run-scoped test datasets with archiving and ground truth
separation. It ensures test datasets are:
- Independent per run (different samples via seeded randomization)
- Unlabeled in filesystem (no emotion in filenames)
- Labeled in separate manifest (for post-evaluation scoring)
- Archivable after use (supports dataset rotation)

Architecture:
    Test Dataset Structure:
    /videos/test/
    ├── run_0001/
    │   ├── affectnet_00000.jpg  # Unlabeled filenames
    │   ├── affectnet_00001.jpg
    │   └── ...
    ├── run_0002/
    │   └── ...
    └── archive/
        ├── run_0001_20260330_184523/
        └── ...
    
    Ground Truth Manifests:
    /videos/manifests/
    ├── run_0001_test_labels.jsonl  # Separate from DB
    ├── run_0002_test_labels.jsonl
    └── ...

Usage:
    # Create test dataset for run_0001
    python -m trainer.manage_test_datasets create \
        --run-id run_0001 \
        --samples-per-class 250 \
        --source no_human

    # Archive test dataset after evaluation
    python -m trainer.manage_test_datasets archive \
        --run-id run_0001

    # Load ground truth for evaluation
    python -m trainer.manage_test_datasets load-gt \
        --run-id run_0001
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from trainer.ingest_affectnet import AffectNetIngester

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestDatasetManager:
    """Manage run-scoped test datasets with archiving."""

    def __init__(
        self,
        *,
        videos_root: Path,
        manifests_root: Path,
        affectnet_root: Path,
    ):
        """
        Initialize test dataset manager.

        Args:
            videos_root: Root directory for video/image storage
            manifests_root: Root directory for manifest files
            affectnet_root: Root directory of AffectNet+ dataset
        """
        self.videos_root = Path(videos_root)
        self.manifests_root = Path(manifests_root)
        self.affectnet_root = Path(affectnet_root)
        
        self.test_path = self.videos_root / "test"
        self.archive_path = self.test_path / "archive"
        
        self.test_path.mkdir(parents=True, exist_ok=True)
        self.archive_path.mkdir(parents=True, exist_ok=True)
        self.manifests_root.mkdir(parents=True, exist_ok=True)

    def create_test_dataset(
        self,
        *,
        run_id: str,
        samples_per_class: int = 250,
        source: str = "no_human",
        min_confidence: float = 0.5,
        max_subset: int = 2,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create new test dataset for a specific run.

        Args:
            run_id: Run identifier (e.g., 'run_0001')
            samples_per_class: Target samples per emotion class
            source: 'no_human' or 'validation'
            min_confidence: Minimum soft-label confidence
            max_subset: Maximum subset difficulty
            seed: Random seed (auto-generated from run_id if None)

        Returns:
            Summary statistics
        """
        logger.info("=" * 60)
        logger.info(f"Creating Test Dataset: {run_id}")
        logger.info("=" * 60)
        
        # Check if test dataset already exists
        test_dir = self.test_path / run_id
        if test_dir.exists():
            raise ValueError(
                f"Test dataset already exists for {run_id}. "
                f"Archive it first with: manage_test_datasets archive --run-id {run_id}"
            )
        
        # Use AffectNetIngester to create test dataset
        ingester = AffectNetIngester(
            affectnet_root=self.affectnet_root,
            videos_root=self.videos_root,
            manifests_root=self.manifests_root,
        )
        
        result = ingester.create_test_dataset(
            run_id=run_id,
            samples_per_class=samples_per_class,
            min_confidence=min_confidence,
            max_subset=max_subset,
            source=source,
            seed=seed,
        )
        
        logger.info("=" * 60)
        logger.info("TEST DATASET CREATED")
        logger.info("=" * 60)
        logger.info(f"Location: {test_dir}")
        logger.info(f"Total samples: {result['total_samples']}")
        logger.info(f"Ground truth: {result['ground_truth_path']}")
        logger.info("=" * 60)
        
        return result

    def archive_test_dataset(
        self,
        *,
        run_id: str,
    ) -> Dict[str, Any]:
        """
        Archive completed test dataset.

        Process:
        1. Move test/<run_id>/ → test/archive/<run_id>_YYYYMMDD_HHMMSS/
        2. Keep manifests for historical reference
        3. Update status log

        Args:
            run_id: Run identifier to archive

        Returns:
            Archive summary
        """
        logger.info("=" * 60)
        logger.info(f"Archiving Test Dataset: {run_id}")
        logger.info("=" * 60)
        
        test_dir = self.test_path / run_id
        if not test_dir.exists():
            raise ValueError(f"Test dataset not found: {test_dir}")
        
        # Generate archive directory name with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        archive_name = f"{run_id}_{timestamp}"
        archive_dir = self.archive_path / archive_name
        
        # Move test directory to archive
        logger.info(f"Moving {test_dir} → {archive_dir}")
        shutil.move(str(test_dir), str(archive_dir))
        
        # Count archived files
        archived_files = list(archive_dir.glob("*.jpg"))
        
        logger.info("=" * 60)
        logger.info("ARCHIVE COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Archived location: {archive_dir}")
        logger.info(f"Files archived: {len(archived_files)}")
        logger.info("=" * 60)
        
        return {
            "run_id": run_id,
            "archive_path": str(archive_dir),
            "files_archived": len(archived_files),
            "timestamp": timestamp,
        }

    def load_ground_truth(
        self,
        *,
        run_id: str,
    ) -> Dict[str, str]:
        """
        Load ground truth labels for Gate A validation.

        Args:
            run_id: Run identifier

        Returns:
            Dictionary mapping file_path to label
        """
        manifest_path = self.manifests_root / f"{run_id}_test_labels.jsonl"
        
        if not manifest_path.exists():
            raise ValueError(f"Ground truth manifest not found: {manifest_path}")
        
        labels: Dict[str, str] = {}
        
        with open(manifest_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                entry = json.loads(line)
                file_path = entry.get("file_path")
                label = entry.get("label")
                
                if file_path and label:
                    labels[file_path] = label
        
        logger.info(f"Loaded {len(labels)} ground truth labels from {manifest_path}")
        return labels

    def list_test_datasets(self) -> Dict[str, Any]:
        """
        List all test datasets (active and archived).

        Returns:
            Summary of test datasets
        """
        active = []
        archived = []
        
        # List active test datasets
        for test_dir in sorted(self.test_path.iterdir()):
            if test_dir.is_dir() and test_dir.name != "archive":
                file_count = len(list(test_dir.glob("*.jpg")))
                active.append({
                    "run_id": test_dir.name,
                    "path": str(test_dir),
                    "file_count": file_count,
                })
        
        # List archived test datasets
        for archive_dir in sorted(self.archive_path.iterdir()):
            if archive_dir.is_dir():
                file_count = len(list(archive_dir.glob("*.jpg")))
                archived.append({
                    "archive_name": archive_dir.name,
                    "path": str(archive_dir),
                    "file_count": file_count,
                })
        
        return {
            "active": active,
            "archived": archived,
            "total_active": len(active),
            "total_archived": len(archived),
        }


def main():
    """CLI entry point for test dataset management."""
    parser = argparse.ArgumentParser(
        description="Manage run-scoped test datasets"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Management command")
    
    # Create test dataset
    create_parser = subparsers.add_parser("create", help="Create new test dataset")
    create_parser.add_argument(
        "--run-id",
        type=str,
        required=True,
        help="Run identifier (e.g., run_0001)"
    )
    create_parser.add_argument(
        "--samples-per-class",
        type=int,
        default=250,
        help="Target samples per emotion class (default: 250)"
    )
    create_parser.add_argument(
        "--source",
        type=str,
        default="no_human",
        choices=["no_human", "validation"],
        help="Source dataset (default: no_human)"
    )
    create_parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        help="Minimum soft-label confidence (default: 0.5)"
    )
    create_parser.add_argument(
        "--max-subset",
        type=int,
        default=2,
        choices=[0, 1, 2],
        help="Maximum subset difficulty (default: 2)"
    )
    create_parser.add_argument(
        "--seed",
        type=int,
        help="Random seed (auto-generated if omitted)"
    )
    
    # Archive test dataset
    archive_parser = subparsers.add_parser("archive", help="Archive test dataset")
    archive_parser.add_argument(
        "--run-id",
        type=str,
        required=True,
        help="Run identifier to archive"
    )
    
    # Load ground truth
    load_parser = subparsers.add_parser("load-gt", help="Load ground truth labels")
    load_parser.add_argument(
        "--run-id",
        type=str,
        required=True,
        help="Run identifier"
    )
    
    # List test datasets
    list_parser = subparsers.add_parser("list", help="List all test datasets")
    
    # Common arguments
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
    parser.add_argument(
        "--affectnet-root",
        type=str,
        default="/media/rusty_admin/project_data/reachy_emotion/affectnet/consolidated/AffectNet+",
        help="AffectNet+ root directory"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Initialize manager
    manager = TestDatasetManager(
        videos_root=Path(args.videos_root),
        manifests_root=Path(args.manifests_root),
        affectnet_root=Path(args.affectnet_root),
    )
    
    # Execute command
    try:
        if args.command == "create":
            result = manager.create_test_dataset(
                run_id=args.run_id,
                samples_per_class=args.samples_per_class,
                source=args.source,
                min_confidence=args.min_confidence,
                max_subset=args.max_subset,
                seed=args.seed,
            )
            print("\n" + json.dumps(result, indent=2))
            
        elif args.command == "archive":
            result = manager.archive_test_dataset(run_id=args.run_id)
            print("\n" + json.dumps(result, indent=2))
            
        elif args.command == "load-gt":
            labels = manager.load_ground_truth(run_id=args.run_id)
            print(f"\nLoaded {len(labels)} ground truth labels")
            print("\nSample (first 5):")
            for i, (path, label) in enumerate(list(labels.items())[:5]):
                print(f"  {path}: {label}")
            
        elif args.command == "list":
            result = manager.list_test_datasets()
            print("\n" + "=" * 60)
            print("TEST DATASETS")
            print("=" * 60)
            print(f"\nActive: {result['total_active']}")
            for ds in result['active']:
                print(f"  {ds['run_id']}: {ds['file_count']} files")
            print(f"\nArchived: {result['total_archived']}")
            for ds in result['archived']:
                print(f"  {ds['archive_name']}: {ds['file_count']} files")
            print("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.exception(f"Command failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
