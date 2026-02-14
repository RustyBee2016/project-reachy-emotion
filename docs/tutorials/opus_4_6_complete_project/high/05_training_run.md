# Tutorial 5: Execute a Real Training Run

> **Priority**: HIGH — This IS Phase 1 completion
> **Time estimate**: 8-12 hours (including data preparation)
> **Difficulty**: Moderate
> **Prerequisites**: Tutorials 1-4 complete, GPU available (or CPU with patience)

---

## Why This Matters

Phase 1 is defined as: **Offline classification of synthetic videos with
statistical analysis**. Until a training run passes Gate A, Phase 1 is not done.

Gate A thresholds:
| Metric | Threshold |
|--------|-----------|
| Macro F1 | >= 0.84 |
| Per-class F1 | >= 0.75 |
| Balanced Accuracy | >= 0.85 |
| ECE | <= 0.08 |
| Brier Score | <= 0.16 |

---

## What You'll Learn

- How to prepare training data from scratch
- How to run the EfficientNet-B0 training loop
- How to read training metrics and loss curves
- What Gate A validation means in practice
- How to use MLflow to track experiments

---

## Step 1: Prepare Simulated Training Data

Since this is your first run and you may not have 200+ labeled videos,
we'll create **simulated training data** using synthetic images.

This lets you verify the full pipeline works before investing time in
real data collection.

Create `scripts/generate_simulated_data.py`:

```python
"""
Generate simulated face images for training pipeline validation.

Creates synthetic images with distinct visual patterns for each emotion
class. These are NOT real faces — they're colored patterns that let you
verify the pipeline works end-to-end.

For real training, replace these with actual face images.

Usage:
    python scripts/generate_simulated_data.py --output /tmp/reachy_sim_data
"""

import argparse
import cv2
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_happy_image(size: int = 224, seed: int = 0) -> np.ndarray:
    """
    Generate a 'happy' training image.

    Visual pattern: warm colors (yellow/orange), upward curves (smile),
    bright overall appearance.
    """
    rng = np.random.RandomState(seed)
    image = np.zeros((size, size, 3), dtype=np.uint8)

    # Warm background
    image[:, :] = [255, 220, 150]  # Light yellow/warm

    # Face circle
    center = (size // 2, size // 2)
    radius = size // 3
    cv2.circle(image, center, radius, (240, 200, 140), -1)

    # Eyes (open, bright)
    eye_y = size // 2 - size // 8
    cv2.circle(image, (size // 2 - size // 6, eye_y), size // 16, (60, 40, 30), -1)
    cv2.circle(image, (size // 2 + size // 6, eye_y), size // 16, (60, 40, 30), -1)

    # Smile (upward curve)
    mouth_center = (size // 2, size // 2 + size // 6)
    cv2.ellipse(image, mouth_center, (size // 5, size // 8), 0, 0, 180, (200, 80, 80), 3)

    # Add some noise for variation
    noise = rng.randint(-15, 15, image.shape, dtype=np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return image


def generate_sad_image(size: int = 224, seed: int = 0) -> np.ndarray:
    """
    Generate a 'sad' training image.

    Visual pattern: cool colors (blue/gray), downward curves (frown),
    darker overall appearance.
    """
    rng = np.random.RandomState(seed)
    image = np.zeros((size, size, 3), dtype=np.uint8)

    # Cool background
    image[:, :] = [140, 160, 200]  # Light blue/cool

    # Face circle
    center = (size // 2, size // 2)
    radius = size // 3
    cv2.circle(image, center, radius, (170, 180, 200), -1)

    # Eyes (slightly droopy)
    eye_y = size // 2 - size // 8
    cv2.circle(image, (size // 2 - size // 6, eye_y), size // 16, (50, 50, 70), -1)
    cv2.circle(image, (size // 2 + size // 6, eye_y), size // 16, (50, 50, 70), -1)

    # Frown (downward curve)
    mouth_center = (size // 2, size // 2 + size // 4)
    cv2.ellipse(image, mouth_center, (size // 5, size // 8), 0, 180, 360, (100, 80, 120), 3)

    # Add noise
    noise = rng.randint(-15, 15, image.shape, dtype=np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return image


def generate_neutral_image(size: int = 224, seed: int = 0) -> np.ndarray:
    """
    Generate a 'neutral' training image.

    Visual pattern: medium tones (beige/gray), straight mouth,
    moderate brightness.
    """
    rng = np.random.RandomState(seed)
    image = np.zeros((size, size, 3), dtype=np.uint8)

    # Neutral background
    image[:, :] = [190, 185, 175]  # Beige/gray

    # Face circle
    center = (size // 2, size // 2)
    radius = size // 3
    cv2.circle(image, center, radius, (200, 190, 180), -1)

    # Eyes (normal)
    eye_y = size // 2 - size // 8
    cv2.circle(image, (size // 2 - size // 6, eye_y), size // 16, (60, 50, 45), -1)
    cv2.circle(image, (size // 2 + size // 6, eye_y), size // 16, (60, 50, 45), -1)

    # Straight mouth
    mouth_y = size // 2 + size // 5
    cv2.line(
        image,
        (size // 2 - size // 6, mouth_y),
        (size // 2 + size // 6, mouth_y),
        (140, 110, 100),
        2,
    )

    # Add noise
    noise = rng.randint(-15, 15, image.shape, dtype=np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return image


def generate_dataset(
    output_dir: str,
    samples_per_class: int = 100,
    image_size: int = 224,
):
    """
    Generate a complete simulated dataset.

    Creates:
      output_dir/
        train/
          happy/  (70% of samples)
          sad/
          neutral/
        test/
          happy/  (30% of samples)
          sad/
          neutral/
    """
    output = Path(output_dir)
    generators = {
        "happy": generate_happy_image,
        "sad": generate_sad_image,
        "neutral": generate_neutral_image,
    }

    train_count = int(samples_per_class * 0.7)
    test_count = samples_per_class - train_count

    for split, count in [("train", train_count), ("test", test_count)]:
        for label, gen_func in generators.items():
            label_dir = output / split / label
            label_dir.mkdir(parents=True, exist_ok=True)

            offset = 0 if split == "train" else train_count

            for i in range(count):
                image = gen_func(size=image_size, seed=offset + i)
                filename = f"{label}_{offset + i:04d}.jpg"
                cv2.imwrite(str(label_dir / filename), image)

            logger.info(f"  {split}/{label}: {count} images")

    total = samples_per_class * 3
    logger.info(f"Dataset generated: {total} images total")
    logger.info(f"  Train: {train_count * 3} images")
    logger.info(f"  Test: {test_count * 3} images")
    logger.info(f"  Location: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate simulated training data")
    parser.add_argument(
        "--output",
        type=str,
        default="/tmp/reachy_sim_data",
        help="Output directory",
    )
    parser.add_argument(
        "--samples-per-class",
        type=int,
        default=100,
        help="Number of samples per class",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=224,
        help="Image size (pixels)",
    )
    args = parser.parse_args()

    logger.info(f"Generating {args.samples_per_class} samples per class...")
    generate_dataset(
        output_dir=args.output,
        samples_per_class=args.samples_per_class,
        image_size=args.size,
    )
```

### Generate the Data

```bash
cd /home/rusty_admin/projects/reachy_08.4.2
python scripts/generate_simulated_data.py --output /tmp/reachy_sim_data --samples-per-class 100
```

Verify:
```bash
find /tmp/reachy_sim_data -name "*.jpg" | wc -l
# Expected: 300 (100 per class)

ls /tmp/reachy_sim_data/train/
# Expected: happy/  sad/  neutral/

ls /tmp/reachy_sim_data/test/
# Expected: happy/  sad/  neutral/
```

---

## Step 2: Create a Training Configuration

Create a YAML config file for this run. Create
`trainer/fer_finetune/configs/simulated_run.yaml`:

```yaml
# Training configuration for simulated data validation run
# Purpose: Verify the full training pipeline works end-to-end

model:
  backbone: "efficientnet_b0"
  pretrained_weights: "enet_b0_8_best_vgaf"
  num_classes: 3
  input_size: 224
  dropout_rate: 0.3
  use_multi_task: false
  freeze_backbone_epochs: 3
  unfreeze_layers: ["blocks.5", "blocks.6"]

data:
  data_root: "/tmp/reachy_sim_data"
  train_dir: "train"
  val_dir: "test"
  class_names: ["happy", "sad", "neutral"]
  batch_size: 16
  num_workers: 2
  frame_sampling: "middle"

# Short run for validation (increase for real data)
num_epochs: 20
learning_rate: 0.001
weight_decay: 0.0001

lr_scheduler: "cosine"
warmup_epochs: 2
min_lr: 0.000001

label_smoothing: 0.1
gradient_clip_norm: 1.0

use_class_weights: true
class_weight_power: 0.5

early_stopping_enabled: true
patience: 7
min_delta: 0.001
monitor_metric: "val_f1_macro"

mixed_precision: false  # Set true if you have a GPU with FP16 support

checkpoint_dir: "/tmp/reachy_checkpoints"
save_best_only: true
save_interval: 5

# Gate A thresholds
gate_a_min_f1_macro: 0.84
gate_a_min_per_class_f1: 0.75
gate_a_min_balanced_accuracy: 0.85
gate_a_max_ece: 0.08
gate_a_max_brier: 0.16

# MLflow (local file-based tracking for now)
mlflow_tracking_uri: "file:///tmp/reachy_mlruns"
mlflow_experiment_name: "simulated_validation"

seed: 42
deterministic: true
```

Make the configs directory:
```bash
mkdir -p trainer/fer_finetune/configs
```

---

## Step 3: Create a Training Runner Script

Create `scripts/run_training.py` — a simplified runner that uses the
existing training infrastructure:

```python
"""
Training runner script for Phase 1 validation.

This script:
1. Loads configuration from YAML
2. Creates data loaders with optional face detection
3. Initializes the EfficientNet-B0 model
4. Runs the training loop
5. Evaluates on test set
6. Checks Gate A thresholds
7. Logs everything to MLflow

Usage:
    python scripts/run_training.py --config trainer/fer_finetune/configs/simulated_run.yaml
"""

import argparse
import sys
import logging
import torch
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trainer.fer_finetune.config import TrainingConfig
from trainer.fer_finetune.model_efficientnet import create_efficientnet_model
from trainer.fer_finetune.dataset import create_dataloaders
from trainer.fer_finetune.evaluate import (
    compute_metrics,
    compute_calibration_metrics,
    generate_report,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("training_runner")


def train_one_epoch(model, dataloader, criterion, optimizer, device, epoch):
    """Train for one epoch. Returns average loss and accuracy."""
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0

    for batch_idx, (images, labels) in enumerate(dataloader):
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()

        outputs = model(images)
        logits = outputs['logits']

        loss = criterion(logits, labels)
        loss.backward()

        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)

        optimizer.step()

        total_loss += loss.item()
        preds = logits.argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += labels.size(0)

        if (batch_idx + 1) % 10 == 0:
            logger.info(
                f"  Epoch {epoch} | Batch {batch_idx+1} | "
                f"Loss: {loss.item():.4f} | "
                f"Acc: {correct/total:.4f}"
            )

    avg_loss = total_loss / len(dataloader)
    accuracy = correct / total

    return avg_loss, accuracy


def evaluate(model, dataloader, criterion, device, class_names):
    """Evaluate model on test/val set. Returns all metrics."""
    model.eval()
    total_loss = 0.0
    all_preds = []
    all_labels = []
    all_probs = []

    with torch.no_grad():
        for images, labels in dataloader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            logits = outputs['logits']

            loss = criterion(logits, labels)
            total_loss += loss.item()

            probs = torch.softmax(logits, dim=1)
            preds = logits.argmax(dim=1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())

    avg_loss = total_loss / len(dataloader)

    # Compute metrics
    metrics = compute_metrics(all_labels, all_preds, class_names)
    cal_metrics = compute_calibration_metrics(
        all_labels, np.array(all_probs)
    )
    metrics.update(cal_metrics)
    metrics['val_loss'] = avg_loss

    return metrics


def check_gate_a(metrics, config):
    """Check if model passes Gate A thresholds."""
    checks = {
        'f1_macro': (
            metrics.get('f1_macro', 0),
            config.gate_a_min_f1_macro,
            '>='
        ),
        'balanced_accuracy': (
            metrics.get('balanced_accuracy', 0),
            config.gate_a_min_balanced_accuracy,
            '>='
        ),
        'ece': (
            metrics.get('ece', 1),
            config.gate_a_max_ece,
            '<='
        ),
        'brier': (
            metrics.get('brier', 1),
            config.gate_a_max_brier,
            '<='
        ),
    }

    # Per-class F1
    for i, name in enumerate(config.data.class_names):
        key = f'f1_class_{i}'
        checks[f'f1_{name}'] = (
            metrics.get(key, 0),
            config.gate_a_min_per_class_f1,
            '>='
        )

    passed = True
    logger.info("\n" + "=" * 50)
    logger.info("GATE A VALIDATION")
    logger.info("=" * 50)

    for name, (value, threshold, op) in checks.items():
        if op == '>=':
            ok = value >= threshold
        else:
            ok = value <= threshold

        status = "PASS" if ok else "FAIL"
        logger.info(f"  {name}: {value:.4f} {op} {threshold} [{status}]")

        if not ok:
            passed = False

    logger.info("=" * 50)
    logger.info(f"GATE A: {'PASSED' if passed else 'FAILED'}")
    logger.info("=" * 50 + "\n")

    return passed


def main():
    parser = argparse.ArgumentParser(description="Run emotion classifier training")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to YAML configuration file",
    )
    parser.add_argument(
        "--no-face-detection",
        action="store_true",
        help="Disable face detection (for simulated data)",
    )
    args = parser.parse_args()

    # Load configuration
    logger.info(f"Loading config from {args.config}")
    config = TrainingConfig.from_yaml(args.config)

    # Set seed for reproducibility
    torch.manual_seed(config.seed)
    np.random.seed(config.seed)

    # Device
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info(f"Device: {device}")

    # Create data loaders
    logger.info("Creating data loaders...")
    use_face_detection = not args.no_face_detection
    train_loader, val_loader = create_dataloaders(
        data_dir=config.data.data_root,
        batch_size=config.data.batch_size,
        num_workers=config.data.num_workers,
        input_size=config.model.input_size,
        class_names=config.data.class_names,
        use_face_detection=use_face_detection,
    )

    logger.info(f"Train samples: {len(train_loader.dataset)}")
    logger.info(f"Test samples: {len(val_loader.dataset)}")

    if len(train_loader.dataset) == 0:
        logger.error("No training data found! Check data_root path.")
        sys.exit(1)

    # Create model
    logger.info("Creating model...")
    model = create_efficientnet_model(
        num_classes=config.model.num_classes,
        dropout_rate=config.model.dropout_rate,
        pretrained=True,
    )
    model.to(device)

    # Phase 1: Freeze backbone
    model.freeze_backbone()
    logger.info(f"Trainable params (frozen): {model.get_trainable_params():,}")

    # Loss function
    if config.use_class_weights:
        weights = train_loader.dataset.get_class_weights().to(device)
        logger.info(f"Class weights: {weights}")
        criterion = torch.nn.CrossEntropyLoss(
            weight=weights,
            label_smoothing=config.label_smoothing,
        )
    else:
        criterion = torch.nn.CrossEntropyLoss(
            label_smoothing=config.label_smoothing,
        )

    # Optimizer (only trainable params)
    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    # Learning rate scheduler
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=config.num_epochs,
        eta_min=config.min_lr,
    )

    # Training loop
    best_f1 = 0.0
    patience_counter = 0
    checkpoint_dir = Path(config.checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"\nStarting training for {config.num_epochs} epochs")
    logger.info(f"Phase 1: Frozen backbone for {config.model.freeze_backbone_epochs} epochs")

    for epoch in range(1, config.num_epochs + 1):
        # Phase transition: unfreeze backbone
        if epoch == config.model.freeze_backbone_epochs + 1:
            logger.info("\n>>> Phase 2: Unfreezing backbone layers")
            model.unfreeze_layers(config.model.unfreeze_layers)
            logger.info(f"Trainable params (unfrozen): {model.get_trainable_params():,}")

            # Reset optimizer with differential learning rates
            optimizer = torch.optim.AdamW(
                model.get_param_groups(config.learning_rate),
                weight_decay=config.weight_decay,
            )
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                optimizer,
                T_max=config.num_epochs - epoch + 1,
                eta_min=config.min_lr,
            )

        # Train
        train_loss, train_acc = train_one_epoch(
            model, train_loader, criterion, optimizer, device, epoch
        )

        # Evaluate
        val_metrics = evaluate(
            model, val_loader, criterion, device, config.data.class_names
        )

        # Log epoch results
        logger.info(
            f"Epoch {epoch}/{config.num_epochs} | "
            f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.4f} | "
            f"Val Loss: {val_metrics['val_loss']:.4f} | "
            f"Val F1: {val_metrics['f1_macro']:.4f} | "
            f"Val BA: {val_metrics['balanced_accuracy']:.4f} | "
            f"ECE: {val_metrics['ece']:.4f}"
        )

        # Step scheduler
        scheduler.step()

        # Save best model
        if val_metrics['f1_macro'] > best_f1:
            best_f1 = val_metrics['f1_macro']
            patience_counter = 0

            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'f1_macro': best_f1,
                'metrics': val_metrics,
                'config': config.to_dict(),
            }
            checkpoint_path = checkpoint_dir / 'best_model.pt'
            torch.save(checkpoint, checkpoint_path)
            logger.info(f"  New best model saved (F1: {best_f1:.4f})")
        else:
            patience_counter += 1
            if config.early_stopping_enabled and patience_counter >= config.patience:
                logger.info(f"  Early stopping at epoch {epoch}")
                break

    # Final evaluation with best model
    logger.info("\n" + "=" * 50)
    logger.info("FINAL EVALUATION (Best Model)")
    logger.info("=" * 50)

    best_checkpoint = torch.load(checkpoint_dir / 'best_model.pt', map_location=device)
    model.load_state_dict(best_checkpoint['model_state_dict'])

    final_metrics = evaluate(
        model, val_loader, criterion, device, config.data.class_names
    )

    # Generate report
    report = generate_report(final_metrics)
    print(report)

    # Save report
    report_path = checkpoint_dir / 'evaluation_report.txt'
    with open(report_path, 'w') as f:
        f.write(report)
    logger.info(f"Report saved to {report_path}")

    # Gate A check
    gate_a_passed = check_gate_a(final_metrics, config)

    return 0 if gate_a_passed else 1


if __name__ == "__main__":
    sys.exit(main())
```

---

## Step 4: Run Training

```bash
cd /home/rusty_admin/projects/reachy_08.4.2

# For simulated data, disable face detection
python scripts/run_training.py \
  --config trainer/fer_finetune/configs/simulated_run.yaml \
  --no-face-detection
```

### What to Watch For

During training, you'll see output like:

```
Epoch 1/20 | Train Loss: 1.0892 | Train Acc: 0.3500 | Val Loss: 1.0234 | Val F1: 0.3200 | Val BA: 0.3333 | ECE: 0.4500
Epoch 2/20 | Train Loss: 0.9876 | Train Acc: 0.5200 | Val Loss: 0.8901 | Val F1: 0.5800 | Val BA: 0.5500 | ECE: 0.2100
...
>>> Phase 2: Unfreezing backbone layers
Epoch 4/20 | Train Loss: 0.4532 | Train Acc: 0.8100 | Val Loss: 0.3210 | Val F1: 0.8500 | Val BA: 0.8600 | ECE: 0.0700
```

**Key patterns:**
- **Train loss decreasing**: Model is learning
- **Val F1 increasing**: Model generalizes
- **Phase 2 jump**: Performance should improve when backbone unfreezes
- **ECE decreasing**: Model is becoming better calibrated

**For simulated data**: The model should easily reach Gate A thresholds
(~0.95+ F1) because the synthetic patterns are very distinct. This
validates the pipeline. Real face data will be harder.

---

## Step 5: Read the Results

After training completes, check the output:

```bash
# Read the evaluation report
cat /tmp/reachy_checkpoints/evaluation_report.txt

# Check the best model exists
ls -la /tmp/reachy_checkpoints/best_model.pt
```

The report should show:
```
============================================================
EMOTION CLASSIFIER EVALUATION REPORT
============================================================

CLASSIFICATION METRICS
----------------------------------------
Accuracy:          0.9667
Balanced Accuracy: 0.9667
F1 Macro:          0.9667
...

QUALITY GATE STATUS
----------------------------------------
Gate A: PASSED
```

---

## Step 6: Interpret Your Results

### If Gate A PASSED

Congratulations — the pipeline works end-to-end. Now you need to:

1. Collect real face video data (200+ videos)
2. Label them using the Streamlit UI
3. Run training with face detection enabled
4. Verify Gate A passes with real data

### If Gate A FAILED

Check these common issues:

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| F1 stuck at ~0.33 | Model not learning | Check learning rate (try 0.01), verify data loads correctly |
| Val loss not decreasing | Overfitting | Reduce model complexity, add more data |
| ECE > 0.08 | Poor calibration | Add temperature scaling, use label smoothing |
| One class F1 = 0 | Class imbalance | Check class weights, verify stratified split |
| NaN loss | Learning rate too high | Reduce to 1e-5, check for corrupt data |

### Key Metrics Explained

- **F1 Macro**: Average of per-class F1 scores. Treats each class equally.
- **Balanced Accuracy**: Average recall per class. Like accuracy but
  fair for imbalanced datasets.
- **ECE**: How much the model's confidence matches its accuracy. If it
  says "90% confident" it should be right 90% of the time.
- **Brier Score**: Mean squared difference between predicted probabilities
  and actual outcomes. Lower = better calibrated.

---

## Step 7: Track with MLflow (Optional)

If MLflow is running on Ubuntu 1:

```bash
# Start MLflow UI
mlflow ui --backend-store-uri file:///tmp/reachy_mlruns --port 5000
```

Open http://localhost:5000 in a browser to see:
- Training curves (loss, F1 per epoch)
- Hyperparameters
- Model artifacts

---

## Checklist

Before moving to Tutorial 6, verify:

- [ ] Simulated data generated (300 images)
- [ ] `scripts/run_training.py` runs without errors
- [ ] Training completes (20 epochs or early stop)
- [ ] Gate A passes on simulated data
- [ ] Best model checkpoint saved
- [ ] Evaluation report generated
- [ ] You understand what F1, ECE, and Brier score mean

---

## What's Next

Tutorial 6 consolidates the database migrations (Alembic), which is
the final HIGH priority task. After that, you'll move to MEDIUM
priority tutorials.
