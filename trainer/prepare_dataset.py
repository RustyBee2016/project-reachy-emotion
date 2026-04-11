"""
Dataset preparation module for training pipeline.
Handles run-specific frame extraction, manifest generation, and dataset hashing.
"""

# ---------------------------------------------------------------------------
# Standard library imports for filesystem operations, hashing, JSON manifests,
# logging, random sampling, regex validation, and type hints.
# ---------------------------------------------------------------------------
import hashlib
import json
import logging
import os
import random
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# OpenCV for video frame extraction and face detection (DNN-based SSD model)
# NumPy for array operations during face bbox calculations
# ---------------------------------------------------------------------------
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class DatasetPreparer:
    """Prepare run-specific frame datasets from classed train videos."""

    # -----------------------------------------------------------------------
    # Class Constants
    # -----------------------------------------------------------------------
    # EMOTIONS: 3-class emotion taxonomy (aligned with Gate A validation)
    # FRAMES_PER_VIDEO: Number of random frames extracted per source video
    # RUN_ID_PATTERN: Enforces run_XXXX naming (e.g., run_0001, run_0042)
    # FACE_DETECTOR_NAME: Identifier for OpenCV DNN face detector model
    # -----------------------------------------------------------------------
    EMOTIONS = ("happy", "sad", "neutral")
    FRAMES_PER_VIDEO = 10
    RUN_ID_PATTERN = re.compile(r"^run_\d{4}$")
    FACE_DETECTOR_NAME = "opencv_dnn_res10_ssd"
    
    # -----------------------------------------------------------------------
    # Initialization
    # -----------------------------------------------------------------------
    # Sets up filesystem paths for source videos, extracted frames, and
    # manifests.  Ensures required directories exist.
    # -----------------------------------------------------------------------
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
        self.validation_runs_path = self.base_path / 'validation' / 'run'
        self.test_path = self.base_path / 'test'
        self._face_net = None
        
        # Create directories
        self.manifests_path.mkdir(exist_ok=True)
        self.train_path.mkdir(exist_ok=True)
        self.train_runs_path.mkdir(parents=True, exist_ok=True)
        self.validation_runs_path.mkdir(parents=True, exist_ok=True)
        self.test_path.mkdir(exist_ok=True)

    # -----------------------------------------------------------------------
    # Face Model Path Resolution
    # -----------------------------------------------------------------------
    # Resolves OpenCV DNN face detector model paths from environment variables
    # or default locations within the project directory.
    # -----------------------------------------------------------------------
    def _resolve_face_model_paths(self) -> Tuple[Path, Path]:
        """Resolve OpenCV DNN face detector model paths."""
        proto_env = os.getenv("REACHY_FACE_DNN_PROTO_PATH")
        model_env = os.getenv("REACHY_FACE_DNN_MODEL_PATH")
        if proto_env and model_env:
            return Path(proto_env), Path(model_env)

        project_root = Path(__file__).resolve().parents[1]
        model_dir = project_root / "trainer" / "models" / "face_detector"
        proto_candidates = [
            model_dir / "deploy.prototxt",
            model_dir / "deploy.prototxt.txt",
        ]
        model_candidates = [
            model_dir / "res10_300x300_ssd_iter_140000.caffemodel",
            model_dir / "res10_300x300_ssd_iter_140000_fp16.caffemodel",
        ]
        proto = next((p for p in proto_candidates if p.exists()), proto_candidates[0])
        model = next((p for p in model_candidates if p.exists()), model_candidates[0])
        return proto, model

    # -----------------------------------------------------------------------
    # Face Detection Network (Lazy Loading)
    # -----------------------------------------------------------------------
    # Loads the OpenCV DNN face detector (SSD ResNet-10 300x300) on first
    # use.  The model files (deploy.prototxt, .caffemodel) must be present
    # in trainer/models/face_detector/ or specified via environment variables.
    # Used when face_crop=True during frame extraction.
    # -----------------------------------------------------------------------
    def _get_face_net(self):
        """Load the OpenCV DNN face detector network lazily."""
        if self._face_net is not None:
            return self._face_net

        proto_path, model_path = self._resolve_face_model_paths()
        if not proto_path.exists() or not model_path.exists():
            raise ValueError(
                "Face detector model files are missing. Set "
                "REACHY_FACE_DNN_PROTO_PATH and REACHY_FACE_DNN_MODEL_PATH "
                "or place deploy.prototxt and res10_300x300_ssd_iter_140000*.caffemodel "
                "under trainer/models/face_detector/."
            )

        self._face_net = cv2.dnn.readNetFromCaffe(str(proto_path), str(model_path))
        return self._face_net

    # -----------------------------------------------------------------------
    # Face Bounding Box Detection
    # -----------------------------------------------------------------------
    # Runs the SSD face detector on a single frame and returns the highest-
    # confidence face bbox (if confidence >= threshold).  Expands the bbox
    # by margin_ratio (default 20%) to include more context around the face.
    # Returns None if no face is detected above the confidence threshold.
    # -----------------------------------------------------------------------
    def _detect_face_bbox(
        self,
        frame: np.ndarray,
        *,
        face_confidence: float,
        margin_ratio: float = 0.2,
    ) -> Optional[Dict[str, Any]]:
        """Detect the best face bbox using OpenCV DNN. Returns None when not detected."""
        net = self._get_face_net()
        height, width = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)),
            1.0,
            (300, 300),
            (104.0, 177.0, 123.0),
        )
        net.setInput(blob)
        detections = net.forward()
        if detections is None or detections.shape[2] == 0:
            return None

        best = None
        for idx in range(detections.shape[2]):
            confidence = float(detections[0, 0, idx, 2])
            if confidence < face_confidence:
                continue
            x1 = int(detections[0, 0, idx, 3] * width)
            y1 = int(detections[0, 0, idx, 4] * height)
            x2 = int(detections[0, 0, idx, 5] * width)
            y2 = int(detections[0, 0, idx, 6] * height)
            if x2 <= x1 or y2 <= y1:
                continue
            if best is None or confidence > best["confidence"]:
                best = {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "confidence": confidence,
                }

        if best is None:
            return None

        box_w = best["x2"] - best["x1"]
        box_h = best["y2"] - best["y1"]
        expand_w = int(box_w * margin_ratio)
        expand_h = int(box_h * margin_ratio)
        x1 = max(0, best["x1"] - expand_w)
        y1 = max(0, best["y1"] - expand_h)
        x2 = min(width, best["x2"] + expand_w)
        y2 = min(height, best["y2"] + expand_h)
        if x2 <= x1 or y2 <= y1:
            return None

        return {
            "x1": int(x1),
            "y1": int(y1),
            "x2": int(x2),
            "y2": int(y2),
            "w": int(x2 - x1),
            "h": int(y2 - y1),
            "confidence": float(best["confidence"]),
        }
    
    # -----------------------------------------------------------------------
    # Main Dataset Preparation Entry Point
    # -----------------------------------------------------------------------
    # Orchestrates the complete frame extraction workflow:
    #   1. Validate run_id or auto-generate next run_XXXX
    #   2. Collect source videos from train/<emotion>/*.mp4
    #   3. Extract N random frames per video (with optional face cropping)
    #   4. Generate JSONL manifests with frame metadata
    #   5. Calculate dataset hash for reproducibility
    #
    # Called by:
    #   - n8n Agent 3 (Promotion/Curation Agent)
    #   - Streamlit UI (03_Train.py)
    #   - run_efficientnet_pipeline.py
    # -----------------------------------------------------------------------
    def prepare_training_dataset(
        self,
        run_id: Optional[str] = None,
        val_fraction: float = 0.25,
        seed: Optional[int] = None,
        face_crop: bool = False,
        target_size: int = 224,
        face_confidence: float = 0.6,
        train_fraction: Optional[float] = None,  # deprecated — ignored, kept for backward compat
    ) -> Dict[str, Any]:
        """
        Prepare frame-based training AND validation datasets for a run.

        Extracts frames from source videos in train/{happy,sad,neutral}/,
        then splits them into training (1 - val_fraction) and validation
        (val_fraction) sets.  Training frames are stored under
        train/run/<run_id>/{happy,sad,neutral}/ and validation frames under
        validation/run/<run_id>/{happy,sad,neutral}/.

        Both Variant 1 and Variant 2 share the same validation dataset
        for a given run_id.

        Args:
            run_id: Run identifier (run_xxxx). Auto-generated if omitted.
            val_fraction: Fraction of extracted frames reserved for validation
                          (default 0.25 = 25 %)
            seed: Random seed for reproducibility
            face_crop: Enable DNN face detection/cropping before saving frames
            target_size: Output frame size (square)
            face_confidence: Minimum face detection confidence

        Returns:
            Dictionary with run metadata
        """
        normalized_run_id = self.resolve_run_id(run_id)

        if seed is None:
            seed = int(hashlib.md5(normalized_run_id.encode()).hexdigest(), 16) % (2**31)

        rng = random.Random(seed)
        source_videos = self._collect_source_videos()
        self._validate_source_videos(source_videos)

        all_frames = self._extract_run_frames(
            run_id=normalized_run_id,
            rng=rng,
            source_videos=source_videos,
            face_crop=face_crop,
            target_size=target_size,
            face_confidence=face_confidence,
        )

        # Split extracted frames into train (75 %) and validation (25 %)
        train_frames, val_frames = self._split_train_val(
            run_id=normalized_run_id,
            rng=rng,
            val_fraction=val_fraction,
            all_entries=all_frames,
        )

        # Generate manifests for both splits
        test_entries: List[Dict[str, str]] = []
        self._generate_manifests(normalized_run_id, train_frames, test_entries)
        self._generate_val_manifest(normalized_run_id, val_frames)

        dataset_hash = self.calculate_dataset_hash(run_id=normalized_run_id)

        return {
            'run_id': normalized_run_id,
            'train_count': len(train_frames),
            'val_count': len(val_frames),
            'test_count': len(test_entries),
            'videos_processed': sum(len(videos) for videos in source_videos.values()),
            'frames_per_video': self.FRAMES_PER_VIDEO,
            'seed': seed,
            'val_fraction': val_fraction,
            'dataset_hash': dataset_hash,
            'face_crop': bool(face_crop),
            'target_size': int(target_size),
            'face_confidence': float(face_confidence),
        }

    def plan_training_dataset(
        self,
        run_id: Optional[str] = None,
        val_fraction: float = 0.25,
        seed: Optional[int] = None,
        face_crop: bool = False,
        target_size: int = 224,
        face_confidence: float = 0.6,
        train_fraction: Optional[float] = None,  # deprecated — ignored, kept for backward compat
    ) -> Dict[str, Any]:
        """Validate and estimate run outputs without writing frames/manifests."""
        normalized_run_id = self.resolve_run_id(run_id)
        if seed is None:
            seed = int(hashlib.md5(normalized_run_id.encode()).hexdigest(), 16) % (2**31)

        source_videos = self._collect_source_videos()
        self._validate_source_videos(source_videos)

        videos_processed = sum(len(videos) for videos in source_videos.values())
        total_frames = videos_processed * self.FRAMES_PER_VIDEO
        est_val = max(1, round(total_frames * val_fraction / len(self.EMOTIONS))) * len(self.EMOTIONS)
        return {
            "run_id": normalized_run_id,
            "train_count": total_frames - est_val,
            "val_count": est_val,
            "test_count": 0,
            "videos_processed": videos_processed,
            "frames_per_video": self.FRAMES_PER_VIDEO,
            "seed": seed,
            "val_fraction": val_fraction,
            "dataset_hash": "",
            "dry_run": True,
            "face_crop": bool(face_crop),
            "target_size": int(target_size),
            "face_confidence": float(face_confidence),
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
        face_crop: bool = False,
        target_size: int = 224,
        face_confidence: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """Extract random frames directly into train/run/<run_id>."""
        extracted: List[Dict[str, str]] = []
        run_root = self.train_runs_path / run_id
        if run_root.exists():
            # Guard: refuse to overwrite a run that has already been split
            # into train/valid datasets.  Call prune_run_artifacts() first
            # if intentional re-extraction is needed.
            completed_markers = [
                d for d in run_root.iterdir()
                if d.is_dir() and (d.name.startswith("train_ds_") or d.name.startswith("valid_ds_"))
            ]
            if completed_markers:
                raise ValueError(
                    f"Run {run_id} already contains split datasets "
                    f"({', '.join(d.name for d in completed_markers)}). "
                    f"Call prune_run_artifacts('{run_id}') before re-extracting."
                )
            shutil.rmtree(run_root)
        run_root.mkdir(parents=True, exist_ok=True)

        for label in self.EMOTIONS:
            videos = source_videos.get(label, [])
            label_dir = run_root / label
            label_dir.mkdir(parents=True, exist_ok=True)
            for video_path in videos:
                frame_entries = self._extract_random_frames_from_video(
                    video_path=video_path,
                    num_frames=self.FRAMES_PER_VIDEO,
                    output_dir=label_dir,
                    label=label,
                    rng=rng,
                    face_crop=face_crop,
                    target_size=target_size,
                    face_confidence=face_confidence,
                )
                extracted.extend(frame_entries)

        return extracted

    # -----------------------------------------------------------------------
    # Train / Validation Split
    # -----------------------------------------------------------------------
    # After all frames are extracted into train/run/<run_id>/<label>/,
    # this method moves val_fraction of them to
    # validation/run/<run_id>/<label>/.  The split is per-class so that
    # each emotion retains its proportional representation in both sets.
    # -----------------------------------------------------------------------
    def _split_train_val(
        self,
        *,
        run_id: str,
        rng: random.Random,
        val_fraction: float,
        all_entries: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Split extracted frames into train and validation sets.

        Moves ``val_fraction`` of frames from
        ``train/run/<run_id>/<label>/`` to
        ``validation/run/<run_id>/<label>/``.

        Returns:
            (train_entries, val_entries)
        """
        val_run_dir = self.validation_runs_path / run_id
        if val_run_dir.exists():
            shutil.rmtree(val_run_dir)

        train_entries: List[Dict[str, Any]] = []
        val_entries: List[Dict[str, Any]] = []

        # Group entries by label
        by_label: Dict[str, List[Dict[str, Any]]] = {}
        for entry in all_entries:
            label = entry["label"]
            by_label.setdefault(label, []).append(entry)

        for label in self.EMOTIONS:
            entries = by_label.get(label, [])
            rng.shuffle(entries)
            n_val = max(1, round(len(entries) * val_fraction)) if entries else 0
            val_batch = entries[:n_val]
            train_batch = entries[n_val:]

            # Create validation class directory and move frames
            val_label_dir = val_run_dir / label
            val_label_dir.mkdir(parents=True, exist_ok=True)
            for entry in val_batch:
                src = Path(entry["path"])
                dst = val_label_dir / src.name
                shutil.move(str(src), str(dst))
                entry["path"] = str(dst)
                val_entries.append(entry)

            train_entries.extend(train_batch)

        logger.info(
            "Split %d frames → %d train + %d val (%.0f%% val) for %s",
            len(all_entries), len(train_entries), len(val_entries),
            val_fraction * 100, run_id,
        )
        return train_entries, val_entries

    def _extract_random_frames_from_video(
        self,
        *,
        video_path: Path,
        num_frames: int,
        output_dir: Path,
        label: str,
        rng: random.Random,
        face_crop: bool = False,
        target_size: int = 224,
        face_confidence: float = 0.6,
    ) -> List[Dict[str, Any]]:
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
        entries: List[Dict[str, Any]] = []
        for order_idx, frame_idx in enumerate(selected):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            success, frame = cap.read()
            if not success:
                continue
            original_h, original_w = frame.shape[:2]

            face_bbox: Optional[Dict[str, Any]] = None
            if face_crop:
                try:
                    face_bbox = self._detect_face_bbox(
                        frame,
                        face_confidence=face_confidence,
                    )
                except Exception as exc:
                    cap.release()
                    raise ValueError(f"Face detection failed for {video_path}: {exc}") from exc
                if face_bbox is None:
                    # Requested policy: skip frames without detected faces.
                    continue
                crop = frame[face_bbox["y1"]:face_bbox["y2"], face_bbox["x1"]:face_bbox["x2"]]
                if crop.size == 0:
                    continue
                frame = cv2.resize(crop, (int(target_size), int(target_size)), interpolation=cv2.INTER_AREA)

            frame_name = f"{label}_{stem}_f{order_idx:02d}_idx{frame_idx:05d}.jpg"
            frame_path = output_dir / frame_name
            if not cv2.imwrite(str(frame_path), frame):
                continue

            entry: Dict[str, Any] = {
                "video_id": stem,
                "path": str(frame_path),
                "label": label,
                "source_video": str(video_path),
            }
            if face_bbox is not None:
                entry["face_bbox"] = {
                    "x": int(face_bbox["x1"]),
                    "y": int(face_bbox["y1"]),
                    "w": int(face_bbox["w"]),
                    "h": int(face_bbox["h"]),
                }
                entry["face_confidence"] = float(face_bbox["confidence"])
                entry["face_detector"] = self.FACE_DETECTOR_NAME
                entry["face_crop"] = True
                entry["target_size"] = int(target_size)
                entry["source_frame_shape"] = [int(original_h), int(original_w)]
            entries.append(entry)

        cap.release()
        return entries

    def _generate_manifests(
        self,
        run_id: str,
        train_entries: List[Dict[str, Any]],
        test_entries: List[Dict[str, Any]],
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
                for optional_key in (
                    "face_bbox",
                    "face_confidence",
                    "face_detector",
                    "face_crop",
                    "target_size",
                    "source_frame_shape",
                ):
                    if optional_key in video:
                        entry[optional_key] = video[optional_key]
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
                for optional_key in (
                    "face_bbox",
                    "face_confidence",
                    "face_detector",
                    "face_crop",
                    "target_size",
                    "source_frame_shape",
                ):
                    if optional_key in video:
                        entry[optional_key] = video[optional_key]
                f.write(json.dumps(entry) + '\n')

    def _generate_val_manifest(
        self,
        run_id: str,
        val_entries: List[Dict[str, Any]],
    ) -> None:
        """Generate JSONL manifest for the validation split."""
        val_manifest_path = self.manifests_path / f'{run_id}_val.jsonl'
        with open(val_manifest_path, 'w') as f:
            for frame in val_entries:
                entry = {
                    'video_id': frame['video_id'],
                    'path': frame['path'],
                    'label': frame['label'],
                    'source_video': frame.get('source_video'),
                }
                for optional_key in (
                    "face_bbox",
                    "face_confidence",
                    "face_detector",
                    "face_crop",
                    "target_size",
                    "source_frame_shape",
                ):
                    if optional_key in frame:
                        entry[optional_key] = frame[optional_key]
                f.write(json.dumps(entry) + '\n')

    def _load_run_train_entry_map(self, run_id: str) -> Dict[str, Dict[str, Any]]:
        """Map frame path/name to manifest entry for metadata-preserving splits."""
        entry_map: Dict[str, Dict[str, Any]] = {}
        manifest_path = self.manifests_path / f"{run_id}_train.jsonl"
        if not manifest_path.exists():
            return entry_map
        with open(manifest_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                frame_path = str(entry.get("path", "")).strip()
                if not frame_path:
                    continue
                path_obj = Path(frame_path)
                if path_obj.is_absolute():
                    try:
                        path_obj = path_obj.relative_to(self.base_path)
                    except ValueError:
                        pass
                entry_map[str(path_obj)] = entry
                entry_map[path_obj.name] = entry
        return entry_map

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

    # -----------------------------------------------------------------------
    # Dataset Hash Calculation (Reproducibility Tracking)
    # -----------------------------------------------------------------------
    # Computes a SHA256 hash of the dataset based on file paths and sizes.
    # This hash is logged to MLflow and used to detect dataset drift between
    # training runs.  If the hash changes, it indicates the dataset has been
    # modified (new videos added, frames re-extracted, etc.).
    #
    # IMPORTANT: This is a path+size hash, NOT a content hash.  Two files
    # with identical paths and sizes but different pixel data will produce
    # the same hash.  This is a deliberate speed/accuracy tradeoff for large
    # image datasets.  For content-level guarantees, extend with a
    # hash_contents=True parameter that reads and hashes pixel data.
    # -----------------------------------------------------------------------
    def calculate_dataset_hash(self, run_id: Optional[str] = None) -> str:
        """
        Calculate SHA256 hash of dataset for reproducibility.

        NOTE: This hash is based on *relative file paths and file sizes*, not
        file contents.  This is a deliberate speed-vs-accuracy trade-off:
        hashing large image sets by content is slow, while path+size is fast
        and sufficient to detect structural changes (added/removed/renamed
        files or significant content edits).  Two files at the same path with
        identical sizes but different pixel data will produce the same hash.
        For Gate A reproducibility audits requiring content-level guarantees,
        consider extending this method with an optional ``hash_contents=True``
        parameter.
        
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
