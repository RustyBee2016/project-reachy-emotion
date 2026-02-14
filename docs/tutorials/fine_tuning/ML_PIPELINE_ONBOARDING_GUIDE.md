# ML Pipeline Onboarding Guide: EfficientNet-B0 (HSEmotion)

**Project**: Reachy Emotion Recognition  
**Audience**: New ML Engineers  
**Last Updated**: 2026-01-31  
**Estimated Time**: 4-6 hours

---

## Welcome, New ML Engineer!

This guide will get you up to speed on our emotion classification ML pipeline. By the end, you'll understand:

1. **Why we chose EfficientNet-B0** with HSEmotion weights
2. **How to run inference** with the base model
3. **How to fine-tune** with synthetic video data
4. **How to validate** against quality gates
5. **How to export** for Jetson deployment

---

## Part 1: Architecture Overview

### Model Selection: Why EfficientNet-B0?

| Factor | ResNet-50 | EfficientNet-B0 | Winner |
|--------|-----------|-----------------|--------|
| **Latency (Jetson)** | ~120 ms | ~40 ms | EfficientNet |
| **GPU Memory** | ~2.2 GB | ~0.8 GB | EfficientNet |
| **Accuracy** | ~86% | ~86% | Tie |
| **Thermal Headroom** | Tight | 3× margin | EfficientNet |

**Key insight**: EfficientNet-B0 gives us **3× latency and memory headroom**, which means:
- Room for gesture planning workloads
- Better thermal performance on Jetson
- Future-proofing for multimodal features

### What is HSEmotion?

HSEmotion is a library providing **video-optimized emotion recognition** models:

- **Pre-trained on**: VGGFace2 + AffectNet (large facial expression datasets)
- **Model name**: `enet_b0_8_best_vgaf`
- **8 classes**: anger, contempt, disgust, fear, happy, neutral, sad, surprise
- **Our use**: Binary (happy/sad) for Phase 1, expandable to 8-class

```python
# Install HSEmotion
pip install hsemotion

# Or via emotiefflib
pip install emotiefflib
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    EfficientNet-B0 Backbone                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Stem     │→ │ Blocks   │→ │ Blocks   │→ │ Conv     │    │
│  │ Conv     │  │ 1-4      │  │ 5-6      │  │ Head     │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│       ↓              ↓             ↓             ↓          │
│   [Frozen in Phase 1]        [Unfrozen in Phase 2]         │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    Global Average Pooling
                              ↓
                    ┌──────────────────┐
                    │   Dropout (0.3)  │
                    └──────────────────┘
                              ↓
                    ┌──────────────────┐
                    │  FC: 1280 → 2    │ ← Classification Head
                    └──────────────────┘
                              ↓
                      [happy, sad]
```

---

## Part 2: Quick Start - Running Inference

### Step 2.1: Environment Setup

```bash
# Create conda environment
conda create -n reachy_ml python=3.10 -y
conda activate reachy_ml

# Install PyTorch (CUDA 12.x)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Install dependencies
pip install timm albumentations scikit-learn mlflow
pip install hsemotion  # Optional: HSEmotion library
```

### Step 2.2: Load Pre-trained Model

```python
import torch
from trainer.fer_finetune.model_efficientnet import create_efficientnet_model

# Create model with HSEmotion weights
model = create_efficientnet_model(
    num_classes=2,           # Binary: happy, sad
    pretrained=True,         # Load HSEmotion weights
    dropout_rate=0.3,
)

# Move to GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)
model.eval()

print(f"Model loaded: {model.get_total_params():,} parameters")
```

### Step 2.3: Run Inference on an Image

```python
import cv2
import torch
from torchvision import transforms

# Image preprocessing (matches HSEmotion training)
transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
])

def predict_emotion(image_path: str, model, device) -> dict:
    """Predict emotion from an image."""
    # Load and preprocess
    image = cv2.imread(image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    tensor = transform(image).unsqueeze(0).to(device)
    
    # Inference
    with torch.no_grad():
        outputs = model(tensor)
        logits = outputs['logits']
        probs = torch.softmax(logits, dim=1)
    
    # Decode
    class_names = ["happy", "sad"]
    pred_idx = probs.argmax(dim=1).item()
    confidence = probs[0, pred_idx].item()
    
    return {
        "emotion": class_names[pred_idx],
        "confidence": confidence,
        "probabilities": {
            name: probs[0, i].item() 
            for i, name in enumerate(class_names)
        }
    }

# Example usage
result = predict_emotion("test_face.jpg", model, device)
print(f"Emotion: {result['emotion']} ({result['confidence']:.1%})")
```

---

## Part 3: Understanding the Training Pipeline

### Training Strategy: Two-Phase Approach

```
Phase 1 (Epochs 1-5): Frozen Backbone
├── Backbone: FROZEN (no gradient updates)
├── Head: TRAINABLE (learns task-specific features)
├── Learning rate: Higher (0.001)
└── Goal: Train classification head quickly

Phase 2 (Epochs 6+): Fine-tuning
├── Backbone blocks 5-6: UNFROZEN
├── Head: TRAINABLE
├── Learning rate: Lower (0.0001 for backbone)
└── Goal: Adapt backbone to our specific domain
```

### Why Two Phases?

1. **Phase 1**: The backbone already knows "how to see faces" from HSEmotion training. We only need to teach the head "what emotions we care about."

2. **Phase 2**: Once the head is trained, we slightly adjust the backbone's later layers to better match our specific video data.

### Key Files

```
trainer/
├── train_efficientnet.py              # Entry point script
├── fer_finetune/
│   ├── model_efficientnet.py          # Model definition
│   ├── train_efficientnet.py          # Training loop
│   ├── config.py                      # Configuration system
│   ├── dataset.py                     # Data loading
│   ├── evaluate.py                    # Metrics
│   └── specs/
│       ├── efficientnet_b0_emotion_2cls.yaml  # Binary config
│       └── efficientnet_b0_emotion_8cls.yaml  # 8-class config
```

---

## Part 4: Training with Synthetic Video Data

### Step 4.1: Data Directory Structure

Your training data should be organized as:

```
/media/project_data/reachy_emotion/videos/
├── train/
│   ├── happy/
│   │   ├── video_001.mp4
│   │   ├── video_002.mp4
│   │   └── ...
│   └── sad/
│       ├── video_101.mp4
│       ├── video_102.mp4
│       └── ...
└── test/
    ├── happy/
    │   └── ...
    └── sad/
        └── ...
```

### Step 4.2: Understanding the Config File

```yaml
# trainer/fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml

model:
  backbone: efficientnet_b0
  num_classes: 2
  pretrained_weights: enet_b0_8_best_vgaf   # HSEmotion weights
  freeze_backbone_epochs: 5                  # Phase 1 duration
  unfreeze_layers: ["blocks.6", "blocks.5"]  # Layers for Phase 2

data:
  data_root: /media/project_data/reachy_emotion/videos
  batch_size: 32
  class_names: ["happy", "sad"]
  mixup_alpha: 0.2        # Data augmentation strength

# Training
num_epochs: 30
learning_rate: 0.0003
lr_scheduler: cosine
warmup_epochs: 3

# Quality Gates
gate_a_min_f1_macro: 0.84
gate_a_min_balanced_accuracy: 0.85
gate_a_max_ece: 0.08
```

### Step 4.3: Launch Training

```bash
# Activate environment
conda activate reachy_ml

# Navigate to project
cd /path/to/reachy_emotion

# Start training (binary classification)
python trainer/train_efficientnet.py \
    --config fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml \
    --run-id my_first_run

# With custom data directory
python trainer/train_efficientnet.py \
    --config fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml \
    --data-dir /path/to/my/videos \
    --run-id custom_data_run
```

### Step 4.4: Monitor Training

Training output shows progress:

```
============================================================
EfficientNet-B0 Emotion Classifier Training
Model: HSEmotion enet_b0_8_best_vgaf
Run ID: my_first_run
============================================================

EfficientNetTrainer initialized on device: cuda
Model params: 4,013,954 total, 2,562 trainable   ← Phase 1: only head

Epoch 1/30 (LR: 3.00e-04)
  Train - Loss: 0.6832, F1: 0.5234
  Val   - Loss: 0.5921, F1: 0.6012, ECE: 0.1523

...

==================================================
Transitioning to Phase 2: Unfreezing backbone layers   ← Automatic!
==================================================
Unfrozen 524,288 parameters matching: ['blocks.6', 'blocks.5']
Trainable params: 526,850

Epoch 6/30 (LR: 2.85e-04)
  Train - Loss: 0.3245, F1: 0.7823
  Val   - Loss: 0.2891, F1: 0.8234, ECE: 0.0723

...

Gate A: PASSED
  F1 macro: 0.8523 (req: 0.84)
  Balanced acc: 0.8612 (req: 0.85)
  ECE: 0.0612 (req: ≤0.08)
```

---

## Part 5: Quality Gates

### Gate A: Offline Validation (Pre-deployment)

| Metric | Threshold | What it measures |
|--------|-----------|-----------------|
| **Macro F1** | ≥ 0.84 | Overall performance |
| **Balanced Accuracy** | ≥ 0.85 | Performance across classes |
| **Per-class F1** | ≥ 0.75 | No class left behind |
| **ECE** | ≤ 0.08 | Confidence calibration |
| **Brier** | ≤ 0.16 | Probability accuracy |

### Gate B: Robot Deployment (Jetson)

| Metric | Threshold | EfficientNet-B0 Typical |
|--------|-----------|------------------------|
| **Latency p50** | ≤ 120 ms | ~40 ms ✓ |
| **Latency p95** | ≤ 250 ms | ~80 ms ✓ |
| **GPU Memory** | ≤ 2.5 GB | ~0.8 GB ✓ |
| **Macro F1** | ≥ 0.80 | Depends on training |

### What Happens If Gates Fail?

```
Gate A: FAILED
  F1 macro: 0.7923 (req: 0.84)      ← Below threshold
  Balanced acc: 0.8012 (req: 0.85)  ← Below threshold
  ECE: 0.0612 (req: ≤0.08)          ← OK

Training completed - Gate A FAILED
```

**Solutions:**
- Collect more training data
- Train for more epochs
- Adjust hyperparameters (learning rate, dropout)
- Check for data quality issues

---

## Part 6: Resuming and Checkpointing

### Checkpoints Saved

```
checkpoints/
├── latest.pth              # Most recent epoch
├── best_model.pth          # Best validation F1
└── checkpoint_epoch_5.pth  # Periodic saves
```

### Resume Training

```bash
# Resume from latest checkpoint
python trainer/train_efficientnet.py \
    --config fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml \
    --resume checkpoints/latest.pth

# Resume from specific epoch
python trainer/train_efficientnet.py \
    --config fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml \
    --resume checkpoints/checkpoint_epoch_10.pth
```

---

## Part 7: Export for Deployment

### Export to ONNX

```bash
# Export best model to ONNX
python trainer/train_efficientnet.py \
    --export-only \
    --resume checkpoints/best_model.pth \
    --export-path exports/my_model/
```

### Output Structure

```
exports/my_model/
├── emotion_efficientnet.onnx    # ONNX model
├── emotion_efficientnet_fp16.onnx  # FP16 optimized
├── config.json                  # Model metadata
└── class_names.json             # Class mapping
```

### Convert to TensorRT (on Jetson)

```bash
# On Jetson Xavier NX
trtexec \
    --onnx=emotion_efficientnet_fp16.onnx \
    --saveEngine=emotion_efficientnet.engine \
    --fp16 \
    --workspace=2048
```

---

## Part 8: MLflow Experiment Tracking

### View Experiments

```bash
# Start MLflow UI
mlflow ui --backend-store-uri file:///workspace/mlruns

# Open in browser: http://localhost:5000
```

### What's Tracked

- **Parameters**: All config values
- **Metrics**: Loss, F1, accuracy, ECE per epoch
- **Artifacts**: Model checkpoints, training curves
- **Tags**: Model type, run ID

### Query Experiments Programmatically

```python
import mlflow

mlflow.set_tracking_uri("file:///workspace/mlruns")

# Get best run from experiment
experiment = mlflow.get_experiment_by_name("efficientnet_b0_emotion_2cls")
runs = mlflow.search_runs(experiment.experiment_id, order_by=["metrics.val_f1_macro DESC"])

best_run = runs.iloc[0]
print(f"Best F1: {best_run['metrics.val_f1_macro']:.4f}")
print(f"Run ID: {best_run['run_id']}")
```

---

## Part 9: Common Issues and Solutions

### Issue: "CUDA out of memory"

**Solution**: Reduce batch size in config:
```yaml
data:
  batch_size: 16  # Was 32
```

### Issue: "No module named 'hsemotion'"

**Solution**: Install HSEmotion or use timm fallback:
```bash
pip install hsemotion
# Or: the code will automatically use timm + ImageNet weights
```

### Issue: Low validation accuracy

**Solutions**:
1. Check data balance: `ls -la data/train/happy/ | wc -l`
2. Increase training epochs
3. Adjust learning rate (try 0.0001)
4. Check for corrupted videos

### Issue: Training phase not transitioning

**Check**: Ensure `freeze_backbone_epochs` in config matches expectations:
```yaml
model:
  freeze_backbone_epochs: 5  # Transition happens after epoch 5
```

---

## Part 10: Quick Reference

### Commands Cheat Sheet

```bash
# Train 2-class model
python trainer/train_efficientnet.py --config fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml

# Train 8-class model
python trainer/train_efficientnet.py --config fer_finetune/specs/efficientnet_b0_emotion_8cls.yaml

# Resume training
python trainer/train_efficientnet.py --config <config> --resume checkpoints/latest.pth

# Export to ONNX
python trainer/train_efficientnet.py --export-only --resume checkpoints/best_model.pth

# Check GPU
nvidia-smi

# Start MLflow UI
mlflow ui --backend-store-uri file:///workspace/mlruns
```

### Key Parameters

| Parameter | Default | Tune when... |
|-----------|---------|--------------|
| `learning_rate` | 0.0003 | Underfitting/overfitting |
| `batch_size` | 32 | OOM errors |
| `num_epochs` | 30 | Not converging |
| `dropout_rate` | 0.3 | Overfitting |
| `freeze_backbone_epochs` | 5 | Head not learning |
| `mixup_alpha` | 0.2 | Need more regularization |

---

## Next Steps

1. **Run the Quick Start** — Get inference working first
2. **Train on demo data** — Use synthetic videos from the web app
3. **Monitor with MLflow** — Understand your experiments
4. **Pass Gate A** — Achieve deployment-ready metrics
5. **Export and deploy** — Get your model onto Jetson

---

## Additional Resources

- [Fine-Tuning Guide 01: What is Fine-Tuning?](01_WHAT_IS_FINE_TUNING.md)
- [Fine-Tuning Guide 04: Training Walkthrough](04_TRAINING_WALKTHROUGH.md)
- [HSEmotion GitHub](https://github.com/HSE-asavchenko/hsemotion)
- [EfficientNet Paper](https://arxiv.org/abs/1905.11946)
- [Week 2 Tutorial: Training Pipeline Integration](../WEEK_02_TRAINING_PIPELINE_INTEGRATION.md)

---

**Questions?** Ask a senior engineer or check the troubleshooting sections in individual guides.

*Happy training!* 🚀
