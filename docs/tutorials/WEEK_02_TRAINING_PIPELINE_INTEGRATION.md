# Week 2 Tutorial: Training Pipeline Integration

**Project**: Reachy Emotion Recognition  
**Duration**: 5 days  
**Prerequisites**: Week 1 complete, PyTorch environment configured

---

## Overview

This week focuses on integrating statistical analysis with the training pipeline, validating pre-trained weights, and ensuring Gate A checks are automated.

### Weekly Goals
- [ ] Download/verify pre-trained EfficientNet-B0 weights (AffectNet + RAF-DB)
- [ ] End-to-end test training pipeline with synthetic data
- [ ] Validate Gate A checks in training orchestrator
- [ ] Wire stats scripts to post-training evaluation

---

## Day 1: Pre-trained Weights Setup

### Step 1.1: Understand the Model Architecture

The project uses EfficientNet-B0 pre-trained on AffectNet + RAF-DB datasets for facial emotion recognition.

**Key files:**
- `trainer/fer_finetune/model.py` — Model architecture
- `trainer/fer_finetune/config.py` — Configuration system
- `trainer/fer_finetune/specs/` — YAML config files

### Step 1.2: Create Weights Download Script

Create `trainer/download_pretrained_weights.py`:

```python
#!/usr/bin/env python3
"""
Download and verify pre-trained EfficientNet-B0 weights for emotion recognition.

Supports:
- HSEmotion weights (AffectNet + RAF-DB)
- ImageNet fallback
- Checksum verification
"""

import os
import sys
import hashlib
import requests
from pathlib import Path
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Weight sources and checksums
WEIGHT_SOURCES = {
    "hsemotion_affectnet": {
        "url": "https://github.com/HSE-asavchenko/face-emotion-recognition/releases/download/v1.0/affectnet_emotions.pt",
        "sha256": None,  # Will be computed on first download
        "description": "HSEmotion EfficientNet-B0 trained on AffectNet",
    },
    "hsemotion_rafdb": {
        "url": "https://github.com/HSE-asavchenko/face-emotion-recognition/releases/download/v1.0/rafdb_emotions.pt",
        "sha256": None,
        "description": "HSEmotion EfficientNet-B0 trained on RAF-DB",
    },
    "imagenet": {
        "url": "torchvision",  # Use torchvision built-in
        "sha256": None,
        "description": "ImageNet pre-trained (fallback)",
    },
}

DEFAULT_WEIGHTS_DIR = Path("/media/rusty_admin/project_data/ml_models/resnet50")


def download_file(url: str, dest_path: Path, desc: str = "Downloading") -> bool:
    """Download file with progress bar."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(dest_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=desc) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    pbar.update(len(chunk))
        
        return True
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 checksum of file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def verify_weights(file_path: Path, expected_sha256: str = None) -> bool:
    """Verify weights file exists and optionally check checksum."""
    if not file_path.exists():
        logger.error(f"Weights file not found: {file_path}")
        return False
    
    if expected_sha256:
        actual_sha256 = compute_sha256(file_path)
        if actual_sha256 != expected_sha256:
            logger.error(f"Checksum mismatch: expected {expected_sha256}, got {actual_sha256}")
            return False
        logger.info(f"Checksum verified: {actual_sha256[:16]}...")
    
    # Try to load with PyTorch
    try:
        import torch
        state_dict = torch.load(file_path, map_location='cpu')
        logger.info(f"Weights loaded successfully, {len(state_dict)} keys")
        return True
    except Exception as e:
        logger.error(f"Failed to load weights: {e}")
        return False


def download_hsemotion_weights(
    weights_dir: Path = DEFAULT_WEIGHTS_DIR,
    source: str = "hsemotion_affectnet"
) -> Path:
    """
    Download HSEmotion pre-trained weights.
    
    Args:
        weights_dir: Directory to save weights
        source: Weight source key
    
    Returns:
        Path to downloaded weights
    """
    weights_dir.mkdir(parents=True, exist_ok=True)
    
    source_info = WEIGHT_SOURCES.get(source)
    if not source_info:
        raise ValueError(f"Unknown source: {source}")
    
    if source_info["url"] == "torchvision":
        logger.info("Using torchvision ImageNet weights (no download needed)")
        return None
    
    filename = source_info["url"].split("/")[-1]
    dest_path = weights_dir / filename
    
    if dest_path.exists():
        logger.info(f"Weights already exist: {dest_path}")
        if verify_weights(dest_path, source_info.get("sha256")):
            return dest_path
        else:
            logger.warning("Existing weights failed verification, re-downloading...")
    
    logger.info(f"Downloading {source_info['description']}...")
    if download_file(source_info["url"], dest_path, desc=filename):
        # Compute and log checksum
        sha256 = compute_sha256(dest_path)
        logger.info(f"Downloaded: {dest_path}")
        logger.info(f"SHA256: {sha256}")
        
        if verify_weights(dest_path):
            return dest_path
    
    return None


def setup_pretrained_weights(
    weights_dir: Path = DEFAULT_WEIGHTS_DIR,
    preferred_source: str = "hsemotion_affectnet"
) -> Path:
    """
    Set up pre-trained weights, with fallback to ImageNet.
    
    Args:
        weights_dir: Directory for weights
        preferred_source: Preferred weight source
    
    Returns:
        Path to weights file (or None for torchvision)
    """
    logger.info("=" * 60)
    logger.info("Setting up pre-trained weights")
    logger.info("=" * 60)
    
    # Try preferred source
    weights_path = download_hsemotion_weights(weights_dir, preferred_source)
    if weights_path:
        return weights_path
    
    # Fallback to RAF-DB
    if preferred_source != "hsemotion_rafdb":
        logger.info("Trying RAF-DB weights as fallback...")
        weights_path = download_hsemotion_weights(weights_dir, "hsemotion_rafdb")
        if weights_path:
            return weights_path
    
    # Fallback to ImageNet
    logger.warning("Using ImageNet weights as fallback")
    return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Download pre-trained weights")
    parser.add_argument(
        "--source",
        choices=list(WEIGHT_SOURCES.keys()),
        default="hsemotion_affectnet",
        help="Weight source"
    )
    parser.add_argument(
        "--weights-dir",
        type=Path,
        default=DEFAULT_WEIGHTS_DIR,
        help="Directory to save weights"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing weights"
    )
    
    args = parser.parse_args()
    
    if args.verify_only:
        weights_dir = args.weights_dir
        for f in weights_dir.glob("*.pt"):
            print(f"\nVerifying: {f}")
            verify_weights(f)
    else:
        weights_path = setup_pretrained_weights(args.weights_dir, args.source)
        if weights_path:
            print(f"\nWeights ready: {weights_path}")
        else:
            print("\nUsing torchvision ImageNet weights")


if __name__ == "__main__":
    main()
```

### Step 1.3: Run Weights Setup

```bash
# Download weights
python trainer/download_pretrained_weights.py --source hsemotion_affectnet

# Verify existing weights
python trainer/download_pretrained_weights.py --verify-only
```

### Step 1.4: Update Model to Use Downloaded Weights

Update `trainer/fer_finetune/model.py` to load custom weights:

```python
def load_pretrained_weights(self, weights_path: str):
    """Load pre-trained weights from file."""
    if weights_path and Path(weights_path).exists():
        state_dict = torch.load(weights_path, map_location='cpu')
        
        # Handle different state dict formats
        if 'model_state_dict' in state_dict:
            state_dict = state_dict['model_state_dict']
        elif 'state_dict' in state_dict:
            state_dict = state_dict['state_dict']
        
        # Load with strict=False to allow mismatched classifier heads
        missing, unexpected = self.load_state_dict(state_dict, strict=False)
        logger.info(f"Loaded weights from {weights_path}")
        logger.info(f"Missing keys: {len(missing)}, Unexpected: {len(unexpected)}")
    else:
        logger.warning(f"Weights not found: {weights_path}, using random init")
```

### Checkpoint: Day 1 Complete
- [ ] Weights download script created
- [ ] Weights downloaded and verified
- [ ] Model updated to load custom weights

---

## Day 2: Training Pipeline E2E Test

### Step 2.1: Create Synthetic Training Data

Create `trainer/create_synthetic_dataset.py`:

```python
#!/usr/bin/env python3
"""
Create synthetic dataset for training pipeline testing.

Generates fake image files and labels for E2E testing without real data.
"""

import os
import numpy as np
from pathlib import Path
from PIL import Image
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EMOTION_CLASSES = ["anger", "contempt", "disgust", "fear", 
                   "happiness", "neutral", "sadness", "surprise"]


def create_synthetic_image(size: tuple = (224, 224)) -> Image.Image:
    """Create a random synthetic image."""
    # Random noise with some structure
    data = np.random.randint(0, 255, (*size, 3), dtype=np.uint8)
    return Image.fromarray(data, 'RGB')


def create_synthetic_dataset(
    output_dir: Path,
    n_train: int = 100,
    n_val: int = 20,
    n_test: int = 20,
    seed: int = 42
):
    """
    Create synthetic dataset with train/val/test splits.
    
    Args:
        output_dir: Output directory
        n_train: Number of training samples per class
        n_val: Number of validation samples per class
        n_test: Number of test samples per class
        seed: Random seed
    """
    np.random.seed(seed)
    output_dir = Path(output_dir)
    
    splits = {
        "train": n_train,
        "val": n_val,
        "test": n_test,
    }
    
    manifest = {"train": [], "val": [], "test": []}
    
    for split_name, n_per_class in splits.items():
        split_dir = output_dir / split_name
        
        for class_idx, class_name in enumerate(EMOTION_CLASSES):
            class_dir = split_dir / class_name
            class_dir.mkdir(parents=True, exist_ok=True)
            
            for i in range(n_per_class):
                # Create image
                img = create_synthetic_image()
                img_path = class_dir / f"{class_name}_{i:04d}.jpg"
                img.save(img_path, quality=85)
                
                # Add to manifest
                manifest[split_name].append({
                    "path": str(img_path.relative_to(output_dir)),
                    "label": class_idx,
                    "class_name": class_name,
                })
        
        logger.info(f"Created {split_name}: {len(manifest[split_name])} samples")
    
    # Save manifest
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    logger.info(f"Manifest saved: {manifest_path}")
    
    # Create class mapping
    class_map = {name: idx for idx, name in enumerate(EMOTION_CLASSES)}
    class_map_path = output_dir / "class_map.json"
    with open(class_map_path, 'w') as f:
        json.dump(class_map, f, indent=2)
    
    return output_dir


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Create synthetic dataset")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/synthetic_emotion"),
        help="Output directory"
    )
    parser.add_argument("--n-train", type=int, default=50, help="Train samples per class")
    parser.add_argument("--n-val", type=int, default=10, help="Val samples per class")
    parser.add_argument("--n-test", type=int, default=10, help="Test samples per class")
    
    args = parser.parse_args()
    
    create_synthetic_dataset(
        args.output_dir,
        n_train=args.n_train,
        n_val=args.n_val,
        n_test=args.n_test,
    )
    
    print(f"\nSynthetic dataset created: {args.output_dir}")


if __name__ == "__main__":
    main()
```

### Step 2.2: Create Test Training Config

Create `trainer/fer_finetune/specs/test_synthetic.yaml`:

```yaml
# Test configuration for synthetic data
# Used for E2E pipeline testing

model:
  backbone: resnet50
  num_classes: 8
  dropout_rate: 0.3
  pretrained_weights: null  # Use ImageNet
  use_multi_task: false

data:
  train_dir: data/synthetic_emotion/train
  val_dir: data/synthetic_emotion/val
  test_dir: data/synthetic_emotion/test
  image_size: 224
  batch_size: 16
  num_workers: 2

training:
  epochs: 3  # Short for testing
  learning_rate: 0.001
  weight_decay: 0.0001
  label_smoothing: 0.1
  
  # Two-phase training
  freeze_epochs: 1
  unfreeze_layers: ["layer4", "fc"]
  
  # Mixed precision
  use_amp: true
  
  # Augmentation
  use_mixup: false  # Disable for testing
  mixup_alpha: 0.2

scheduler:
  type: cosine
  warmup_epochs: 0
  min_lr: 0.00001

early_stopping:
  patience: 5
  min_delta: 0.001

quality_gates:
  macro_f1: 0.0  # Disabled for synthetic data
  balanced_accuracy: 0.0
  ece: 1.0
  brier: 1.0

output:
  checkpoint_dir: outputs/test_run
  save_best_only: true
  export_onnx: true
```

### Step 2.3: Run Training E2E Test

```bash
# Create synthetic dataset
python trainer/create_synthetic_dataset.py --n-train 50 --n-val 10 --n-test 10

# Run training
python trainer/train_efficientnet.py --config fer_finetune/specs/test_synthetic.yaml --run-id test_e2e

# Verify outputs
ls outputs/test_run/
```

### Step 2.4: Verify Training Outputs

Check that training produces:
- [ ] Checkpoint files (`.pt`)
- [ ] Training logs
- [ ] Validation metrics
- [ ] ONNX export (if enabled)

### Checkpoint: Day 2 Complete
- [ ] Synthetic dataset created
- [ ] Test config created
- [ ] Training runs without errors
- [ ] Outputs verified

---

## Day 3: Gate A Validation Integration

### Step 3.1: Create Gate A Validator

Create `trainer/gate_a_validator.py`:

```python
#!/usr/bin/env python3
"""
Gate A Validation for trained emotion models.

Validates that a trained model meets Gate A requirements:
- Macro F1 ≥ 0.84
- Balanced Accuracy ≥ 0.85
- Per-class F1 ≥ 0.75 (no class < 0.70)
- ECE ≤ 0.08
- Brier ≤ 0.16
"""

import torch
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
import json
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "stats" / "scripts"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GateAResult:
    """Result of Gate A validation."""
    passed: bool
    metrics: Dict[str, float]
    gates: Dict[str, bool]
    failures: list
    recommendations: list


# Gate A thresholds from requirements.md
GATE_A_THRESHOLDS = {
    "macro_f1": 0.84,
    "balanced_accuracy": 0.85,
    "per_class_f1_min": 0.75,
    "per_class_f1_floor": 0.70,
    "ece": 0.08,
    "brier": 0.16,
}


def validate_gate_a(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: Optional[np.ndarray] = None,
    class_names: Optional[list] = None,
) -> GateAResult:
    """
    Validate model predictions against Gate A requirements.
    
    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        y_proba: Predicted probabilities (optional, for calibration)
        class_names: Class names for reporting
    
    Returns:
        GateAResult with pass/fail status and details
    """
    from sklearn.metrics import (
        f1_score, balanced_accuracy_score, accuracy_score
    )
    
    metrics = {}
    gates = {}
    failures = []
    recommendations = []
    
    # Macro F1
    macro_f1 = f1_score(y_true, y_pred, average='macro', zero_division=0)
    metrics["macro_f1"] = macro_f1
    gates["macro_f1"] = macro_f1 >= GATE_A_THRESHOLDS["macro_f1"]
    if not gates["macro_f1"]:
        failures.append(f"Macro F1 {macro_f1:.4f} < {GATE_A_THRESHOLDS['macro_f1']}")
        recommendations.append("Increase training data or adjust class weights")
    
    # Balanced Accuracy
    bal_acc = balanced_accuracy_score(y_true, y_pred)
    metrics["balanced_accuracy"] = bal_acc
    gates["balanced_accuracy"] = bal_acc >= GATE_A_THRESHOLDS["balanced_accuracy"]
    if not gates["balanced_accuracy"]:
        failures.append(f"Balanced Accuracy {bal_acc:.4f} < {GATE_A_THRESHOLDS['balanced_accuracy']}")
        recommendations.append("Address class imbalance in training data")
    
    # Per-class F1
    per_class_f1 = f1_score(y_true, y_pred, average=None, zero_division=0)
    metrics["per_class_f1"] = per_class_f1.tolist()
    
    min_f1 = per_class_f1.min()
    metrics["min_class_f1"] = min_f1
    
    gates["per_class_f1_min"] = min_f1 >= GATE_A_THRESHOLDS["per_class_f1_min"]
    gates["per_class_f1_floor"] = min_f1 >= GATE_A_THRESHOLDS["per_class_f1_floor"]
    
    if not gates["per_class_f1_floor"]:
        weak_classes = np.where(per_class_f1 < GATE_A_THRESHOLDS["per_class_f1_floor"])[0]
        class_names = class_names or [f"class_{i}" for i in range(len(per_class_f1))]
        weak_names = [class_names[i] for i in weak_classes]
        failures.append(f"Classes below floor ({GATE_A_THRESHOLDS['per_class_f1_floor']}): {weak_names}")
        recommendations.append(f"Add more training data for: {', '.join(weak_names)}")
    
    # Calibration metrics (if probabilities provided)
    if y_proba is not None:
        try:
            from quality_gate_metrics import compute_ece, compute_brier_score
            
            ece = compute_ece(y_true, y_proba)
            brier = compute_brier_score(y_true, y_proba)
            
            metrics["ece"] = ece
            metrics["brier"] = brier
            
            gates["ece"] = ece <= GATE_A_THRESHOLDS["ece"]
            gates["brier"] = brier <= GATE_A_THRESHOLDS["brier"]
            
            if not gates["ece"]:
                failures.append(f"ECE {ece:.4f} > {GATE_A_THRESHOLDS['ece']}")
                recommendations.append("Apply temperature scaling for calibration")
            
            if not gates["brier"]:
                failures.append(f"Brier {brier:.4f} > {GATE_A_THRESHOLDS['brier']}")
        except ImportError:
            logger.warning("Calibration metrics not available")
    
    # Overall pass/fail
    passed = all(gates.values())
    
    return GateAResult(
        passed=passed,
        metrics=metrics,
        gates=gates,
        failures=failures,
        recommendations=recommendations,
    )


def validate_checkpoint(
    checkpoint_path: Path,
    test_loader,
    device: str = "cuda",
    class_names: Optional[list] = None,
) -> GateAResult:
    """
    Validate a saved checkpoint against Gate A.
    
    Args:
        checkpoint_path: Path to model checkpoint
        test_loader: DataLoader for test data
        device: Device to run inference on
        class_names: Class names for reporting
    
    Returns:
        GateAResult
    """
    from fer_finetune.model import EmotionClassifier
    
    # Load model
    checkpoint = torch.load(checkpoint_path, map_location=device)
    
    config = checkpoint.get('config', {})
    model = EmotionClassifier(
        backbone=config.get('backbone', 'resnet50'),
        num_classes=config.get('num_classes', 8),
    )
    model.load_state_dict(checkpoint['model_state_dict'])
    model.to(device)
    model.eval()
    
    # Run inference
    all_preds = []
    all_labels = []
    all_probs = []
    
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            outputs = model(images)
            probs = torch.softmax(outputs, dim=1)
            preds = outputs.argmax(dim=1)
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probs.cpu().numpy())
    
    y_true = np.array(all_labels)
    y_pred = np.array(all_preds)
    y_proba = np.array(all_probs)
    
    return validate_gate_a(y_true, y_pred, y_proba, class_names)


def print_gate_a_report(result: GateAResult):
    """Print Gate A validation report."""
    print("\n" + "=" * 60)
    print("GATE A VALIDATION REPORT")
    print("=" * 60)
    
    status = "✅ PASSED" if result.passed else "❌ FAILED"
    print(f"\nOverall Status: {status}")
    
    print("\n--- Metrics ---")
    for name, value in result.metrics.items():
        if isinstance(value, list):
            print(f"  {name}: {[f'{v:.4f}' for v in value]}")
        else:
            print(f"  {name}: {value:.4f}")
    
    print("\n--- Gate Results ---")
    for gate, passed in result.gates.items():
        status = "✅" if passed else "❌"
        threshold = GATE_A_THRESHOLDS.get(gate, "N/A")
        print(f"  {status} {gate}: threshold={threshold}")
    
    if result.failures:
        print("\n--- Failures ---")
        for failure in result.failures:
            print(f"  ❌ {failure}")
    
    if result.recommendations:
        print("\n--- Recommendations ---")
        for rec in result.recommendations:
            print(f"  → {rec}")
    
    print("=" * 60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Gate A Validation")
    parser.add_argument("--checkpoint", type=Path, required=True, help="Model checkpoint")
    parser.add_argument("--test-dir", type=Path, required=True, help="Test data directory")
    parser.add_argument("--device", default="cuda", help="Device")
    
    args = parser.parse_args()
    
    # Create test loader
    from fer_finetune.dataset import create_dataloaders
    
    _, _, test_loader = create_dataloaders(
        train_dir=None,
        val_dir=None,
        test_dir=args.test_dir,
        batch_size=32,
    )
    
    result = validate_checkpoint(
        args.checkpoint,
        test_loader,
        device=args.device,
    )
    
    print_gate_a_report(result)
    
    # Exit with appropriate code
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
```

### Step 3.2: Integrate Gate A into Training

Update `trainer/fer_finetune/train.py` to run Gate A validation after training:

```python
# At the end of training:
def run_gate_a_validation(self, test_loader) -> bool:
    """Run Gate A validation on test set."""
    from gate_a_validator import validate_gate_a, print_gate_a_report
    
    logger.info("Running Gate A validation...")
    
    self.model.eval()
    all_preds, all_labels, all_probs = [], [], []
    
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(self.device)
            outputs = self.model(images)
            probs = torch.softmax(outputs, dim=1)
            preds = outputs.argmax(dim=1)
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probs.cpu().numpy())
    
    result = validate_gate_a(
        np.array(all_labels),
        np.array(all_preds),
        np.array(all_probs),
        class_names=self.config.class_names,
    )
    
    print_gate_a_report(result)
    
    # Log to MLflow
    if self.mlflow_enabled:
        mlflow.log_metric("gate_a_passed", 1 if result.passed else 0)
        for name, value in result.metrics.items():
            if not isinstance(value, list):
                mlflow.log_metric(f"gate_a_{name}", value)
    
    return result.passed
```

### Step 3.3: Test Gate A Integration

```bash
# Run training with Gate A validation
python trainer/train_efficientnet.py \
    --config fer_finetune/specs/test_synthetic.yaml \
    --run-id test_gate_a

# Manually run Gate A on checkpoint
python trainer/gate_a_validator.py \
    --checkpoint outputs/test_run/best_model.pt \
    --test-dir data/synthetic_emotion/test
```

### Checkpoint: Day 3 Complete
- [ ] Gate A validator created
- [ ] Integrated into training pipeline
- [ ] Gate A runs after training

---

## Day 4: Wire Stats Scripts to Post-Training

### Step 4.1: Create Post-Training Analysis Script

Create `trainer/post_training_analysis.py`:

```python
#!/usr/bin/env python3
"""
Post-training statistical analysis.

Runs full statistical analysis after training completes:
1. Quality gate metrics on test set
2. Comparison with baseline (if available)
3. Per-class analysis
"""

import sys
from pathlib import Path
import json
import numpy as np
import torch
import logging

# Add stats scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "stats" / "scripts"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_post_training_analysis(
    checkpoint_path: Path,
    test_dir: Path,
    baseline_checkpoint: Path = None,
    output_dir: Path = None,
    device: str = "cuda",
):
    """
    Run complete post-training statistical analysis.
    
    Args:
        checkpoint_path: Path to trained model checkpoint
        test_dir: Test data directory
        baseline_checkpoint: Optional baseline model for comparison
        output_dir: Output directory for results
        device: Device for inference
    """
    from fer_finetune.model import EmotionClassifier
    from fer_finetune.dataset import create_dataloaders
    
    output_dir = output_dir or checkpoint_path.parent / "stats_analysis"
    output_dir.mkdir(exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("POST-TRAINING STATISTICAL ANALYSIS")
    logger.info("=" * 60)
    
    # Load test data
    _, _, test_loader = create_dataloaders(
        train_dir=None, val_dir=None, test_dir=test_dir, batch_size=32
    )
    
    # Get predictions from trained model
    logger.info("Running inference on test set...")
    y_true, y_pred, y_proba = get_predictions(checkpoint_path, test_loader, device)
    
    # Save predictions for stats scripts
    np.savez(
        output_dir / "predictions.npz",
        y_true=y_true,
        y_pred=y_pred,
        y_proba=y_proba,
    )
    
    # Run quality gate analysis
    logger.info("\n--- Quality Gate Analysis ---")
    from quality_gate_metrics import compute_all_metrics, print_report, save_report
    
    report = compute_all_metrics(y_true, y_pred, y_proba)
    print_report(report)
    save_report(report, output_dir / "quality_gate_metrics.json")
    
    # If baseline provided, run comparison
    if baseline_checkpoint and baseline_checkpoint.exists():
        logger.info("\n--- Model Comparison (Stuart-Maxwell) ---")
        
        base_true, base_pred, _ = get_predictions(baseline_checkpoint, test_loader, device)
        
        # Save paired predictions
        np.savez(
            output_dir / "paired_predictions.npz",
            base_preds=base_pred,
            finetuned_preds=y_pred,
        )
        
        from stuart_maxwell_test import stuart_maxwell_test, print_report as print_sm
        
        sm_result = stuart_maxwell_test(base_pred, y_pred)
        print_sm(sm_result)
    
    logger.info(f"\nResults saved to: {output_dir}")
    
    return report


def get_predictions(checkpoint_path, test_loader, device):
    """Get predictions from a checkpoint."""
    from fer_finetune.model import EmotionClassifier
    
    checkpoint = torch.load(checkpoint_path, map_location=device)
    config = checkpoint.get('config', {})
    
    model = EmotionClassifier(
        backbone=config.get('backbone', 'resnet50'),
        num_classes=config.get('num_classes', 8),
    )
    model.load_state_dict(checkpoint['model_state_dict'])
    model.to(device)
    model.eval()
    
    all_preds, all_labels, all_probs = [], [], []
    
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            outputs = model(images)
            probs = torch.softmax(outputs, dim=1)
            preds = outputs.argmax(dim=1)
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probs.cpu().numpy())
    
    return np.array(all_labels), np.array(all_preds), np.array(all_probs)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Post-training analysis")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--test-dir", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--device", default="cuda")
    
    args = parser.parse_args()
    
    run_post_training_analysis(
        args.checkpoint,
        args.test_dir,
        args.baseline,
        args.output_dir,
        args.device,
    )


if __name__ == "__main__":
    main()
```

### Step 4.2: Test Post-Training Analysis

```bash
python trainer/post_training_analysis.py \
    --checkpoint outputs/test_run/best_model.pt \
    --test-dir data/synthetic_emotion/test \
    --output-dir outputs/test_run/stats
```

### Checkpoint: Day 4 Complete
- [ ] Post-training analysis script created
- [ ] Integrates with stats scripts
- [ ] Outputs saved correctly

---

## Day 5: Documentation & Final Testing

### Step 5.1: Update Training Documentation

Create `trainer/README.md` with usage instructions.

### Step 5.2: Run Full Pipeline Test

```bash
# 1. Create synthetic data
python trainer/create_synthetic_dataset.py

# 2. Download weights (or use ImageNet)
python trainer/download_pretrained_weights.py --source imagenet

# 3. Run training
python trainer/train_efficientnet.py \
    --config fer_finetune/specs/test_synthetic.yaml \
    --run-id week2_final_test

# 4. Run post-training analysis
python trainer/post_training_analysis.py \
    --checkpoint outputs/week2_final_test/best_model.pt \
    --test-dir data/synthetic_emotion/test

# 5. Verify all outputs
ls outputs/week2_final_test/
```

### Checkpoint: Day 5 Complete
- [ ] Full pipeline tested
- [ ] Documentation updated
- [ ] All outputs verified

---

## Week 2 Deliverables Summary

| Deliverable | Status | Location |
|-------------|--------|----------|
| Weights download script | ✅ | `trainer/download_pretrained_weights.py` |
| Synthetic dataset generator | ✅ | `trainer/create_synthetic_dataset.py` |
| Gate A validator | ✅ | `trainer/gate_a_validator.py` |
| Post-training analysis | ✅ | `trainer/post_training_analysis.py` |
| E2E pipeline tested | ✅ | `outputs/` |

---

## Next Steps

Proceed to [Week 3: n8n Workflow Testing](WEEK_03_N8N_WORKFLOW_TESTING.md).
