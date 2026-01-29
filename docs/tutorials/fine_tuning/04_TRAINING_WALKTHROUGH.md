# Guide 04: Training Walkthrough

**Duration**: 3-4 hours  
**Difficulty**: Intermediate  
**Prerequisites**: Guides 01-03 complete, data prepared

---

## Learning Objectives

By the end of this guide, you will:
- [ ] Understand the training configuration file
- [ ] Know how to start training
- [ ] Understand what happens during training
- [ ] Know how to interpret training output
- [ ] Be able to resume training from a checkpoint

---

## 1. Training Configuration

### The Config File

Training is controlled by a YAML configuration file. Let's examine `resnet50_emotion_2cls.yaml`:

```yaml
# trainer/fer_finetune/specs/resnet50_emotion_2cls.yaml

# Model settings
model:
  backbone: resnet50                    # Network architecture
  num_classes: 2                        # happy, sad
  input_size: 224                       # Image size (224x224)
  dropout_rate: 0.3                     # Dropout for regularization
  pretrained_weights: resnet50-affectnet-raf-db  # Pre-trained weights
  freeze_backbone_epochs: 5             # Phase 1 duration
  unfreeze_layers: ["layer4"]           # Layers to unfreeze in Phase 2
  use_multi_task: false                 # Single-task (classification only)

# Data settings
data:
  data_root: data                       # Path to data directory
  batch_size: 32                        # Images per batch
  num_workers: 4                        # Parallel data loading threads
  class_names: ["happy", "sad"]         # Class labels
  mixup_alpha: 0.2                      # Mixup augmentation strength
  mixup_probability: 0.5                # Probability of applying mixup

# Training settings
num_epochs: 20                          # Total training epochs
learning_rate: 0.001                    # Initial learning rate
min_lr: 0.00001                         # Minimum learning rate
weight_decay: 0.01                      # L2 regularization
lr_scheduler: cosine                    # Learning rate schedule
warmup_epochs: 2                        # Warmup period
gradient_clip_norm: 1.0                 # Gradient clipping
label_smoothing: 0.1                    # Label smoothing

# Early stopping
early_stopping_enabled: true
patience: 10                            # Epochs without improvement
min_delta: 0.001                        # Minimum improvement

# Checkpointing
checkpoint_dir: outputs/checkpoints
save_interval: 5                        # Save every N epochs

# Quality gates (Gate A from requirements)
gate_a_min_f1_macro: 0.84
gate_a_min_balanced_accuracy: 0.85
gate_a_min_per_class_f1: 0.70
gate_a_max_ece: 0.08
gate_a_max_brier: 0.16

# Experiment tracking
mlflow_tracking_uri: http://localhost:5000
mlflow_experiment_name: reachy_emotion_2cls

# Reproducibility
seed: 42
deterministic: true
mixed_precision: true                   # Use FP16 for faster training
```

### Key Parameters Explained

| Parameter | What it does | Typical values |
|-----------|--------------|----------------|
| `batch_size` | Images processed together | 16-64 |
| `learning_rate` | Step size for updates | 0.0001-0.01 |
| `num_epochs` | Training iterations | 20-50 |
| `freeze_backbone_epochs` | Phase 1 duration | 3-10 |
| `dropout_rate` | Regularization strength | 0.2-0.5 |
| `mixup_alpha` | Data augmentation strength | 0.1-0.4 |

---

## 2. Starting Training

### Step 2.1: Verify Everything is Ready

```bash
# Activate environment
source venv/bin/activate

# Navigate to project
cd /path/to/reachy_emotion

# Check GPU
nvidia-smi

# Check data exists
ls data/train/
ls data/val/
```

### Step 2.2: Start Training

```bash
# Basic training command
python trainer/train_resnet50.py \
    --config fer_finetune/specs/resnet50_emotion_2cls.yaml

# With custom run ID
python trainer/train_resnet50.py \
    --config fer_finetune/specs/resnet50_emotion_2cls.yaml \
    --run-id my_first_training

# With custom data directory
python trainer/train_resnet50.py \
    --config fer_finetune/specs/resnet50_emotion_2cls.yaml \
    --data-dir /path/to/my/data

# With custom output directory
python trainer/train_resnet50.py \
    --config fer_finetune/specs/resnet50_emotion_2cls.yaml \
    --output-dir /path/to/outputs
```

### Step 2.3: What Happens When You Start

```
============================================================
ResNet-50 Emotion Classifier Training
Model: resnet50-affectnet-raf-db (placeholder)
Run ID: resnet50_emotion_20260128_231500
============================================================

Loading config: fer_finetune/specs/resnet50_emotion_2cls.yaml
Trainer initialized on device: cuda
Model params: 23,510,082 total, 4,098 trainable

============================================================
Starting training run: resnet50_emotion_20260128_231500
============================================================

Data loaders created: 25 train batches, 7 val batches
Class weights applied: [1.0, 1.0]
Backbone frozen

Epoch 1/20 (LR: 1.00e-04)
  Train - Loss: 0.6823, F1: 0.5234
  Val   - Loss: 0.5912, F1: 0.6123, ECE: 0.1523
Gate A: FAILED
  F1 macro: 0.6123 (req: 0.84)
  Balanced acc: 0.6234 (req: 0.85)
  ECE: 0.1523 (req: ≤0.08)
```

---

## 3. Understanding the Training Loop

### What Happens Each Epoch

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ONE TRAINING EPOCH                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. TRAINING PHASE                                                  │
│     ┌─────────────────────────────────────────────────────────┐    │
│     │ For each batch in training data:                         │    │
│     │   a. Load batch of images + labels                       │    │
│     │   b. Apply augmentation (flip, rotate, etc.)             │    │
│     │   c. Forward pass: images → model → predictions          │    │
│     │   d. Compute loss (how wrong are we?)                    │    │
│     │   e. Backward pass: compute gradients                    │    │
│     │   f. Update weights (optimizer step)                     │    │
│     └─────────────────────────────────────────────────────────┘    │
│                                                                      │
│  2. VALIDATION PHASE                                                │
│     ┌─────────────────────────────────────────────────────────┐    │
│     │ For each batch in validation data:                       │    │
│     │   a. Load batch (NO augmentation)                        │    │
│     │   b. Forward pass only (no gradient computation)         │    │
│     │   c. Collect predictions                                 │    │
│     │                                                          │    │
│     │ After all batches:                                       │    │
│     │   - Compute metrics (F1, accuracy, ECE, etc.)           │    │
│     │   - Check quality gates                                  │    │
│     └─────────────────────────────────────────────────────────┘    │
│                                                                      │
│  3. END OF EPOCH                                                    │
│     - Update learning rate (scheduler)                              │
│     - Save checkpoint if best model                                 │
│     - Check early stopping                                          │
│     - Check phase transition (Phase 1 → Phase 2)                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Phase Transition

After `freeze_backbone_epochs` (default: 5), training transitions:

```
============================================================
Transitioning to Phase 2: Unfreezing backbone layers
============================================================

Unfrozen 2359296 parameters in layers: ['layer4']
Trainable params: 2,363,394
```

Now the model can fine-tune the backbone features.

---

## 4. Reading Training Output

### Epoch Output Explained

```
Epoch 15/20 (LR: 3.45e-04)
  Train - Loss: 0.2134, F1: 0.8756
  Val   - Loss: 0.2567, F1: 0.8534, ECE: 0.0623
Gate A: FAILED
  F1 macro: 0.8534 (req: 0.84)
  Balanced acc: 0.8612 (req: 0.85)
  ECE: 0.0623 (req: ≤0.08)
Saved best model: outputs/checkpoints/best_model.pth
```

| Field | Meaning | Good values |
|-------|---------|-------------|
| `Epoch 15/20` | Current epoch / total | Progress indicator |
| `LR: 3.45e-04` | Current learning rate | Decreases over time |
| `Train Loss` | Training error | Should decrease |
| `Train F1` | Training F1 score | Should increase |
| `Val Loss` | Validation error | Should decrease |
| `Val F1` | Validation F1 score | Should increase |
| `ECE` | Calibration error | Should be low (<0.08) |

### Signs of Good Training

```
✅ GOOD: Loss decreasing, F1 increasing
Epoch 1:  Loss: 0.68, F1: 0.52
Epoch 5:  Loss: 0.45, F1: 0.71
Epoch 10: Loss: 0.28, F1: 0.83
Epoch 15: Loss: 0.21, F1: 0.87

✅ GOOD: Train and Val metrics are close
Train F1: 0.87, Val F1: 0.85  (difference: 0.02)

✅ GOOD: Metrics improve after Phase 2 starts
Phase 1 end:   Val F1: 0.78
Phase 2 start: Val F1: 0.79
Phase 2 end:   Val F1: 0.86
```

### Signs of Problems

```
❌ BAD: Loss not decreasing
Epoch 1:  Loss: 0.68
Epoch 5:  Loss: 0.67
Epoch 10: Loss: 0.68
→ Learning rate might be too low, or data issue

❌ BAD: Large gap between train and val (overfitting)
Train F1: 0.95, Val F1: 0.72  (difference: 0.23)
→ Model memorizing training data, need more regularization

❌ BAD: Loss exploding
Epoch 1:  Loss: 0.68
Epoch 2:  Loss: 2.34
Epoch 3:  Loss: NaN
→ Learning rate too high, or numerical instability

❌ BAD: Validation getting worse (overfitting)
Epoch 10: Val F1: 0.83
Epoch 15: Val F1: 0.81
Epoch 20: Val F1: 0.78
→ Training too long, early stopping should trigger
```

---

## 5. Monitoring Training Progress

### Using Terminal Output

The simplest way - watch the terminal:

```bash
# Training outputs progress every epoch
# Watch for:
# - Loss decreasing
# - F1 increasing
# - Gate A status
```

### Using TensorBoard

```bash
# In a separate terminal
tensorboard --logdir outputs/logs --port 6006

# Open browser: http://localhost:6006
```

### Using MLflow

```bash
# Start MLflow server (if not running)
mlflow server --host 0.0.0.0 --port 5000

# Open browser: http://localhost:5000
# Find your experiment and run
```

---

## 6. Checkpoints and Resuming

### Checkpoint Files

Training saves checkpoints automatically:

```
outputs/checkpoints/
├── latest.pth          # Most recent checkpoint
├── best_model.pth      # Best validation F1
├── checkpoint_epoch_5.pth
├── checkpoint_epoch_10.pth
└── checkpoint_epoch_15.pth
```

### What's in a Checkpoint?

```python
checkpoint = {
    'epoch': 15,                    # Current epoch
    'model_state_dict': {...},      # Model weights
    'optimizer_state_dict': {...},  # Optimizer state
    'scheduler_state_dict': {...},  # LR scheduler state
    'metrics': {...},               # Last validation metrics
    'config': {...},                # Training configuration
    'training_phase': 2,            # Current phase
    'best_metric': 0.8534,          # Best F1 so far
}
```

### Resuming Training

If training is interrupted (crash, timeout, etc.):

```bash
# Resume from latest checkpoint
python trainer/train_resnet50.py \
    --config fer_finetune/specs/resnet50_emotion_2cls.yaml \
    --resume outputs/checkpoints/latest.pth

# Resume from specific checkpoint
python trainer/train_resnet50.py \
    --config fer_finetune/specs/resnet50_emotion_2cls.yaml \
    --resume outputs/checkpoints/checkpoint_epoch_10.pth
```

Output when resuming:
```
Loading checkpoint: outputs/checkpoints/latest.pth
Resumed from epoch 15, phase 2
Best metric so far: 0.8534
Trainable params: 2,363,394

============================================================
Resuming training run: resnet50_emotion_20260128_231500 from epoch 16
============================================================
```

---

## 7. Training Time Estimates

### Factors Affecting Training Time

| Factor | Impact |
|--------|--------|
| Dataset size | More images = longer epochs |
| Batch size | Larger = faster (if GPU memory allows) |
| Number of epochs | More = longer total time |
| GPU speed | Faster GPU = faster training |
| Mixed precision | FP16 is ~2x faster than FP32 |

### Typical Training Times

| Dataset Size | GPU | Time per Epoch | Total (20 epochs) |
|--------------|-----|----------------|-------------------|
| 1,000 images | RTX 3090 | ~30 seconds | ~10 minutes |
| 10,000 images | RTX 3090 | ~3 minutes | ~1 hour |
| 50,000 images | RTX 3090 | ~15 minutes | ~5 hours |

---

## 8. Hands-On Exercise

### Exercise: Run Your First Training

1. **Prepare minimal data** (if you don't have real data):
   ```bash
   # Create synthetic data for testing
   python -c "
   from pathlib import Path
   import numpy as np
   from PIL import Image
   
   for split in ['train', 'val']:
       for cls in ['happy', 'sad']:
           d = Path(f'data_test/{split}/{cls}')
           d.mkdir(parents=True, exist_ok=True)
           n = 100 if split == 'train' else 25
           for i in range(n):
               color = (255, 255, 0) if cls == 'happy' else (0, 0, 255)
               img = np.full((224, 224, 3), color, dtype=np.uint8)
               noise = np.random.randint(-30, 30, (224, 224, 3))
               img = np.clip(img + noise, 0, 255).astype(np.uint8)
               Image.fromarray(img).save(d / f'{i:04d}.jpg')
   print('Created test data in data_test/')
   "
   ```

2. **Run short training** (5 epochs):
   ```bash
   python trainer/train_resnet50.py \
       --config fer_finetune/specs/resnet50_emotion_2cls.yaml \
       --data-dir data_test \
       --run-id test_run_001
   ```

3. **Observe the output**:
   - Does loss decrease?
   - Does F1 increase?
   - Does Phase 2 transition happen?

4. **Check the checkpoint**:
   ```bash
   ls outputs/checkpoints/
   ```

---

## 9. Troubleshooting

### CUDA Out of Memory

```
RuntimeError: CUDA out of memory
```

**Solutions**:
1. Reduce batch size in config (32 → 16 → 8)
2. Close other GPU processes
3. Use gradient accumulation (advanced)

### Training Not Converging

**Symptoms**: Loss stays flat, F1 doesn't improve

**Solutions**:
1. Increase learning rate (0.001 → 0.01)
2. Check data is loaded correctly
3. Verify labels are correct
4. Try without mixup first

### NaN Loss

**Symptoms**: Loss becomes NaN

**Solutions**:
1. Reduce learning rate (0.001 → 0.0001)
2. Enable gradient clipping (already on by default)
3. Check for corrupted images in data

### Early Stopping Too Soon

**Symptoms**: Training stops before good results

**Solutions**:
1. Increase patience (10 → 20)
2. Decrease min_delta (0.001 → 0.0001)
3. Disable early stopping temporarily

---

## 10. Summary

### What You've Learned

1. ✅ Training configuration parameters
2. ✅ How to start training
3. ✅ What happens during each epoch
4. ✅ How to read training output
5. ✅ Signs of good vs. bad training
6. ✅ How to resume from checkpoints
7. ✅ Common troubleshooting

### Key Commands

```bash
# Start training
python trainer/train_resnet50.py --config fer_finetune/specs/resnet50_emotion_2cls.yaml

# Resume training
python trainer/train_resnet50.py --config ... --resume outputs/checkpoints/latest.pth

# Custom data directory
python trainer/train_resnet50.py --config ... --data-dir /path/to/data
```

### What's Next

In the next guide, we'll learn about monitoring and debugging:
- Using MLflow for experiment tracking
- Debugging common issues
- Analyzing training curves

---

*Next: [Guide 05: Monitoring & Debugging](05_MONITORING_DEBUGGING.md)*
