"""
Dataset module for emotion classification fine-tuning.

Handles:
- Video frame extraction
- Face detection and cropping (optional)
- Data augmentation (Albumentations)
- Multi-dataset support (AffectNet, RAF-DB, synthetic)
"""

import torch
from torch.utils.data import Dataset, DataLoader, Subset, random_split
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Callable, Any
import numpy as np
import cv2
import logging
import json

from trainer.data_roots import resolve_training_data_roots

logger = logging.getLogger(__name__)

# Try to import albumentations, fall back to torchvision transforms
try:
    import albumentations as A
    from albumentations.pytorch import ToTensorV2
    USE_ALBUMENTATIONS = True
except ImportError:
    USE_ALBUMENTATIONS = False
    logger.warning("Albumentations not available, using torchvision transforms")
    from torchvision import transforms


class EmotionDataset(Dataset):
    """
    Dataset for emotion classification from video frames.
    
    Supports:
    - Video files (.mp4) with frame extraction
    - Image files (.jpg, .png) directly
    - Class-organized directory structure: data_dir/{class_name}/*.mp4
    """
    
    # Default class mapping for 3-class classification
    DEFAULT_CLASSES = {"happy": 0, "sad": 1, "neutral": 2}
    
    # Full 8-class mapping (AffectNet compatible)
    FULL_CLASSES = {
        "neutral": 0, "happy": 1, "sad": 2, "anger": 3,
        "fear": 4, "disgust": 5, "surprise": 6, "contempt": 7
    }
    
    def __init__(
        self,
        data_dir: str,
        split: str = "train",
        transform: Optional[Callable] = None,
        class_names: Optional[List[str]] = None,
        frame_sampling: str = "middle",
        frames_per_video: int = 1,
        face_detector: Optional[Any] = None,
        manifest_path: Optional[str] = None,
    ):
        """
        Initialize emotion dataset.
        
        Args:
            data_dir: Root data directory
            split: Data split ("train", "test", "val")
            transform: Image transforms (Albumentations or torchvision)
            class_names: List of class names (default: ["happy", "sad"])
            frame_sampling: Frame extraction strategy
                - "middle": Extract middle frame
                - "random": Random frame (training)
                - "first": First frame
                - "multi": Multiple frames per video
            frames_per_video: Number of frames for "multi" sampling
            face_detector: Optional face detector for cropping
            manifest_path: Optional JSONL manifest to load labeled samples directly
        """
        self.data_dir = Path(data_dir)
        self.split = split
        self.split_dir = self.data_dir / split
        if not self.split_dir.exists():
            class_dirs = [self.data_dir / name for name in (class_names or ["happy", "sad", "neutral"])]
            if any(path.exists() for path in class_dirs):
                self.split_dir = self.data_dir
        self.transform = transform
        self.frame_sampling = frame_sampling
        self.frames_per_video = frames_per_video
        self.face_detector = face_detector
        self.manifest_path = Path(manifest_path) if manifest_path else None
        
        # Set up class mapping
        if class_names is None:
            class_names = ["happy", "sad", "neutral"]
        self.class_names = class_names
        self.class_to_idx = {name: idx for idx, name in enumerate(class_names)}
        self.idx_to_class = {idx: name for name, idx in self.class_to_idx.items()}
        
        # Collect samples
        if self.manifest_path and self.manifest_path.exists():
            self.samples = self._collect_manifest_samples(self.manifest_path)
        else:
            self.samples = self._collect_samples()
        
        logger.info(f"EmotionDataset initialized: {split}")
        logger.info(f"  Data dir: {self.split_dir}")
        logger.info(f"  Classes: {self.class_names}")
        logger.info(f"  Samples: {len(self.samples)}")
        logger.info(f"  Frame sampling: {frame_sampling}")

    def _collect_manifest_samples(self, manifest_path: Path) -> List[Dict]:
        """Collect samples from run manifest entries."""
        samples: List[Dict] = []
        with open(manifest_path, "r") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                label_name = str(entry.get("label", "")).strip().lower()
                if label_name not in self.class_to_idx:
                    continue
                raw_path = Path(str(entry.get("path", "")))
                path = raw_path if raw_path.is_absolute() else (self.data_dir / raw_path)
                if not path.exists() or not path.is_file():
                    continue
                suffix = path.suffix.lower()
                sample_type = "video" if suffix in {".mp4", ".mov", ".avi", ".mkv"} else "image"
                samples.append(
                    {
                        "path": path,
                        "type": sample_type,
                        "label": self.class_to_idx[label_name],
                        "class_name": label_name,
                    }
                )
        return samples
    
    def _collect_samples(self) -> List[Dict]:
        """Collect all samples from the split directory.

        Supports two layouts:
        1. **Class-subdirectory**: ``split_dir/{class_name}/*.{jpg,mp4,...}``
        2. **Flat label-prefix**: ``split_dir/{class_name}_*.{jpg,mp4,...}``
           (used by run-scoped ``train_ds_<run_id>`` directories)

        The method tries class-subdirectories first; if none exist it falls
        back to flat label-prefix collection.
        """
        samples = []
        
        if not self.split_dir.exists():
            logger.warning(f"Split directory does not exist: {self.split_dir}")
            return samples

        # Check whether class subdirectories exist
        has_class_dirs = any(
            (self.split_dir / cn).is_dir() for cn in self.class_names
        )

        if has_class_dirs:
            samples = self._collect_class_dir_samples()
        else:
            samples = self._collect_flat_prefix_samples()

        # Log class distribution
        class_counts: Dict[str, int] = {}
        for sample in samples:
            cn = sample["class_name"]
            class_counts[cn] = class_counts.get(cn, 0) + 1
        logger.info(f"  Class distribution: {class_counts}")
        
        return samples

    def _collect_class_dir_samples(self) -> List[Dict]:
        """Collect from ``split_dir/{class_name}/`` subdirectories."""
        samples: List[Dict] = []
        for class_name in self.class_names:
            class_dir = self.split_dir / class_name
            if not class_dir.exists():
                logger.warning(f"Class directory does not exist: {class_dir}")
                continue
            
            class_idx = self.class_to_idx[class_name]
            
            # Collect video files
            for video_path in class_dir.glob("*.mp4"):
                samples.append({
                    "path": video_path,
                    "type": "video",
                    "label": class_idx,
                    "class_name": class_name,
                })
            
            # Collect image files
            for ext in ["*.jpg", "*.jpeg", "*.png"]:
                for img_path in class_dir.glob(ext):
                    samples.append({
                        "path": img_path,
                        "type": "image",
                        "label": class_idx,
                        "class_name": class_name,
                    })
        return samples

    def _collect_flat_prefix_samples(self) -> List[Dict]:
        """Collect from a flat directory where filenames are prefixed with the
        class label, e.g. ``happy_luma_20260220_*.jpg``.

        This is the layout produced by frame-extraction runs that create
        ``train_ds_<run_id>/`` and ``valid_ds_<run_id>/`` directories.
        """
        samples: List[Dict] = []
        IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
        VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv"}

        for path in sorted(self.split_dir.iterdir()):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix not in IMAGE_EXTS and suffix not in VIDEO_EXTS:
                continue
            sample_type = "video" if suffix in VIDEO_EXTS else "image"

            # Match filename against known class prefixes
            fname_lower = path.name.lower()
            matched_class: Optional[str] = None
            for class_name in self.class_names:
                if fname_lower.startswith(f"{class_name}_"):
                    matched_class = class_name
                    break

            if matched_class is None:
                continue  # skip files that don't match any class prefix

            samples.append({
                "path": path,
                "type": sample_type,
                "label": self.class_to_idx[matched_class],
                "class_name": matched_class,
            })
        return samples
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        """
        Get a sample.
        
        Args:
            idx: Sample index
        
        Returns:
            Tuple of (image_tensor, label)
        """
        sample = self.samples[idx]
        
        # Load image/frame
        if sample["type"] == "video":
            image = self._extract_frame(sample["path"])
        else:
            image = self._load_image(sample["path"])
        
        # Optional face detection and cropping
        if self.face_detector is not None:
            image = self._crop_face(image)
        
        # Apply transforms
        if self.transform is not None:
            if USE_ALBUMENTATIONS:
                augmented = self.transform(image=image)
                image = augmented["image"]
            else:
                # torchvision transforms expect PIL or tensor
                from PIL import Image as PILImage
                image = PILImage.fromarray(image)
                image = self.transform(image)
        else:
            # Default: convert to tensor
            image = torch.from_numpy(image).permute(2, 0, 1).float() / 255.0
        
        return image, sample["label"]
    
    def _extract_frame(self, video_path: Path) -> np.ndarray:
        """
        Extract frame(s) from video.
        
        Args:
            video_path: Path to video file
        
        Returns:
            Frame as numpy array [H, W, 3] RGB
        """
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames == 0:
            raise ValueError(f"Video has no frames: {video_path}")
        
        # Determine frame index based on sampling strategy
        if self.frame_sampling == "middle":
            frame_idx = total_frames // 2
        elif self.frame_sampling == "random":
            frame_idx = np.random.randint(0, total_frames)
        elif self.frame_sampling == "first":
            frame_idx = 0
        else:
            frame_idx = total_frames // 2
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise ValueError(f"Could not read frame {frame_idx} from {video_path}")
        
        # Convert BGR to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        return frame
    
    def _load_image(self, image_path: Path) -> np.ndarray:
        """Load image file."""
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    def _crop_face(self, image: np.ndarray) -> np.ndarray:
        """
        Detect and crop face from image.
        
        Falls back to center crop if no face detected.
        """
        if self.face_detector is None:
            return image
        
        # Placeholder for face detection
        # In production, use RetinaFace, SCRFD, or similar
        # For now, return original image
        return image
    
    def get_class_weights(self) -> torch.Tensor:
        """
        Compute class weights for imbalanced datasets.
        
        Returns:
            Tensor of class weights inversely proportional to frequency
        """
        class_counts = torch.zeros(len(self.class_names))
        for sample in self.samples:
            class_counts[sample["label"]] += 1
        
        # Inverse frequency weighting
        total = class_counts.sum()
        weights = total / (len(self.class_names) * class_counts)
        
        # Normalize
        weights = weights / weights.sum() * len(self.class_names)
        
        return weights
    
    def validate(self, min_samples_per_class: int = 10) -> Dict[str, Any]:
        """
        Validate dataset integrity and readiness for training.
        
        Checks:
        - Minimum samples per class
        - Class balance
        - File accessibility
        - Video/image file integrity (sample check)
        
        Args:
            min_samples_per_class: Minimum required samples per class
        
        Returns:
            Dictionary with validation results and any issues found
        """
        results = {
            'valid': True,
            'total_samples': len(self.samples),
            'class_counts': {},
            'issues': [],
            'warnings': [],
        }
        
        # Check class distribution
        for class_name in self.class_names:
            count = sum(1 for s in self.samples if s['class_name'] == class_name)
            results['class_counts'][class_name] = count
            
            if count == 0:
                results['issues'].append(f"Class '{class_name}' has no samples")
                results['valid'] = False
            elif count < min_samples_per_class:
                results['issues'].append(
                    f"Class '{class_name}' has only {count} samples "
                    f"(minimum: {min_samples_per_class})"
                )
                results['valid'] = False
        
        # Check class balance
        if results['class_counts']:
            counts = list(results['class_counts'].values())
            max_count = max(counts)
            min_count = min(counts)
            if max_count > 0 and min_count / max_count < 0.5:
                imbalance_ratio = min_count / max_count
                results['warnings'].append(
                    f"Class imbalance detected: ratio = {imbalance_ratio:.2f}. "
                    f"Consider using class weights or oversampling."
                )
        
        # Sample file integrity check (check first 5 files per class)
        files_checked = 0
        files_failed = 0
        for class_name in self.class_names:
            class_samples = [s for s in self.samples if s['class_name'] == class_name][:5]
            for sample in class_samples:
                files_checked += 1
                try:
                    if sample['type'] == 'video':
                        cap = cv2.VideoCapture(str(sample['path']))
                        if not cap.isOpened():
                            files_failed += 1
                            results['warnings'].append(f"Cannot open video: {sample['path']}")
                        else:
                            ret, _ = cap.read()
                            if not ret:
                                files_failed += 1
                                results['warnings'].append(f"Cannot read frame from: {sample['path']}")
                        cap.release()
                    else:
                        img = cv2.imread(str(sample['path']))
                        if img is None:
                            files_failed += 1
                            results['warnings'].append(f"Cannot read image: {sample['path']}")
                except Exception as e:
                    files_failed += 1
                    results['warnings'].append(f"Error reading {sample['path']}: {e}")
        
        results['files_checked'] = files_checked
        results['files_failed'] = files_failed
        
        if files_failed > 0:
            results['warnings'].append(
                f"{files_failed}/{files_checked} sample files failed integrity check"
            )
        
        # Log results
        if results['valid']:
            logger.info(f"Dataset validation PASSED: {results['total_samples']} samples")
        else:
            logger.error(f"Dataset validation FAILED: {results['issues']}")
        
        for warning in results['warnings']:
            logger.warning(f"Dataset warning: {warning}")
        
        return results


def validate_dataset(
    data_dir: str,
    split: str = "train",
    class_names: Optional[List[str]] = None,
    min_samples_per_class: int = 10,
) -> Dict[str, Any]:
    """
    Convenience function to validate a dataset before training.
    
    Args:
        data_dir: Root data directory
        split: Data split to validate
        class_names: List of expected class names
        min_samples_per_class: Minimum samples required per class
    
    Returns:
        Validation results dictionary
    """
    if class_names is None:
        class_names = ["happy", "sad", "neutral"]
    
    dataset = EmotionDataset(
        data_dir=data_dir,
        split=split,
        class_names=class_names,
    )
    
    return dataset.validate(min_samples_per_class=min_samples_per_class)


def get_train_transforms(
    input_size: int = 224,
    mean: List[float] = [0.485, 0.456, 0.406],
    std: List[float] = [0.229, 0.224, 0.225],
) -> Callable:
    """
    Get training augmentation transforms.
    
    Augmentations designed for emotion recognition:
    - Geometric: crop, flip, rotation
    - Color: brightness, contrast, saturation
    - Noise/blur: for robustness to camera quality
    
    Args:
        input_size: Target image size
        mean: Normalization mean (ImageNet default)
        std: Normalization std (ImageNet default)
    
    Returns:
        Transform function/composition
    """
    if USE_ALBUMENTATIONS:
        return A.Compose([
            # Resize with random crop
            A.RandomResizedCrop(
                size=(input_size, input_size),
                scale=(0.8, 1.0),
                ratio=(0.9, 1.1),
            ),
            
            # Geometric augmentations
            A.HorizontalFlip(p=0.5),
            A.Rotate(limit=15, p=0.3, border_mode=cv2.BORDER_CONSTANT),
            
            # Color augmentations
            A.ColorJitter(
                brightness=0.3,
                contrast=0.3,
                saturation=0.2,
                hue=0.1,
                p=0.5,
            ),
            
            # Noise and blur for robustness
            A.OneOf([
                A.GaussNoise(var_limit=(10.0, 50.0)),
                A.GaussianBlur(blur_limit=(3, 5)),
                A.MotionBlur(blur_limit=3),
            ], p=0.2),
            
            # Occasional occlusion (simulates partial face visibility)
            A.CoarseDropout(
                max_holes=4,
                max_height=input_size // 8,
                max_width=input_size // 8,
                fill_value=0,
                p=0.1,
            ),
            
            # Normalize and convert to tensor
            A.Normalize(mean=mean, std=std),
            ToTensorV2(),
        ])
    else:
        # Fallback to torchvision
        return transforms.Compose([
            transforms.Resize((input_size, input_size)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(15),
            transforms.ColorJitter(
                brightness=0.3,
                contrast=0.3,
                saturation=0.2,
                hue=0.1,
            ),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ])


def get_val_transforms(
    input_size: int = 224,
    mean: List[float] = [0.485, 0.456, 0.406],
    std: List[float] = [0.229, 0.224, 0.225],
) -> Callable:
    """
    Get validation/test transforms (no augmentation).
    
    Args:
        input_size: Target image size
        mean: Normalization mean
        std: Normalization std
    
    Returns:
        Transform function/composition
    """
    if USE_ALBUMENTATIONS:
        return A.Compose([
            A.Resize(height=input_size, width=input_size),
            A.Normalize(mean=mean, std=std),
            ToTensorV2(),
        ])
    else:
        return transforms.Compose([
            transforms.Resize((input_size, input_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ])


def create_dataloaders(
    data_dir: str,
    batch_size: int = 32,
    num_workers: int = 4,
    input_size: int = 224,
    class_names: Optional[List[str]] = None,
    frame_sampling_train: str = "random",
    frame_sampling_val: str = "middle",
    run_id: Optional[str] = None,
    frames_per_video: int = 1,
) -> Tuple[DataLoader, DataLoader]:
    """
    Create train and validation data loaders.
    
    Args:
        data_dir: Root data directory
        batch_size: Batch size
        num_workers: Number of data loading workers
        input_size: Image input size
        class_names: List of class names
        frame_sampling_train: Frame sampling for training
        frame_sampling_val: Frame sampling for validation
        run_id: Optional run_xxxx to prefer run-scoped train/test roots
        frames_per_video: Number of frames sampled per source video when using multi mode

    Returns:
        Tuple of (train_loader, val_loader)
    """
    roots = resolve_training_data_roots(data_dir, run_id=run_id)
    data_root = Path(data_dir)
    train_manifest_path = None
    val_manifest_path = None
    if run_id:
        manifest_root = data_root / "manifests"
        candidate_train_manifests = [
            manifest_root / f"{run_id}_train_ds.jsonl",
            manifest_root / f"{run_id}_train.jsonl",
        ]
        candidate_val_manifests = [
            manifest_root / f"{run_id}_valid_ds_labeled.jsonl",
            manifest_root / f"{run_id}_test.jsonl",
        ]
        for candidate in candidate_train_manifests:
            if candidate.exists() and candidate.stat().st_size > 0:
                train_manifest_path = str(candidate)
                break
        for candidate in candidate_val_manifests:
            if candidate.exists() and candidate.stat().st_size > 0:
                val_manifest_path = str(candidate)
                break

    # When run-scoped roots are resolved (e.g. train_ds_run_0101/), pass the
    # directory directly and use split="" so EmotionDataset reads from the
    # root itself rather than appending a split subdirectory.
    if roots.uses_run_scoped_train and not train_manifest_path:
        train_data_dir = str(roots.train_root)
        train_split = ""
    else:
        train_data_dir = data_dir
        train_split = "train"

    has_dedicated_val = roots.uses_run_scoped_val or bool(val_manifest_path)

    # Detect default val directory that contains class subdirectories
    # (e.g. videos/test/happy/, videos/test/sad/).  This covers the common
    # case where --skip-train evaluates on the default test split without a
    # run-scoped directory or manifest.
    if not has_dedicated_val and roots.val_root.exists():
        _cls = class_names or list(EmotionDataset.DEFAULT_CLASSES.keys())
        if any((roots.val_root / cn).is_dir() for cn in _cls):
            has_dedicated_val = True

    if roots.uses_run_scoped_val and not val_manifest_path:
        val_data_dir = str(roots.val_root)
        val_split = ""
    elif val_manifest_path:
        val_data_dir = data_dir
        val_split = "test"
    elif has_dedicated_val:
        # Default test dir with class subdirectories
        val_data_dir = str(roots.val_root)
        val_split = ""
    else:
        val_data_dir = None
        val_split = None

    # -----------------------------------------------------------------
    # When no dedicated validation directory exists (default fallback),
    # perform a 90/10 random split on the training data itself so that
    # we always have a validation set during training.
    # -----------------------------------------------------------------
    if has_dedicated_val:
        train_dataset = EmotionDataset(
            data_dir=train_data_dir,
            split=train_split,
            transform=get_train_transforms(input_size),
            class_names=class_names,
            frame_sampling=frame_sampling_train,
            frames_per_video=frames_per_video,
            manifest_path=train_manifest_path,
        )

        val_dataset = EmotionDataset(
            data_dir=val_data_dir,  # type: ignore[arg-type]
            split=val_split or "",
            transform=get_val_transforms(input_size),
            class_names=class_names,
            frame_sampling=frame_sampling_val,
            frames_per_video=frames_per_video,
            manifest_path=val_manifest_path,
        )
    else:
        # Build a single dataset from videos/train, then split 90/10
        full_dataset = EmotionDataset(
            data_dir=train_data_dir,
            split=train_split,
            transform=get_train_transforms(input_size),
            class_names=class_names,
            frame_sampling=frame_sampling_train,
            frames_per_video=frames_per_video,
            manifest_path=train_manifest_path,
        )
        n_total = len(full_dataset)
        n_val = max(1, int(n_total * 0.1))
        n_train = n_total - n_val
        logger.info(
            f"No dedicated val dir — splitting train data 90/10: "
            f"{n_train} train, {n_val} val (from {n_total} total)"
        )
        generator = torch.Generator().manual_seed(42)
        train_subset, val_subset = random_split(
            full_dataset, [n_train, n_val], generator=generator,
        )
        train_dataset = train_subset  # type: ignore[assignment]
        val_dataset = val_subset  # type: ignore[assignment]

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True,
        drop_last=len(train_dataset) > batch_size,
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size * 2,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
    )
    
    return train_loader, val_loader


class MixedDataset(Dataset):
    """
    Dataset combining multiple sources (AffectNet + RAF-DB + synthetic).
    
    Supports weighted sampling from different datasets.
    """
    
    def __init__(
        self,
        datasets: List[EmotionDataset],
        weights: Optional[List[float]] = None,
    ):
        """
        Args:
            datasets: List of EmotionDataset instances
            weights: Sampling weights for each dataset (default: equal)
        """
        self.datasets = datasets
        
        if weights is None:
            weights = [1.0 / len(datasets)] * len(datasets)
        self.weights = weights
        
        # Build combined sample list with dataset indices
        self.samples = []
        for ds_idx, ds in enumerate(datasets):
            for sample_idx in range(len(ds)):
                self.samples.append((ds_idx, sample_idx))
        
        logger.info(f"MixedDataset: {len(datasets)} datasets, {len(self.samples)} total samples")
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        ds_idx, sample_idx = self.samples[idx]
        return self.datasets[ds_idx][sample_idx]
