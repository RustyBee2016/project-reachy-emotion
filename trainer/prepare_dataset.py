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
    RUN_ID_PATTERN = re.compile(r"^run_\d{4}$")
    
    def __init__(self, base_path: str):
        """
        Initialize dataset preparer.
        
        Args:
            base_path: Root directory containing train/ and manifests/
        """
        self.base_path = Path(base_path)
        self.manifests_path = self.base_path / 'manifests'
        self.train_path = self.base_path / 'train'
        self.train_runs_path = self.train_path / 'run'
        self.test_path = self.base_path / 'test'
        
        # Create directories
        self.manifests_path.mkdir(exist_ok=True)
        self.train_path.mkdir(exist_ok=True)
        self.train_runs_path.mkdir(parents=True, exist_ok=True)
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
            run_id: Run identifier (run_xxxx). Auto-generated if omitted.
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

        consolidated_frames = self._extract_run_frames(
            run_id=normalized_run_id,
            rng=rng,
            source_videos=source_videos,
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

    def plan_training_dataset(
        self,
        run_id: Optional[str] = None,
        train_fraction: float = 0.7,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Validate and estimate run outputs without writing frames/manifests."""
        normalized_run_id = self.resolve_run_id(run_id)
        if seed is None:
            seed = int(hashlib.md5(normalized_run_id.encode()).hexdigest(), 16) % (2**31)

        source_videos = self._collect_source_videos()
        self._validate_source_videos(source_videos)

        videos_processed = sum(len(videos) for videos in source_videos.values())
        return {
            "run_id": normalized_run_id,
            "train_count": videos_processed * self.FRAMES_PER_VIDEO,
            "test_count": 0,
            "videos_processed": videos_processed,
            "frames_per_video": self.FRAMES_PER_VIDEO,
            "seed": seed,
            "train_fraction": train_fraction,
            "dataset_hash": "",
            "dry_run": True,
        }

    def resolve_run_id(self, run_id: Optional[str] = None) -> str:
        """Validate run ID or generate the next run_xxxx identifier."""
        if run_id is None:
            return self._next_run_id()

        normalized = run_id.strip()
        if not normalized:
            raise ValueError("run_id must not be empty")
        if not self.RUN_ID_PATTERN.fullmatch(normalized):
            raise ValueError("run_id must match pattern run_xxxx (e.g., run_0001)")
        return normalized

    def _next_run_id(self) -> str:
        """Generate next run identifier from existing train/manifests artifacts."""
        pattern = re.compile(r"^run_(\d{4})$")
        max_idx = 0

        if self.train_path.exists():
            for entry in self.train_path.iterdir():
                if not entry.is_dir():
                    continue
                match = pattern.fullmatch(entry.name)
                if match:
                    max_idx = max(max_idx, int(match.group(1)))
                for nested in entry.iterdir():
                    if not nested.is_dir():
                        continue
                    nested_match = pattern.fullmatch(nested.name)
                    if nested_match:
                        max_idx = max(max_idx, int(nested_match.group(1)))

        if self.base_path.exists():
            for entry in self.base_path.iterdir():
                if not entry.is_dir():
                    continue
                for prefix in ("train_", "test_"):
                    if not entry.name.startswith(prefix):
                        continue
                    match = pattern.fullmatch(entry.name[len(prefix) :])
                    if match:
                        max_idx = max(max_idx, int(match.group(1)))

        if self.manifests_path.exists():
            for manifest in self.manifests_path.glob("run_*_train.jsonl"):
                name = manifest.name[:-len("_train.jsonl")]
                match = pattern.fullmatch(name)
                if match:
                    max_idx = max(max_idx, int(match.group(1)))

        next_idx = max_idx + 1
        if next_idx > 9999:
            raise ValueError("Maximum run_id exceeded (run_9999)")
        return f"run_{next_idx:04d}"

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
        """Extract random frames directly into train/run/<run_id>."""
        extracted: List[Dict[str, str]] = []
        run_root = self.train_runs_path / run_id
        if run_root.exists():
            shutil.rmtree(run_root)
        run_root.mkdir(parents=True, exist_ok=True)

        for label in self.EMOTIONS:
            videos = source_videos.get(label, [])
            for video_path in videos:
                frame_entries = self._extract_random_frames_from_video(
                    video_path=video_path,
                    num_frames=self.FRAMES_PER_VIDEO,
                    output_dir=run_root,
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

            frame_name = f"{label}_{stem}_f{order_idx:02d}_idx{frame_idx:05d}.jpg"
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

    def _load_run_train_labels(self, run_id: str) -> Dict[str, str]:
        """Load frame labels from the run train manifest when available."""
        labels: Dict[str, str] = {}
        manifest_path = self.manifests_path / f"{run_id}_train.jsonl"
        if not manifest_path.exists():
            return labels

        with open(manifest_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                frame_path = str(entry.get("path", "")).strip()
                label = str(entry.get("label", "")).strip().lower()
                if not frame_path or label not in self.EMOTIONS:
                    continue
                normalized = Path(frame_path)
                if normalized.is_absolute():
                    try:
                        normalized = normalized.relative_to(self.base_path)
                    except ValueError:
                        pass
                labels[str(normalized)] = label
                labels[normalized.name] = label
        return labels

    @staticmethod
    def _strip_label_prefix(file_name: str) -> str:
        for label in DatasetPreparer.EMOTIONS:
            prefix = f"{label}_"
            if file_name.startswith(prefix):
                return file_name[len(prefix):]
        return file_name

    def split_run_dataset(
        self,
        run_id: str,
        *,
        train_ratio: float = 0.9,
        seed: Optional[int] = None,
        strip_valid_labels: bool = True,
    ) -> Dict[str, Any]:
        """Move run frames into train/valid dataset subfolders under the run root."""
        normalized_run_id = self.resolve_run_id(run_id)
        if not (0.0 < train_ratio < 1.0):
            raise ValueError("train_ratio must be between 0 and 1 (exclusive)")

        if seed is None:
            seed = int(hashlib.md5(normalized_run_id.encode()).hexdigest(), 16) % (2**31)
        rng = random.Random(seed)

        run_root = self.train_runs_path / normalized_run_id
        if not run_root.exists():
            raise ValueError(f"Run root does not exist: {run_root}")

        train_ds_dir = run_root / f"train_ds_{normalized_run_id}"
        valid_ds_dir = run_root / f"valid_ds_{normalized_run_id}"
        if train_ds_dir.exists():
            shutil.rmtree(train_ds_dir)
        if valid_ds_dir.exists():
            shutil.rmtree(valid_ds_dir)
        train_ds_dir.mkdir(parents=True, exist_ok=True)
        valid_ds_dir.mkdir(parents=True, exist_ok=True)

        flat_frames = sorted([p for p in run_root.glob("*.jpg") if p.is_file()])
        if not flat_frames:
            raise ValueError(
                f"No frame files found directly under {run_root}. "
                "Run extraction first or move files back before splitting."
            )

        label_map = self._load_run_train_labels(normalized_run_id)
        buckets: Dict[str, List[Path]] = {label: [] for label in self.EMOTIONS}
        unknown: List[Path] = []

        for frame_path in flat_frames:
            rel_key = str(frame_path.relative_to(self.base_path))
            label = label_map.get(rel_key) or label_map.get(frame_path.name)
            if label not in self.EMOTIONS:
                name_lower = frame_path.name.lower()
                label = next((em for em in self.EMOTIONS if name_lower.startswith(f"{em}_")), None)
            if label in self.EMOTIONS:
                buckets[label].append(frame_path)
            else:
                unknown.append(frame_path)

        train_frames: List[tuple[Path, str]] = []
        valid_frames: List[tuple[Path, Optional[str]]] = []
        for label in self.EMOTIONS:
            bucket = buckets[label]
            rng.shuffle(bucket)
            if not bucket:
                continue
            if len(bucket) == 1:
                split_idx = 1
            else:
                split_idx = max(1, min(len(bucket) - 1, int(len(bucket) * train_ratio)))
            train_frames.extend((path, label) for path in bucket[:split_idx])
            valid_frames.extend((path, label) for path in bucket[split_idx:])

        for frame_path in unknown:
            train_frames.append((frame_path, "neutral"))

        moved_train: List[Dict[str, Any]] = []
        moved_valid_labeled: List[Dict[str, Any]] = []
        moved_valid_unlabeled: List[Dict[str, Any]] = []

        for src_path, label in train_frames:
            dst_path = train_ds_dir / src_path.name
            shutil.move(str(src_path), str(dst_path))
            moved_train.append({"path": str(dst_path), "label": label})

        for src_path, label in valid_frames:
            target_name = self._strip_label_prefix(src_path.name) if strip_valid_labels else src_path.name
            dst_path = valid_ds_dir / target_name
            suffix_idx = 1
            while dst_path.exists():
                dst_path = valid_ds_dir / f"{Path(target_name).stem}_{suffix_idx:03d}{Path(target_name).suffix}"
                suffix_idx += 1
            shutil.move(str(src_path), str(dst_path))
            moved_valid_labeled.append({"path": str(dst_path), "label": label})
            moved_valid_unlabeled.append({"path": str(dst_path), "label": None})

        train_manifest = self.manifests_path / f"{normalized_run_id}_train_ds.jsonl"
        valid_labeled_manifest = self.manifests_path / f"{normalized_run_id}_valid_ds_labeled.jsonl"
        valid_unlabeled_manifest = self.manifests_path / f"{normalized_run_id}_valid_ds_unlabeled.jsonl"
        with open(train_manifest, "w", encoding="utf-8") as handle:
            for row in moved_train:
                handle.write(json.dumps(row) + "\n")
        with open(valid_labeled_manifest, "w", encoding="utf-8") as handle:
            for row in moved_valid_labeled:
                handle.write(json.dumps(row) + "\n")
        with open(valid_unlabeled_manifest, "w", encoding="utf-8") as handle:
            for row in moved_valid_unlabeled:
                handle.write(json.dumps(row) + "\n")

        return {
            "run_id": normalized_run_id,
            "train_ratio": train_ratio,
            "seed": seed,
            "strip_valid_labels": strip_valid_labels,
            "train_count": len(moved_train),
            "valid_count": len(moved_valid_labeled),
            "train_ds_dir": str(train_ds_dir),
            "valid_ds_dir": str(valid_ds_dir),
            "train_manifest": str(train_manifest),
            "valid_labeled_manifest": str(valid_labeled_manifest),
            "valid_unlabeled_manifest": str(valid_unlabeled_manifest),
        }

    def calculate_dataset_hash(self, run_id: Optional[str] = None) -> str:
        """
        Calculate SHA256 hash of dataset for reproducibility.
        
        Returns:
            Hex string of dataset hash
        """
        hasher = hashlib.sha256()
        
        if run_id:
            dataset_root = self.train_runs_path / run_id
            if not dataset_root.exists():
                # Backward-compat for older consolidated layout.
                dataset_root = self.base_path / f"train_{run_id}"
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

        train_consolidated_dir = self.train_runs_path / normalized_run_id
        if train_consolidated_dir.exists():
            shutil.rmtree(train_consolidated_dir)
        legacy_train_consolidated_dir = self.base_path / f"train_{normalized_run_id}"
        if legacy_train_consolidated_dir.exists():
            shutil.rmtree(legacy_train_consolidated_dir)

        test_consolidated_dir = self.test_path / normalized_run_id
        if test_consolidated_dir.exists():
            shutil.rmtree(test_consolidated_dir)
        legacy_test_consolidated_dir = self.base_path / f"test_{normalized_run_id}"
        if legacy_test_consolidated_dir.exists():
            shutil.rmtree(legacy_test_consolidated_dir)

        for label in self.EMOTIONS:
            label_run_dir = self.train_path / label / normalized_run_id
            if label_run_dir.exists():
                shutil.rmtree(label_run_dir)

        for suffix in ("train", "test"):
            manifest_path = self.manifests_path / f"{normalized_run_id}_{suffix}.jsonl"
            if manifest_path.exists():
                manifest_path.unlink()
