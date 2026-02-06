# Guide 05: Monitoring & Debugging

**Duration**: 2-3 hours  
**Difficulty**: Intermediate  
**Prerequisites**: Guide 04 complete, training started at least once

---

## Learning Objectives

By the end of this guide, you will:
- [ ] Know how to use MLflow for experiment tracking
- [ ] Understand training curves and what they mean
- [ ] Be able to diagnose common training problems
- [ ] Know how to compare different training runs

---

## 1. MLflow Experiment Tracking

### What is MLflow?

**MLflow** is a tool that tracks your experiments:
- Records all training parameters
- Logs metrics over time
- Stores model artifacts
- Allows comparing different runs

### Starting MLflow Server

```bash
# Start MLflow server (run in separate terminal)
mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --backend-store-uri sqlite:///mlflow.db \
    --default-artifact-root ./mlruns

# Open in browser: http://localhost:5000
```

### MLflow UI Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  MLflow Experiments                                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Experiment: reachy_emotion_2cls                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Run Name          │ Status  │ val_f1  │ val_loss │ Duration │   │
│  ├───────────────────┼─────────┼─────────┼──────────┼──────────┤   │
│  │ run_20260128_001  │ ✅ Done │ 0.8534  │ 0.2567   │ 45m      │   │
│  │ run_20260128_002  │ ✅ Done │ 0.8123  │ 0.3012   │ 42m      │   │
│  │ run_20260127_001  │ ❌ Fail │ 0.6234  │ 0.5891   │ 12m      │   │
│  └───────────────────┴─────────┴─────────┴──────────┴──────────┘   │
│                                                                      │
│  Click a run to see details:                                        │
│  - Parameters (learning rate, batch size, etc.)                     │
│  - Metrics over time (loss, F1, ECE)                               │
│  - Artifacts (checkpoints, configs)                                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### What Gets Logged

The training script automatically logs:

| Category | Items |
|----------|-------|
| **Parameters** | learning_rate, batch_size, num_epochs, etc. |
| **Metrics** | train_loss, val_loss, train_f1, val_f1, ece, brier |
| **Artifacts** | best_model.pth, config.yaml |
| **Tags** | run_id, model_name, training_phase |

---

## 2. Understanding Training Curves

### Loss Curves

```
Loss over Epochs
│
│  ╲
│   ╲___
│       ╲___
│           ╲___
│               ╲___________
│                           
└────────────────────────────▶ Epochs
   1    5    10   15   20

✅ GOOD: Smooth decrease, then plateau
```

**What to look for**:
- **Decreasing trend**: Model is learning
- **Plateau**: Model has converged
- **Spikes**: Possible learning rate issues

### F1 Score Curves

```
F1 Score over Epochs
│                    ___________
│               ____╱
│          ____╱
│     ____╱
│____╱
│
└────────────────────────────▶ Epochs
   1    5    10   15   20

✅ GOOD: Increasing, then plateau
```

### Train vs. Validation Gap

```
                Train F1
               ╱‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
              ╱
             ╱
            ╱   Val F1
           ╱  ╱‾‾‾‾‾‾‾‾‾‾‾‾‾‾
          ╱  ╱
         ╱  ╱
        ╱  ╱
       ╱  ╱
      ╱  ╱
└────────────────────────────▶ Epochs

Small gap (< 5%): ✅ Good generalization
Large gap (> 15%): ❌ Overfitting
```

---

## 3. Diagnosing Common Problems

### Problem 1: Overfitting

**Symptoms**:
- Train F1 keeps increasing
- Val F1 plateaus or decreases
- Large gap between train and val

```
Train F1: 0.95  ──▶  Keeps going up
Val F1:   0.78  ──▶  Stuck or going down
Gap:      0.17  ──▶  Too large!
```

**Solutions**:

| Solution | How to apply |
|----------|--------------|
| More dropout | Increase `dropout_rate: 0.3 → 0.5` |
| More augmentation | Increase `mixup_alpha: 0.2 → 0.4` |
| Less epochs | Reduce `num_epochs` or use early stopping |
| More data | Add more training images |
| Weight decay | Increase `weight_decay: 0.01 → 0.05` |

### Problem 2: Underfitting

**Symptoms**:
- Both train and val F1 are low
- Loss not decreasing
- Model not learning

```
Train F1: 0.55  ──▶  Low
Val F1:   0.52  ──▶  Also low
Loss:     0.65  ──▶  Not decreasing
```

**Solutions**:

| Solution | How to apply |
|----------|--------------|
| Higher learning rate | Increase `learning_rate: 0.001 → 0.01` |
| More epochs | Increase `num_epochs` |
| Less regularization | Decrease `dropout_rate`, `weight_decay` |
| Unfreeze more layers | Add more layers to `unfreeze_layers` |
| Check data | Verify images and labels are correct |

### Problem 3: Unstable Training

**Symptoms**:
- Loss jumps up and down
- Metrics oscillate wildly
- Training doesn't converge

```
Epoch 1:  Loss: 0.68
Epoch 2:  Loss: 0.45  ↓
Epoch 3:  Loss: 0.89  ↑ Jump!
Epoch 4:  Loss: 0.52  ↓
Epoch 5:  Loss: 1.23  ↑ Jump!
```

**Solutions**:

| Solution | How to apply |
|----------|--------------|
| Lower learning rate | Decrease `learning_rate: 0.001 → 0.0001` |
| Larger batch size | Increase `batch_size: 32 → 64` |
| Gradient clipping | Already enabled, but check `gradient_clip_norm` |
| Warmup | Increase `warmup_epochs: 2 → 5` |

### Problem 4: Poor Calibration (High ECE)

**Symptoms**:
- F1 is good but ECE is high
- Model is overconfident

```
Val F1:  0.85  ──▶  Good!
ECE:     0.15  ──▶  Too high (should be < 0.08)
```

**Solutions**:

| Solution | How to apply |
|----------|--------------|
| Label smoothing | Increase `label_smoothing: 0.1 → 0.2` |
| Temperature scaling | Apply post-training (see Guide 06) |
| Mixup | Enable or increase `mixup_alpha` |

---

## 4. Debugging Checklist

When training isn't working, check these in order:

### Step 1: Check Data

```python
# Verify data loading
from trainer.fer_finetune.dataset import create_dataloaders

train_loader, val_loader = create_dataloaders(
    data_dir='data',
    batch_size=32,
    num_workers=4,
    input_size=224,
    class_names=['happy', 'sad'],
)

# Check batch
images, labels = next(iter(train_loader))
print(f"Images shape: {images.shape}")  # Should be [32, 3, 224, 224]
print(f"Labels: {labels[:10]}")          # Should be 0s and 1s
print(f"Unique labels: {labels.unique()}")  # Should be [0, 1]

# Check class balance
from collections import Counter
all_labels = []
for _, labels in train_loader:
    all_labels.extend(labels.tolist())
print(f"Class distribution: {Counter(all_labels)}")
```

### Step 2: Check Model

```python
# Verify model works
import torch
from trainer.fer_finetune.model import EmotionClassifier

model = EmotionClassifier(num_classes=2)
device = torch.device('cuda')
model = model.to(device)

# Test forward pass
dummy = torch.randn(1, 3, 224, 224).to(device)
output = model(dummy)
print(f"Output shape: {output['logits'].shape}")  # Should be [1, 2]

# Check gradients flow
loss = output['logits'].sum()
loss.backward()
print(f"Gradients computed: {model.fc.weight.grad is not None}")
```

### Step 3: Check Config

```python
# Verify config loads correctly
from trainer.fer_finetune.config import TrainingConfig

config = TrainingConfig.from_yaml('trainer/fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml')
print(f"Learning rate: {config.learning_rate}")
print(f"Batch size: {config.data.batch_size}")
print(f"Data root: {config.data.data_root}")

# Verify data path exists
from pathlib import Path
data_path = Path(config.data.data_root)
print(f"Data path exists: {data_path.exists()}")
print(f"Train classes: {list((data_path / 'train').iterdir())}")
```

### Step 4: Check GPU

```python
import torch

print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU name: {torch.cuda.get_device_name(0)}")
print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

# Check memory usage
print(f"Memory allocated: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
print(f"Memory cached: {torch.cuda.memory_reserved() / 1e9:.2f} GB")
```

---

## 5. Comparing Experiments

### Using MLflow Compare

1. Open MLflow UI (http://localhost:5000)
2. Select multiple runs (checkbox)
3. Click "Compare"
4. View side-by-side metrics

### Manual Comparison Script

```python
"""Compare multiple training runs."""

import json
from pathlib import Path

def compare_runs(run_dirs):
    """Compare metrics from multiple runs."""
    results = []
    
    for run_dir in run_dirs:
        run_dir = Path(run_dir)
        
        # Load final metrics
        metrics_file = run_dir / 'final_metrics.json'
        if metrics_file.exists():
            with open(metrics_file) as f:
                metrics = json.load(f)
        else:
            # Try to load from checkpoint
            checkpoint = torch.load(run_dir / 'best_model.pth', map_location='cpu')
            metrics = checkpoint.get('metrics', {})
        
        results.append({
            'run': run_dir.name,
            'val_f1': metrics.get('f1_macro', 0),
            'val_loss': metrics.get('loss', 0),
            'ece': metrics.get('ece', 0),
        })
    
    # Print comparison table
    print(f"{'Run':<30} {'Val F1':<10} {'Val Loss':<10} {'ECE':<10}")
    print("-" * 60)
    for r in sorted(results, key=lambda x: x['val_f1'], reverse=True):
        print(f"{r['run']:<30} {r['val_f1']:<10.4f} {r['val_loss']:<10.4f} {r['ece']:<10.4f}")

# Example usage
compare_runs([
    'outputs/run_001',
    'outputs/run_002',
    'outputs/run_003',
])
```

---

## 6. Logging Custom Metrics

### Adding Custom Logging

If you need to track additional metrics:

```python
# In your training script or notebook
import mlflow

# Start a run
with mlflow.start_run(run_name="custom_metrics_run"):
    # Log parameters
    mlflow.log_param("custom_param", "value")
    
    # Log metrics at each epoch
    for epoch in range(num_epochs):
        # ... training code ...
        
        mlflow.log_metric("custom_metric", value, step=epoch)
        mlflow.log_metric("per_class_f1_happy", f1_happy, step=epoch)
        mlflow.log_metric("per_class_f1_sad", f1_sad, step=epoch)
    
    # Log artifacts
    mlflow.log_artifact("confusion_matrix.png")
    mlflow.log_artifact("training_curves.png")
```

---

## 7. Visualizing Results

### Plot Training Curves

```python
"""Plot training curves from checkpoint."""

import matplotlib.pyplot as plt
import torch
from pathlib import Path

def plot_training_curves(checkpoint_dir):
    """Plot loss and F1 curves from training history."""
    
    # Load training history (if saved)
    history_file = Path(checkpoint_dir) / 'training_history.json'
    
    if history_file.exists():
        import json
        with open(history_file) as f:
            history = json.load(f)
    else:
        print("No training history found. Using MLflow instead.")
        return
    
    epochs = range(1, len(history['train_loss']) + 1)
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    
    # Loss plot
    axes[0].plot(epochs, history['train_loss'], label='Train')
    axes[0].plot(epochs, history['val_loss'], label='Val')
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Loss')
    axes[0].set_title('Loss Curves')
    axes[0].legend()
    axes[0].grid(True)
    
    # F1 plot
    axes[1].plot(epochs, history['train_f1'], label='Train')
    axes[1].plot(epochs, history['val_f1'], label='Val')
    axes[1].axhline(y=0.84, color='r', linestyle='--', label='Gate A threshold')
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('F1 Score')
    axes[1].set_title('F1 Score Curves')
    axes[1].legend()
    axes[1].grid(True)
    
    plt.tight_layout()
    plt.savefig('training_curves.png', dpi=150)
    plt.show()
    print("Saved to training_curves.png")

plot_training_curves('outputs/checkpoints')
```

### Plot Confusion Matrix

```python
"""Plot confusion matrix from predictions."""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix

def plot_confusion_matrix(y_true, y_pred, class_names):
    """Plot confusion matrix."""
    cm = confusion_matrix(y_true, y_pred)
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(
        cm, 
        annot=True, 
        fmt='d', 
        cmap='Blues',
        xticklabels=class_names,
        yticklabels=class_names,
    )
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title('Confusion Matrix')
    plt.tight_layout()
    plt.savefig('confusion_matrix.png', dpi=150)
    plt.show()

# Example usage (after getting predictions)
# plot_confusion_matrix(y_true, y_pred, ['happy', 'sad'])
```

---

## 8. Summary

### What You've Learned

1. ✅ How to use MLflow for experiment tracking
2. ✅ How to read and interpret training curves
3. ✅ How to diagnose overfitting, underfitting, and instability
4. ✅ Debugging checklist for training issues
5. ✅ How to compare different experiments
6. ✅ How to visualize training results

### Key Takeaways

| Problem | Key Indicator | Solution |
|---------|---------------|----------|
| Overfitting | Train >> Val | More regularization |
| Underfitting | Both low | Higher LR, more capacity |
| Instability | Loss jumps | Lower LR, larger batch |
| Poor calibration | High ECE | Label smoothing, temperature |

### What's Next

In the next guide, we'll learn about evaluation and Gate A validation:
- Computing all Gate A metrics
- Understanding what each metric means
- Deciding if the model is ready for deployment

---

*Next: [Guide 06: Evaluation & Gate A](06_EVALUATION_GATE_A.md)*
