# Guide 02: Environment Setup

**Duration**: 1-2 hours  
**Difficulty**: Beginner  
**Prerequisites**: Guide 01 complete

---

## Learning Objectives

By the end of this guide, you will:
- [ ] Have Python environment set up
- [ ] Have PyTorch installed with GPU support
- [ ] Have all training dependencies installed
- [ ] Verify GPU is accessible
- [ ] Understand the project structure

---

## 1. System Requirements

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | NVIDIA GTX 1080 (8GB) | NVIDIA RTX 3090 (24GB) |
| RAM | 16 GB | 32 GB |
| Storage | 50 GB free | 100 GB free |
| CPU | 4 cores | 8+ cores |

### Software Requirements

| Software | Version | Purpose |
|----------|---------|---------|
| Ubuntu | 20.04 LTS | Operating system |
| Python | 3.10+ | Programming language |
| CUDA | 11.8+ | GPU acceleration |
| cuDNN | 8.6+ | Deep learning primitives |

---

## 2. Connect to Training Server

The training happens on **Ubuntu 1** (10.0.4.130), which has the GPU.

```bash
# SSH to Ubuntu 1
ssh your_username@10.0.4.130

# Verify you're on the right machine
hostname
# Should show: ubuntu1 or similar

# Check GPU is available
nvidia-smi
```

Expected output:
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.104.05   Driver Version: 535.104.05   CUDA Version: 12.2     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  NVIDIA GeForce ...  Off  | 00000000:01:00.0 Off |                  N/A |
| 30%   45C    P8    20W / 350W |    500MiB / 24576MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
```

**If you don't see a GPU**: Contact your system administrator.

---

## 3. Set Up Python Environment

### Step 3.1: Create Virtual Environment

```bash
# Navigate to project directory
cd /path/to/reachy_emotion

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Verify Python version
python --version
# Should be 3.10 or higher
```

### Step 3.2: Upgrade pip

```bash
pip install --upgrade pip setuptools wheel
```

### Step 3.3: Install PyTorch with CUDA

```bash
# Install PyTorch with CUDA 11.8 support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Step 3.4: Verify PyTorch GPU Access

```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
```

Expected output:
```
PyTorch: 2.1.0+cu118
CUDA available: True
GPU: NVIDIA GeForce RTX 3090
```

**If CUDA is not available**: 
1. Check NVIDIA drivers: `nvidia-smi`
2. Check CUDA version matches PyTorch
3. Reinstall PyTorch with correct CUDA version

---

## 4. Install Training Dependencies

### Step 4.1: Install Core Dependencies

```bash
# Install from requirements file
pip install -r requirements-phase1.txt
pip install -r requirements-phase2.txt
```

### Step 4.2: Install Additional ML Dependencies

```bash
# Deep learning utilities
pip install timm              # Pre-trained models
pip install albumentations    # Image augmentation
pip install opencv-python     # Image processing

# Experiment tracking
pip install mlflow            # Experiment tracking
pip install tensorboard       # Training visualization

# Metrics and analysis
pip install scikit-learn      # ML metrics
pip install scipy             # Statistical functions
pip install matplotlib        # Plotting
pip install seaborn           # Statistical visualization
```

### Step 4.3: Verify All Imports Work

```bash
python -c "
import torch
import torchvision
import timm
import albumentations
import cv2
import mlflow
import sklearn
print('All imports successful!')
"
```

---

## 5. Project Structure Overview

```
reachy_emotion/
├── trainer/                    # Training code
│   ├── train_resnet50.py       # Main training script
│   ├── fer_finetune/           # Fine-tuning module
│   │   ├── __init__.py
│   │   ├── config.py           # Training configuration
│   │   ├── model.py            # ResNet-50 model
│   │   ├── dataset.py          # Data loading
│   │   ├── train.py            # Training loop
│   │   ├── evaluate.py         # Metrics computation
│   │   ├── export.py           # ONNX export
│   │   └── specs/              # Config files
│   │       ├── resnet50_emotion_2cls.yaml
│   │       └── resnet50_emotion_8cls.yaml
│   └── tao/                    # TAO Toolkit (alternative)
│
├── data/                       # Training data (create this)
│   ├── train/                  # Training images
│   │   ├── happy/
│   │   └── sad/
│   └── val/                    # Validation images
│       ├── happy/
│       └── sad/
│
├── outputs/                    # Training outputs (created automatically)
│   ├── checkpoints/            # Model checkpoints
│   ├── logs/                   # Training logs
│   └── exports/                # ONNX exports
│
├── stats/                      # Statistical analysis
│   └── scripts/                # Analysis scripts
│
└── docs/                       # Documentation
    └── tutorials/
        └── fine_tuning/        # This guide!
```

---

## 6. Download Pre-trained Weights

### Step 6.1: Create Weights Directory

```bash
mkdir -p /media/project_data/ml_models/resnet50
```

### Step 6.2: Download Weights

The pre-trained weights should be available at the model storage path. If not:

```bash
# Option 1: Download from project storage (if available)
# scp admin@storage:/models/resnet50_affectnet_rafdb.pth /media/project_data/ml_models/resnet50/

# Option 2: Use ImageNet weights (fallback)
# The training script will automatically download ImageNet weights if custom weights aren't found
```

### Step 6.3: Verify Weights (if downloaded)

```bash
python -c "
import torch
weights_path = '/media/project_data/ml_models/resnet50/resnet50_affectnet_rafdb.pth'
try:
    checkpoint = torch.load(weights_path, map_location='cpu')
    print(f'Weights loaded successfully')
    print(f'Keys: {list(checkpoint.keys())[:5]}...')
except FileNotFoundError:
    print('Custom weights not found - will use ImageNet weights')
"
```

---

## 7. Verify Training Setup

### Step 7.1: Run Import Test

```bash
cd /path/to/reachy_emotion

python -c "
from trainer.fer_finetune.config import TrainingConfig
from trainer.fer_finetune.model import EmotionClassifier
from trainer.fer_finetune.train import Trainer

print('✅ All training modules import successfully')
"
```

### Step 7.2: Create Test Model

```bash
python -c "
import torch
from trainer.fer_finetune.model import EmotionClassifier

# Create model
model = EmotionClassifier(
    backbone='resnet50',
    num_classes=2,
    dropout_rate=0.3,
)

# Move to GPU
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = model.to(device)

# Test forward pass
dummy_input = torch.randn(1, 3, 224, 224).to(device)
output = model(dummy_input)

print(f'✅ Model created successfully')
print(f'   Device: {device}')
print(f'   Output shape: {output[\"logits\"].shape}')
print(f'   Total params: {model.get_total_params():,}')
print(f'   Trainable params: {model.get_trainable_params():,}')
"
```

Expected output:
```
✅ Model created successfully
   Device: cuda
   Output shape: torch.Size([1, 2])
   Total params: 23,510,082
   Trainable params: 4,098
```

### Step 7.3: Check Training Config

```bash
python -c "
from trainer.fer_finetune.config import TrainingConfig

# Load 2-class config
config = TrainingConfig.from_yaml('trainer/fer_finetune/specs/resnet50_emotion_2cls.yaml')

print('✅ Config loaded successfully')
print(f'   Model: {config.model.backbone}')
print(f'   Classes: {config.model.num_classes}')
print(f'   Epochs: {config.num_epochs}')
print(f'   Batch size: {config.data.batch_size}')
print(f'   Learning rate: {config.learning_rate}')
"
```

---

## 8. Common Setup Issues

### Issue: CUDA not available

```bash
# Check NVIDIA driver
nvidia-smi

# Check CUDA version
nvcc --version

# Reinstall PyTorch with matching CUDA version
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Issue: Out of memory

```bash
# Check GPU memory usage
nvidia-smi

# Kill other processes using GPU
# (Be careful - ask before killing others' processes)
```

### Issue: Module not found

```bash
# Make sure you're in the project directory
cd /path/to/reachy_emotion

# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements-phase1.txt
```

### Issue: Permission denied

```bash
# Check file permissions
ls -la /media/project_data/ml_models/

# Fix permissions if needed
sudo chown -R $USER:$USER /media/project_data/ml_models/
```

---

## 9. Environment Checklist

Before proceeding, verify:

| Check | Command | Expected |
|-------|---------|----------|
| Python version | `python --version` | 3.10+ |
| PyTorch installed | `python -c "import torch; print(torch.__version__)"` | 2.0+ |
| CUDA available | `python -c "import torch; print(torch.cuda.is_available())"` | True |
| GPU accessible | `nvidia-smi` | Shows GPU |
| Training modules | `python -c "from trainer.fer_finetune.train import Trainer"` | No error |
| Config loads | See Step 7.3 | Shows config values |

---

## 10. Summary

### What You've Done

1. ✅ Connected to training server (Ubuntu 1)
2. ✅ Created Python virtual environment
3. ✅ Installed PyTorch with CUDA support
4. ✅ Installed all training dependencies
5. ✅ Verified GPU access
6. ✅ Understood project structure
7. ✅ Verified training setup works

### What's Next

In the next guide, we'll prepare the training data:
- Understand data format requirements
- Organize images into train/val splits
- Apply data augmentation
- Create data loaders

---

## Self-Assessment

Rate your understanding (1-3):

| Concept | Rating |
|---------|--------|
| Virtual environment setup | __ |
| PyTorch GPU verification | __ |
| Project structure | __ |
| Troubleshooting common issues | __ |

---

*Next: [Guide 03: Data Preparation](03_DATA_PREPARATION.md)*
