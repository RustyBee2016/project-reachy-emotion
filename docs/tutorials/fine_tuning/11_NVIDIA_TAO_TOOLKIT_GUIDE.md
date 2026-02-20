# Guide 11: NVIDIA TAO Toolkit for Emotion Classification

**Duration**: 3-4 hours  
**Difficulty**: Intermediate to Advanced  
**Prerequisites**: Guides 01-03 complete, Docker basics understood

---

## Overview

**NVIDIA TAO (Train, Adapt, Optimize) Toolkit** is an AI development platform that accelerates the creation of production-ready models. This guide covers:

1. What TAO Toolkit is and why we use it
2. Setting up the TAO environment
3. Training EmotionNet with TAO
4. Exporting to TensorRT for Jetson deployment
5. Integration with the Reachy project pipeline

**TAO is the recommended approach for production deployments to Jetson Xavier NX.**

---

## 1. What is NVIDIA TAO Toolkit?

### 1.1 TAO vs. Standard PyTorch Training

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  TRAINING APPROACH COMPARISON                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  STANDARD PYTORCH (Guides 01-07)         NVIDIA TAO TOOLKIT             │
│  ────────────────────────────────        ──────────────────────────     │
│                                                                          │
│  ✅ Flexible, full control               ✅ Production-optimized         │
│  ✅ Easy to debug and modify             ✅ Built-in TensorRT export     │
│  ✅ Works on any GPU                     ✅ Jetson-optimized models      │
│  ⚠️ Manual TensorRT conversion          ✅ INT8 calibration support     │
│  ⚠️ Requires ONNX intermediate          ✅ Pruning & quantization       │
│                                                                          │
│  Best for:                               Best for:                       │
│  • Development & experimentation         • Production deployment         │
│  • Custom architectures                  • Edge device optimization      │
│  • Research                              • Maximum inference speed       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Why Use TAO for Reachy?

| Benefit | Impact |
|---------|--------|
| **Optimized for Jetson** | 2-3x faster inference on Xavier NX |
| **Direct TensorRT Export** | No ONNX intermediate step |
| **INT8 Quantization** | 50% smaller model, faster inference |
| **Pruning Support** | Remove unnecessary weights |
| **NVIDIA Support** | Professional-grade pipeline |

### 1.3 Important: TAO Uses ResNet-18, Not EfficientNet-B0

You'll notice that the TAO configuration uses **ResNet-18** as its backbone, while the rest of this curriculum uses **EfficientNet-B0 (HSEmotion)**. This is intentional:

| Aspect | PyTorch Pipeline (Guides 01-07) | TAO Pipeline (this guide) |
|--------|--------------------------------|---------------------------|
| **Backbone** | EfficientNet-B0 | ResNet-18 |
| **Weights** | HSEmotion `enet_b0_8_best_vgaf` | ImageNet |
| **Why** | Best accuracy with HSEmotion emotion-specific pre-training | TAO 4.x classification task has built-in ResNet support with optimized TensorRT export |
| **Export** | PyTorch → ONNX → TensorRT | TAO → .etlt → TensorRT (direct) |
| **Use case** | Development, experimentation, custom training | Production Jetson deployment when TAO's optimization matters |

**Which should you use?**
- **Start with PyTorch + EfficientNet-B0** for development and Gate A validation
- **Use TAO + ResNet-18** when you need maximum Jetson optimization and are ready for production deployment
- Both must independently pass Gate A (F1 ≥ 0.84) and Gate B (latency ≤ 120 ms) before deployment

### 1.4 TAO Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      TAO TOOLKIT WORKFLOW                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   Dataset    │    │  Pre-trained │    │    Spec      │              │
│  │  (images)    │───▶│    Model     │───▶│   Config     │              │
│  └──────────────┘    │  (backbone)  │    │   (.yaml)    │              │
│                      └──────────────┘    └──────────────┘              │
│                             │                   │                        │
│                             ▼                   ▼                        │
│                      ┌─────────────────────────────────┐                │
│                      │         TAO TRAINING            │                │
│                      │   (Docker container with GPU)   │                │
│                      └─────────────────────────────────┘                │
│                                    │                                     │
│                                    ▼                                     │
│                      ┌─────────────────────────────────┐                │
│                      │      Trained Model (.tlt)       │                │
│                      └─────────────────────────────────┘                │
│                                    │                                     │
│                     ┌──────────────┼──────────────┐                     │
│                     ▼              ▼              ▼                     │
│              ┌──────────┐   ┌──────────┐   ┌──────────┐                │
│              │  Prune   │   │  Export  │   │ Evaluate │                │
│              │ (reduce) │   │(TensorRT)│   │ (Gate A) │                │
│              └──────────┘   └──────────┘   └──────────┘                │
│                     │              │                                     │
│                     ▼              ▼                                     │
│              ┌──────────┐   ┌──────────┐                                │
│              │ Retrain  │   │ .engine  │───▶ Jetson Xavier NX          │
│              │(fine-tune│   │  file    │                                │
│              └──────────┘   └──────────┘                                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Environment Setup

### 2.1 Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Ubuntu | 20.04+ | `lsb_release -a` |
| Docker | 20.10+ | `docker --version` |
| NVIDIA Driver | 535+ | `nvidia-smi` |
| nvidia-container-toolkit | 1.14+ | `nvidia-container-cli --version` |
| GPU Memory | 8GB+ | `nvidia-smi` |

### 2.2 Quick Environment Check

```bash
# Run all checks at once
cat > check_tao_prereqs.sh << 'EOF'
#!/bin/bash
echo "=== TAO Prerequisites Check ==="

echo -n "Docker: "
docker --version 2>/dev/null || echo "NOT INSTALLED"

echo -n "Docker Compose: "
docker-compose --version 2>/dev/null || echo "NOT INSTALLED"

echo -n "NVIDIA Driver: "
nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null || echo "NOT INSTALLED"

echo -n "nvidia-container-toolkit: "
if docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi &>/dev/null; then
    echo "WORKING"
else
    echo "NOT WORKING"
fi

echo -n "GPU(s): "
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "NONE DETECTED"

echo "=== Check Complete ==="
EOF

chmod +x check_tao_prereqs.sh
./check_tao_prereqs.sh
```

### 2.3 Install NVIDIA Container Toolkit (if needed)

```bash
# Add NVIDIA package repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# Install
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Restart Docker
sudo systemctl restart docker

# Verify
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### 2.4 Set Up TAO Environment

```bash
# Navigate to TAO directory
cd /path/to/reachy_emotion/trainer/tao

# Run setup script (pulls images, creates directories, starts containers)
./setup_tao_env.sh
```

**Expected Output:**
```
=========================================
NVIDIA TAO Toolkit Environment Setup
=========================================
Checking prerequisites...
✓ Docker found
✓ Docker Compose found
✓ NVIDIA Docker runtime available
✓ Found 1 GPU(s)
Creating directory structure...
✓ Directories created
Pulling TAO Docker images (this may take a while)...
Pulling TAO 4.0.0 (training)...
Pulling TAO 5.3.0 (export)...
✓ TAO images pulled
Starting TAO containers...
✓ TAO training container running
✓ TAO export container running
Verifying GPU access in containers...
✓ GPU accessible in training container
✓ GPU accessible in export container

=========================================
TAO Environment Ready!
=========================================

Running containers:
NAMES              STATUS         PORTS
reachy-tao-train   Up 10 seconds
reachy-tao-export  Up 10 seconds

GPU Status:
0, NVIDIA GeForce RTX 3090, 24576 MiB, 500 MiB

Usage:
  Training:  docker exec -it reachy-tao-train bash
  Export:    docker exec -it reachy-tao-export bash
  Stop:      docker-compose -f docker-compose-tao.yml down
  Logs:      docker-compose -f docker-compose-tao.yml logs -f

Setup complete!
```

---

## 3. Understanding the TAO Configuration

### 3.1 Configuration File Structure

The TAO spec file (`specs/emotionnet_3cls.yaml`) controls all training parameters:

```yaml
# trainer/tao/specs/emotionnet_3cls.yaml

model:
  arch: "resnet18"              # Backbone architecture
  input_shape: [224, 224, 3]    # H, W, C format
  num_classes: 3                # happy, sad, neutral
  pretrained_weights: "imagenet"
  freeze_blocks: [0, 1]         # Transfer learning: freeze early layers
  dropout_rate: 0.3

dataset:
  train_data_path: "/workspace/data/train"
  val_data_path: "/workspace/data/test"
  classes: ["happy", "sad", "neutral"]
  
  augmentation:
    enable: true
    random_flip: true
    color_jitter: true
    mixup: true
    mixup_alpha: 0.2

training:
  batch_size: 32
  num_epochs: 50
  optimizer: "adam"
  learning_rate: 0.001
  
  lr_schedule:
    type: "cosine"
    warmup_epochs: 5
    min_lr: 0.00001
    
  early_stopping:
    enable: true
    patience: 10
    metric: "val_f1_macro"

gates:
  gate_a:
    min_f1_macro: 0.84
    min_balanced_accuracy: 0.85
```

### 3.2 Key Configuration Sections

| Section | Purpose | Key Parameters |
|---------|---------|----------------|
| **model** | Network architecture | arch, input_shape, num_classes |
| **dataset** | Data loading | paths, classes, augmentation |
| **training** | Training loop | epochs, learning rate, optimizer |
| **gates** | Quality thresholds | Gate A metrics |
| **logging** | Experiment tracking | MLflow, TensorBoard |

---

## 4. Training with TAO

### 4.1 Prepare Data for TAO

TAO expects a specific directory structure:

```bash
# Inside TAO container, data is mounted at /workspace/data/
/workspace/data/
├── train/
│   ├── happy/
│   │   ├── img_0001.jpg
│   │   ├── img_0002.jpg
│   │   └── ...
│   ├── sad/
│   │   ├── img_0001.jpg
│   │   └── ...
│   └── neutral/
│       ├── img_0001.jpg
│       └── ...
└── test/
    ├── happy/
    ├── sad/
    └── neutral/
```

**Verify data is accessible in container:**

```bash
# Enter TAO training container
docker exec -it reachy-tao-train bash

# Check data mount
ls -la /workspace/data/train/
# Should show: happy/ sad/ neutral/

# Count images
find /workspace/data/train -name "*.jpg" | wc -l
# Should show total training images
```

### 4.2 Start Training

```bash
# Inside TAO container
cd /workspace

# Run training with 3-class config
tao classification train \
    --experiment_spec_file=/workspace/specs/emotionnet_3cls.yaml \
    --results_dir=/workspace/experiments/emotionnet_3cls \
    --key=nvidia_tao_key
```

**Alternative: Run from host**

```bash
# From host machine
docker exec -it reachy-tao-train tao classification train \
    --experiment_spec_file=/workspace/specs/emotionnet_3cls.yaml \
    --results_dir=/workspace/experiments/emotionnet_3cls \
    --key=nvidia_tao_key
```

### 4.3 Training Output

```
============================================================
NVIDIA TAO Classification Training
Model: resnet18 (ImageNet pretrained)
Classes: 3 (happy, sad, neutral)
============================================================

Loading dataset...
  Train: 750 images (250 happy, 250 sad, 250 neutral)
  Val: 150 images (50 happy, 50 sad, 50 neutral)

Building model...
  Architecture: ResNet-18
  Frozen blocks: [0, 1]
  Trainable parameters: 1,234,567

Starting training...

Epoch 1/50
────────────────────────────────────────────────────────────
[Train] Loss: 0.6823 | Acc: 0.5640 | F1: 0.5412
[Val]   Loss: 0.6234 | Acc: 0.6000 | F1: 0.5823
LR: 0.0002 (warmup)
────────────────────────────────────────────────────────────

Epoch 10/50
────────────────────────────────────────────────────────────
[Train] Loss: 0.3456 | Acc: 0.8420 | F1: 0.8312
[Val]   Loss: 0.3123 | Acc: 0.8600 | F1: 0.8534
LR: 0.0009
★ New best model saved: emotionnet_3cls_epoch_10.tlt
────────────────────────────────────────────────────────────

...

Epoch 50/50
────────────────────────────────────────────────────────────
[Train] Loss: 0.1234 | Acc: 0.9320 | F1: 0.9245
[Val]   Loss: 0.1456 | Acc: 0.9100 | F1: 0.9056
LR: 0.00001
────────────────────────────────────────────────────────────

============================================================
Training Complete!
Best model: emotionnet_3cls_epoch_45.tlt (Val F1: 0.9089)
============================================================
```

### 4.4 Monitor Training

**TensorBoard (recommended):**

```bash
# From host
tensorboard --logdir=/path/to/reachy_emotion/trainer/tao/experiments/tensorboard --port=6006

# Open browser: http://localhost:6006
```

**MLflow:**

```bash
# From host
mlflow ui --backend-store-uri file:///path/to/reachy_emotion/mlruns --port=5000

# Open browser: http://localhost:5000
```

---

## 5. Evaluating the TAO Model

### 5.1 Run Evaluation

```bash
# Inside TAO container
tao classification evaluate \
    --experiment_spec_file=/workspace/specs/emotionnet_3cls.yaml \
    --model_path=/workspace/experiments/emotionnet_3cls/weights/emotionnet_3cls_epoch_45.tlt \
    --results_dir=/workspace/experiments/emotionnet_3cls/eval \
    --key=nvidia_tao_key
```

### 5.2 Evaluation Output

```
============================================================
TAO Classification Evaluation
============================================================

Loading model: emotionnet_3cls_epoch_45.tlt
Evaluating on test set: 100 images

Results:
──────────────────────────────────────────────────────────────
Metric                  Value      Gate A Threshold
──────────────────────────────────────────────────────────────
Accuracy                0.9100     -
Macro F1                0.9089     ≥ 0.84 ✅
Balanced Accuracy       0.9100     ≥ 0.85 ✅
Per-class F1 (happy)    0.9200     ≥ 0.75 ✅
Per-class F1 (sad)      0.8978     ≥ 0.75 ✅
──────────────────────────────────────────────────────────────

Confusion Matrix:
              Predicted
            happy    sad
Actual happy   46      4
       sad      5     45

============================================================
✅ GATE A PASSED
============================================================
```

---

## 6. Exporting to TensorRT

### 6.1 Export Process Overview

```
TAO Model (.tlt)
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│                    TAO EXPORT                                 │
│                                                               │
│  Options:                                                     │
│  ├── FP32 (default, most accurate)                           │
│  ├── FP16 (2x faster, minimal accuracy loss)                 │
│  └── INT8 (4x faster, requires calibration)                  │
│                                                               │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
TensorRT Engine (.engine)
       │
       ▼
Jetson Xavier NX (DeepStream)
```

### 6.2 Export to FP16 (Recommended)

```bash
# Switch to export container
docker exec -it reachy-tao-export bash

# Export to TensorRT FP16
tao classification export \
    --model_path=/workspace/experiments/emotionnet_3cls/weights/emotionnet_3cls_epoch_45.tlt \
    --output_file=/workspace/engines/emotionnet_3cls_fp16.etlt \
    --key=nvidia_tao_key \
    --data_type=fp16

# Convert to TensorRT engine for Jetson
tao converter \
    /workspace/engines/emotionnet_3cls_fp16.etlt \
    -k nvidia_tao_key \
    -d 3,224,224 \
    -o predictions/Softmax \
    -e /workspace/engines/emotionnet_3cls_fp16.engine \
    -t fp16 \
    -m 1 \
    -b 1
```

### 6.3 Export to INT8 (Maximum Speed)

INT8 requires calibration data for accuracy:

```bash
# Create calibration cache
tao classification calibration_tensorfile \
    --experiment_spec_file=/workspace/specs/emotionnet_3cls.yaml \
    --model_path=/workspace/experiments/emotionnet_3cls/weights/emotionnet_3cls_epoch_45.tlt \
    --cal_image_dir=/workspace/calibration \
    --cal_cache_file=/workspace/engines/calibration.bin \
    --cal_batch_size=8 \
    --max_batches=50 \
    --key=nvidia_tao_key

# Export with INT8
tao converter \
    /workspace/engines/emotionnet_3cls_fp16.etlt \
    -k nvidia_tao_key \
    -d 3,224,224 \
    -o predictions/Softmax \
    -e /workspace/engines/emotionnet_3cls_int8.engine \
    -t int8 \
    -c /workspace/engines/calibration.bin \
    -b 1
```

### 6.4 Compare Export Formats

| Format | File Size | Jetson Latency | Accuracy Impact |
|--------|-----------|----------------|-----------------|
| FP32 | ~45 MB | ~80 ms | Baseline |
| FP16 | ~23 MB | ~40 ms | < 0.5% drop |
| INT8 | ~12 MB | ~25 ms | 1-2% drop |

**Recommendation**: Use FP16 for best accuracy/speed balance.

---

## 7. Deploying to Jetson Xavier NX

### 7.1 Transfer Engine to Jetson

```bash
# From Ubuntu 1 (training server)
scp /path/to/reachy_emotion/trainer/tao/experiments/engines/emotionnet_3cls_fp16.engine \
    jetson@10.0.4.150:/opt/reachy/models/
```

### 7.2 Update DeepStream Configuration

```bash
# On Jetson
cat > /opt/reachy/configs/emotion_inference.txt << 'EOF'
[property]
gpu-id=0
net-scale-factor=0.0039215697906911373
model-engine-file=/opt/reachy/models/emotionnet_3cls_fp16.engine
labelfile-path=/opt/reachy/configs/emotion_labels.txt
batch-size=1
network-mode=2  # FP16
num-detected-classes=2
gie-unique-id=1
output-blob-names=predictions/Softmax
EOF
```

### 7.3 Verify on Jetson (Gate B)

```bash
# On Jetson
python3 /opt/reachy/scripts/benchmark_engine.py \
    --engine /opt/reachy/models/emotionnet_3cls_fp16.engine \
    --iterations 1000

# Expected output:
# ============================================================
# TensorRT Engine Benchmark
# ============================================================
# Engine: emotionnet_3cls_fp16.engine
# Precision: FP16
# 
# Performance:
#   Latency p50: 35.2 ms ✅ (threshold: < 120 ms)
#   Latency p95: 42.1 ms ✅ (threshold: < 250 ms)
#   FPS: 28.4 ✅ (threshold: > 25)
#   GPU Memory: 0.85 GB ✅ (threshold: < 2.5 GB)
# 
# ✅ GATE B PASSED
# ============================================================
```

---

## 8. TAO Commands Reference

### Training Commands

| Command | Purpose |
|---------|---------|
| `tao classification train` | Train a model |
| `tao classification evaluate` | Evaluate model |
| `tao classification inference` | Run inference |
| `tao classification prune` | Prune model weights |

### Export Commands

| Command | Purpose |
|---------|---------|
| `tao classification export` | Export to ETLT |
| `tao converter` | Convert to TensorRT |
| `tao classification calibration_tensorfile` | Generate INT8 calibration |

### Utility Commands

| Command | Purpose |
|---------|---------|
| `tao info` | Show TAO version info |
| `tao list` | List available models |
| `tao download` | Download pre-trained models |

---

## 9. Troubleshooting

### Issue: "Out of memory" during training

```bash
# Reduce batch size in config
training:
  batch_size: 16  # Reduced from 32
```

### Issue: TAO container won't start

```bash
# Check Docker logs
docker-compose -f docker-compose-tao.yml logs tao-train

# Restart containers
docker-compose -f docker-compose-tao.yml down
docker-compose -f docker-compose-tao.yml up -d
```

### Issue: "Permission denied" on mounted volumes

```bash
# Fix permissions
sudo chown -R $(id -u):$(id -g) /media/project_data/reachy_emotion/
```

### Issue: TensorRT conversion fails

```bash
# Ensure you're using the export container (TAO 5.3.0)
docker exec -it reachy-tao-export bash

# Check TensorRT version
tao info --verbose
```

---

## 10. TAO vs. PyTorch Decision Guide

| Scenario | Recommendation |
|----------|---------------|
| **Rapid prototyping** | PyTorch (Guides 01-07) |
| **Custom architectures** | PyTorch |
| **Production Jetson deployment** | TAO (this guide) |
| **Maximum inference speed** | TAO with INT8 |
| **Debugging training issues** | PyTorch |
| **Enterprise deployment** | TAO |

**For the Reachy project**: 
- Use **PyTorch** for development and experimentation
- Use **TAO** for final production deployment to Jetson

---

## 11. Summary

### What You Learned

1. ✅ TAO Toolkit provides optimized training for NVIDIA hardware
2. ✅ Docker containers isolate the TAO environment
3. ✅ Spec files control all training parameters
4. ✅ FP16 export provides best accuracy/speed tradeoff
5. ✅ INT8 requires calibration but maximizes speed
6. ✅ Direct TensorRT export avoids ONNX conversion

### Key Commands

```bash
# Setup
./setup_tao_env.sh

# Train
docker exec -it reachy-tao-train tao classification train \
    --experiment_spec_file=/workspace/specs/emotionnet_3cls.yaml \
    --results_dir=/workspace/experiments/emotionnet_3cls

# Export
docker exec -it reachy-tao-export tao converter \
    /workspace/engines/emotionnet_3cls.etlt \
    -k nvidia_tao_key \
    -e /workspace/engines/emotionnet_3cls_fp16.engine \
    -t fp16
```

### Files Reference

```
trainer/tao/
├── setup_tao_env.sh           # Environment setup script
├── docker-compose-tao.yml     # Container definitions
├── specs/
│   ├── emotionnet_3cls.yaml   # 3-class training config
│   └── emotionnet_6cls.yaml   # 6-class training config
└── experiments/               # Training outputs
    ├── weights/               # Trained models (.tlt)
    ├── tensorboard/           # Training curves
    └── engines/               # TensorRT exports
```

---

*Continue to [Guide 12: n8n Orchestration Integration](12_N8N_ORCHESTRATION_GUIDE.md) for automated training workflows.*
