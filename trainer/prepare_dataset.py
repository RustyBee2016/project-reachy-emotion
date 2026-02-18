"""
Dataset preparation module for training pipeline.
Handles run-specific frame extraction, manifest generation, and dataset hashing.
"""

import json
import hashlib
import random
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

import cv2

logger = logging.getLogger(__name__)


class DatasetPreparer:
    """Prepare run-specific frame datasets from classed train videos."""

    EMOTIONS = ("happy", "sad", "neutral")
    FRAMES_PER_VIDEO = 10
    RUN_ID_PATTERN = re.compile(r"^epoch_\d{2}$")
    
    def __init__(self, base_path: str):
        """
        Initialize dataset preparer.
        
        Args:
            base_path: Root directory containing train/ and manifests/
        """
        self.base_path = Path(base_path)
        self.manifests_path = self.base_path / 'manifests'
        self.train_path = self.base_path / 'train'
        self.test_path = self.base_path / 'test'
        
        # Create directories
        self.manifests_path.mkdir(exist_ok=True)
        self.train_path.mkdir(exist_ok=True)
        self.test_path.mkdir(exist_ok=True)
    
    def prepare_training_dataset(
        self,
        run_id: Optional[str] = None,
        train_fraction: float = 0.7,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Prepare frame-based training dataset for a run.
        
        Args:
            run_id: Run identifier (epoch_XX). Auto-generated if omitted.
            train_fraction: Deprecated compatibility argument (ignored)
            seed: Random seed for reproducibility
        
        Returns:
            Dictionary with run metadata
        """
        normalized_run_id = self.resolve_run_id(run_id)

        if seed is None:
            seed = int(hashlib.md5(normalized_run_id.encode()).hexdigest(), 16) % (2**31)

        rng = random.Random(seed)
        source_videos = self._collect_source_videos()
        self._validate_source_videos(source_videos)

        extracted_frames = self._extract_run_frames(
            run_id=normalized_run_id,
            rng=rng,
            source_videos=source_videos,
        )
        consolidated_frames = self._build_consolidated_run_dataset(
            run_id=normalized_run_id,
            extracted_frames=extracted_frames,
        )

        # Test preparation is intentionally empty for this frame-first train run workflow.
        test_entries: List[Dict[str, str]] = []
        self._generate_manifests(normalized_run_id, consolidated_frames, test_entries)

        dataset_hash = self.calculate_dataset_hash(run_id=normalized_run_id)
        
        return {
            'run_id': normalized_run_id,
            'train_count': len(consolidated_frames),
            'test_count': len(test_entries),
            'videos_processed': sum(len(videos) for videos in source_videos.values()),
            'frames_per_video': self.FRAMES_PER_VIDEO,
            'seed': seed,
            'train_fraction': train_fraction,
            'dataset_hash': dataset_hash
        }

    def resolve_run_id(self, run_id: Optional[str] = None) -> str:
        """Validate run ID or generate the next epoch_XX identifier."""
        if run_id is None:
            return self._next_epoch_run_id()

        normalized = run_id.strip()
        if not normalized:
            raise ValueError("run_id must not be empty")
        if not self.RUN_ID_PATTERN.fullmatch(normalized):
            raise ValueError("run_id must match pattern epoch_XX (e.g., epoch_01)")
        return normalized

    def _next_epoch_run_id(self) -> str:
        """Generate next epoch run identifier from existing train/manifests artifacts."""
        pattern = re.compile(r"^epoch_(\d{2})$")
        max_idx = 0

        if self.train_path.exists():
            for entry in self.train_path.iterdir():
                if not entry.is_dir():
                    continue
                match = pattern.fullmatch(entry.name)
                if match:
                    max_idx = max(max_idx, int(match.group(1)))

        if self.manifests_path.exists():
            for manifest in self.manifests_path.glob("epoch_*_train.jsonl"):
                name = manifest.name.removesuffix("_train.jsonl")
                match = pattern.fullmatch(name)
                if match:
                    max_idx = max(max_idx, int(match.group(1)))

        next_idx = max_idx + 1
        if next_idx > 99:
            raise ValueError("Maximum epoch run_id exceeded (epoch_99)")
        return f"epoch_{next_idx:02d}"

    def _collect_source_videos(self) -> Dict[str, List[Path]]:
        """Collect source videos from train/<label> roots (excluding run directories)."""
        collected: Dict[str, List[Path]] = {}
        for label in self.EMOTIONS:
            label_root = self.train_path / label
            label_root.mkdir(parents=True, exist_ok=True)
            collected[label] = sorted(label_root.glob("*.mp4"))
        return collected

    def _validate_source_videos(self, source_videos: Dict[str, List[Path]]) -> None:
        """Ensure all emotion classes have source videos before extraction."""
        missing = [label for label, videos in source_videos.items() if not videos]
        if missing:
            missing_text = ", ".join(missing)
            raise ValueError(
                "Cannot prepare run dataset: missing source videos in "
                f"train/<label> for: {missing_text}"
            )

    def _extract_run_frames(
        self,
        *,
        run_id: str,
        rng: random.Random,
        source_videos: Dict[str, List[Path]],
    ) -> List[Dict[str, str]]:
        """Extract random frames into train/<label>/<run_id> for each source video."""
        extracted: List[Dict[str, str]] = []

        for label in self.EMOTIONS:
            label_root = self.train_path / label
            label_root.mkdir(parents=True, exist_ok=True)

            run_label_dir = label_root / run_id
            if run_label_dir.exists():
                shutil.rmtree(run_label_dir)
            run_label_dir.mkdir(parents=True, exist_ok=True)

            videos = source_videos.get(label, [])
            for video_path in videos:
                frame_entries = self._extract_random_frames_from_video(
                    video_path=video_path,
                    num_frames=self.FRAMES_PER_VIDEO,
                    output_dir=run_label_dir,
                    label=label,
                    rng=rng,
                )
                extracted.extend(frame_entries)

        return extracted

    def _extract_random_frames_from_video(
        self,
        *,
        video_path: Path,
        num_frames: int,
        output_dir: Path,
        label: str,
        rng: random.Random,
    ) -> List[Dict[str, str]]:
        """Extract N random frames from a video and save as JPEG files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            logger.warning("Skipping unreadable video: %s", video_path)
            return []

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            logger.warning("Skipping zero-frame video: %s", video_path)
            return []

        if total_frames >= num_frames:
            selected = sorted(rng.sample(range(total_frames), num_frames))
        else:
            selected = sorted(rng.randrange(total_frames) for _ in range(num_frames))

        stem = video_path.stem
        entries: List[Dict[str, str]] = []
        for order_idx, frame_idx in enumerate(selected):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            success, frame = cap.read()
            if not success:
                continue

            frame_name = f"{stem}_f{order_idx:02d}_idx{frame_idx:05d}.jpg"
            frame_path = output_dir / frame_name
            if not cv2.imwrite(str(frame_path), frame):
                continue

            entries.append(
                {
                    "video_id": stem,
                    "path": str(frame_path),
                    "label": label,
                    "source_video": str(video_path),
                }
            )

        cap.release()
        return entries

    def _build_consolidated_run_dataset(
        self,
        *,
        run_id: str,
        extracted_frames: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """Create consolidated train/<run_id>/<label>/ frame dataset for training."""
        run_root = self.train_path / run_id
        if run_root.exists():
            shutil.rmtree(run_root)
        run_root.mkdir(parents=True, exist_ok=True)

        consolidated: List[Dict[str, str]] = []
        for frame in extracted_frames:
            label = frame["label"]
            source_frame = Path(frame["path"])
            label_dir = run_root / label
            label_dir.mkdir(parents=True, exist_ok=True)

            destination = label_dir / source_frame.name
            self._link_or_copy(source_frame, destination)

            consolidated.append(
                {
                    "video_id": frame["video_id"],
                    "path": str(destination),
                    "label": label,
                    "source_video": frame["source_video"],
                }
            )

        return consolidated

    @staticmethod
    def _link_or_copy(source: Path, destination: Path) -> None:
        """Prefer hard links to avoid duplication; fall back to copy."""
        if destination.exists():
            destination.unlink()
        try:
            destination.hardlink_to(source)
        except OSError:
            shutil.copy2(source, destination)
    
    def _generate_manifests(
        self,
        run_id: str,
        train_entries: List[Dict[str, str]],
        test_entries: List[Dict[str, str]],
    ):
        """Generate JSONL manifest files for extracted-frame training runs."""
        # Train manifest
        train_manifest_path = self.manifests_path / f'{run_id}_train.jsonl'
        with open(train_manifest_path, 'w') as f:
            for video in train_entries:
                entry = {
                    'video_id': video['video_id'],
                    'path': video['path'],
                    'label': video['label'],
                    'source_video': video.get('source_video'),
                }
                f.write(json.dumps(entry) + '\n')
        
        # Test manifest
        test_manifest_path = self.manifests_path / f'{run_id}_test.jsonl'
        with open(test_manifest_path, 'w') as f:
            for video in test_entries:
                entry = {
                    'video_id': video['video_id'],
                    'path': video['path'],
                    'label': video['label'],
                    'source_video': video.get('source_video'),
                }
                f.write(json.dumps(entry) + '\n')

    def calculate_dataset_hash(self, run_id: Optional[str] = None) -> str:
        """
        Calculate SHA256 hash of dataset for reproducibility.
        
        Returns:
            Hex string of dataset hash
        """
        hasher = hashlib.sha256()
        
        if run_id:
            dataset_root = self.train_path / run_id
            all_files = sorted(dataset_root.rglob('*.jpg'))
        else:
            dataset_root = self.train_path
            all_files = sorted(
                p
                for p in dataset_root.rglob('*')
                if p.is_file() and p.suffix.lower() in {'.mp4', '.jpg', '.jpeg', '.png'}
            )

        for file_path in all_files:
            rel_path = file_path.relative_to(dataset_root)
            hasher.update(str(rel_path).encode())
            hasher.update(str(file_path.stat().st_size).encode())
        
        return hasher.hexdigest()

    def prune_run_artifacts(self, run_id: str) -> None:
        """Remove frame extraction artifacts for a completed run."""
        normalized_run_id = self.resolve_run_id(run_id)

        consolidated_dir = self.train_path / normalized_run_id
        if consolidated_dir.exists():
            shutil.rmtree(consolidated_dir)

        for label in self.EMOTIONS:
            label_run_dir = self.train_path / label / normalized_run_id
            if label_run_dir.exists():
                shutil.rmtree(label_run_dir)

        for suffix in ("train", "test"):
            manifest_path = self.manifests_path / f"{normalized_run_id}_{suffix}.jsonl"
            if manifest_path.exists():
                manifest_path.unlink()
