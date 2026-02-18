# Guide 07: Export & Deployment Preparation

**Duration**: 1-2 hours  
**Difficulty**: Intermediate  
**Prerequisites**: Guide 06 complete, Gate A passed

---

## Learning Objectives

By the end of this guide, you will:
- [ ] Understand why we export to ONNX
- [ ] Know how to export a trained model
- [ ] Be able to verify the exported model
- [ ] Understand the deployment pipeline

---

## 1. Why Export to ONNX?

### What is ONNX?

**ONNX** (Open Neural Network Exchange) is a standard format for neural networks that works across different frameworks.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     WHY ONNX?                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Training (Ubuntu 1)              Deployment (Jetson)               │
│  ──────────────────               ───────────────────               │
│  PyTorch model                    TensorRT engine                   │
│  (.pth file)                      (.engine file)                    │
│                                                                      │
│       │                                  ▲                          │
│       │                                  │                          │
│       ▼                                  │                          │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │                    ONNX FORMAT                           │       │
│  │                    (.onnx file)                          │       │
│  │                                                          │       │
│  │  • Framework-independent                                 │       │
│  │  • Optimizable for different hardware                   │       │
│  │  • Standard interchange format                          │       │
│  └─────────────────────────────────────────────────────────┘       │
│                                                                      │
│  Flow: PyTorch → ONNX → TensorRT → Jetson                          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Benefits of ONNX

| Benefit | Description |
|---------|-------------|
| **Portability** | Works on different hardware (GPU, CPU, edge devices) |
| **Optimization** | Can be converted to TensorRT for faster inference |
| **Verification** | Can test model before deploying to Jetson |
| **Standardization** | Industry-standard format |

---

## 2. Exporting to ONNX

### Using the Training Script

```bash
# Export after training (if Gate A passed)
python trainer/train_efficientnet.py \
    --export-only \
    --resume outputs/checkpoints/best_model.pth \
    --export-path outputs/exports/my_model
```

### Expected Output

```
============================================================
EfficientNet-B0 Emotion Classifier Training
Model: enet_b0_8_best_vgaf (HSEmotion)
Run ID: export_20260128_235000
============================================================

Loading checkpoint: outputs/checkpoints/best_model.pth
Exporting model to: outputs/exports/my_model

Export successful!
  ONNX file: outputs/exports/my_model/emotion_classifier.onnx
  Input shape: [1, 3, 224, 224]
  Output shape: [1, 2]
  Precision: FP16

============================================================
EXPORT RESULTS
============================================================
{
  "onnx_path": "outputs/exports/my_model/emotion_classifier.onnx",
  "input_shape": [1, 3, 224, 224],
  "output_shape": [1, 2],
  "precision": "fp16",
  "opset_version": 17,
  "file_size_mb": 16.8
}
============================================================
```

### Manual Export Script

For more control over the export process:

```python
"""Manual ONNX export script."""

import torch
import torch.onnx
from pathlib import Path

from trainer.fer_finetune.model_efficientnet import load_pretrained_model

def export_to_onnx(
    checkpoint_path: str,
    output_path: str,
    num_classes: int = 2,
    input_size: int = 224,
    opset_version: int = 17,
    use_fp16: bool = True,
):
    """
    Export PyTorch model to ONNX format.
    
    Args:
        checkpoint_path: Path to trained model checkpoint
        output_path: Path for ONNX output file
        num_classes: Number of output classes
        input_size: Input image size
        opset_version: ONNX opset version
        use_fp16: Export in FP16 precision
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # Load model
    print(f"Loading model from: {checkpoint_path}")
    model = load_pretrained_model(
        checkpoint_path,
        num_classes=num_classes,
        device=device,
    )
    model.eval()
    
    # Convert to FP16 if requested
    if use_fp16 and device.type == 'cuda':
        model = model.half()
        dtype = torch.float16
    else:
        dtype = torch.float32
    
    # Create dummy input
    dummy_input = torch.randn(1, 3, input_size, input_size, dtype=dtype, device=device)
    
    # Create output directory
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Export to ONNX
    print(f"Exporting to: {output_path}")
    
    torch.onnx.export(
        model,
        dummy_input,
        str(output_path),
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'output': {0: 'batch_size'},
        },
    )
    
    # Verify export
    file_size = output_path.stat().st_size / (1024 * 1024)
    print(f"\nExport successful!")
    print(f"  File: {output_path}")
    print(f"  Size: {file_size:.2f} MB")
    print(f"  Precision: {'FP16' if use_fp16 else 'FP32'}")
    
    return str(output_path)

# Run export
onnx_path = export_to_onnx(
    checkpoint_path='outputs/checkpoints/best_model.pth',
    output_path='outputs/exports/emotion_classifier.onnx',
    num_classes=3,
    input_size=224,
    use_fp16=True,
)
```

---

## 3. Verifying the Exported Model

### Step 3.1: Check ONNX File

```python
"""Verify ONNX model structure."""

import onnx

def verify_onnx(onnx_path):
    """Check ONNX model is valid."""
    print(f"Loading ONNX model: {onnx_path}")
    
    # Load model
    model = onnx.load(onnx_path)
    
    # Check model is valid
    onnx.checker.check_model(model)
    print("✅ ONNX model is valid")
    
    # Print model info
    print(f"\nModel info:")
    print(f"  IR version: {model.ir_version}")
    print(f"  Opset version: {model.opset_import[0].version}")
    print(f"  Producer: {model.producer_name}")
    
    # Print inputs
    print(f"\nInputs:")
    for input in model.graph.input:
        shape = [d.dim_value for d in input.type.tensor_type.shape.dim]
        print(f"  {input.name}: {shape}")
    
    # Print outputs
    print(f"\nOutputs:")
    for output in model.graph.output:
        shape = [d.dim_value for d in output.type.tensor_type.shape.dim]
        print(f"  {output.name}: {shape}")

verify_onnx('outputs/exports/emotion_classifier.onnx')
```

Expected output:
```
Loading ONNX model: outputs/exports/emotion_classifier.onnx
✅ ONNX model is valid

Model info:
  IR version: 8
  Opset version: 17
  Producer: pytorch

Inputs:
  input: [1, 3, 224, 224]

Outputs:
  output: [1, 2]
```

### Step 3.2: Run Inference with ONNX Runtime

```python
"""Test ONNX model inference."""

import numpy as np
import onnxruntime as ort
from PIL import Image

def test_onnx_inference(onnx_path, test_image_path=None):
    """Run inference with ONNX Runtime."""
    
    # Create inference session
    print(f"Loading ONNX model: {onnx_path}")
    session = ort.InferenceSession(
        onnx_path,
        providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
    )
    
    # Get input/output info
    input_name = session.get_inputs()[0].name
    input_shape = session.get_inputs()[0].shape
    output_name = session.get_outputs()[0].name
    
    print(f"Input: {input_name}, shape: {input_shape}")
    print(f"Output: {output_name}")
    
    # Create test input
    if test_image_path:
        # Load and preprocess real image
        img = Image.open(test_image_path).convert('RGB')
        img = img.resize((224, 224))
        img_array = np.array(img).astype(np.float32) / 255.0
        
        # Normalize (ImageNet stats)
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        img_array = (img_array - mean) / std
        
        # Transpose to NCHW format
        img_array = img_array.transpose(2, 0, 1)
        input_data = img_array[np.newaxis, ...].astype(np.float16)
    else:
        # Use random input for testing
        input_data = np.random.randn(1, 3, 224, 224).astype(np.float16)
    
    # Run inference
    print(f"\nRunning inference...")
    outputs = session.run([output_name], {input_name: input_data})
    
    # Process output
    logits = outputs[0][0]
    probs = np.exp(logits) / np.sum(np.exp(logits))  # Softmax
    
    class_names = ['happy', 'sad']
    predicted_class = class_names[np.argmax(probs)]
    confidence = np.max(probs)
    
    print(f"\nResults:")
    print(f"  Predicted: {predicted_class}")
    print(f"  Confidence: {confidence:.2%}")
    print(f"  Probabilities: {dict(zip(class_names, probs))}")
    
    return predicted_class, confidence

# Test with random input
test_onnx_inference('outputs/exports/emotion_classifier.onnx')

# Test with real image (if available)
# test_onnx_inference('outputs/exports/emotion_classifier.onnx', 'test_image.jpg')
```

### Step 3.3: Compare PyTorch vs ONNX Outputs

```python
"""Verify ONNX output matches PyTorch."""

import torch
import numpy as np
import onnxruntime as ort

from trainer.fer_finetune.model_efficientnet import load_pretrained_model

def compare_pytorch_onnx(checkpoint_path, onnx_path, num_classes=3):
    """Compare outputs from PyTorch and ONNX models."""
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # Load PyTorch model
    pytorch_model = load_pretrained_model(checkpoint_path, num_classes, device)
    pytorch_model.eval()
    pytorch_model = pytorch_model.half()
    
    # Load ONNX model
    onnx_session = ort.InferenceSession(
        onnx_path,
        providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
    )
    
    # Create test input
    test_input = torch.randn(1, 3, 224, 224, dtype=torch.float16, device=device)
    
    # PyTorch inference
    with torch.no_grad():
        pytorch_output = pytorch_model(test_input)['logits']
    pytorch_output = pytorch_output.cpu().numpy()
    
    # ONNX inference
    onnx_input = test_input.cpu().numpy()
    onnx_output = onnx_session.run(None, {'input': onnx_input})[0]
    
    # Compare
    diff = np.abs(pytorch_output - onnx_output)
    max_diff = np.max(diff)
    mean_diff = np.mean(diff)
    
    print(f"PyTorch output: {pytorch_output}")
    print(f"ONNX output:    {onnx_output}")
    print(f"\nMax difference: {max_diff:.6f}")
    print(f"Mean difference: {mean_diff:.6f}")
    
    if max_diff < 0.01:
        print("✅ Outputs match (within tolerance)")
    else:
        print("⚠️ Outputs differ significantly")
    
    return max_diff < 0.01

# Run comparison
compare_pytorch_onnx(
    'outputs/checkpoints/best_model.pth',
    'outputs/exports/emotion_classifier.onnx',
)
```

---

## 4. Deployment Pipeline Overview

### From Training to Robot

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT PIPELINE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  UBUNTU 1 (Training Server)                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 1. Train model (PyTorch)                                     │   │
│  │ 2. Validate Gate A                                           │   │
│  │ 3. Export to ONNX                                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                          │                                          │
│                          │ SCP transfer                             │
│                          ▼                                          │
│  JETSON XAVIER NX (Robot)                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 4. Convert ONNX → TensorRT                                   │   │
│  │ 5. Validate Gate B (FPS, latency)                           │   │
│  │ 6. Deploy to DeepStream pipeline                            │   │
│  │ 7. Run real-time inference                                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Files to Transfer

| File | Source | Destination |
|------|--------|-------------|
| `emotion_classifier.onnx` | Ubuntu 1 | Jetson |
| `config.yaml` | Ubuntu 1 | Jetson |
| `class_names.txt` | Ubuntu 1 | Jetson |

### Transfer Command

```bash
# From Ubuntu 1, transfer to Jetson
scp outputs/exports/emotion_classifier.onnx jetson@10.0.4.150:/opt/reachy/models/

# Transfer config
scp trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml jetson@10.0.4.150:/opt/reachy/configs/
```

---

## 5. Gate B Preview

After deployment to Jetson, the model must pass **Gate B**:

| Metric | Threshold | Measured on |
|--------|-----------|-------------|
| FPS | ≥ 25 | Jetson |
| Latency p50 | ≤ 120 ms | Jetson |
| Latency p95 | ≤ 250 ms | Jetson |
| GPU Memory | ≤ 2.5 GB | Jetson |
| Macro F1 | ≥ 0.80 | Jetson (may be slightly lower than Gate A) |

### Why 3× Headroom Matters

EfficientNet-B0 runs at **~40 ms p50** on Jetson Xavier NX — well under the 120 ms limit. This isn't over-engineering; the extra budget is **shared with other workloads** on the same GPU:

```
Jetson Xavier NX — Shared GPU Budget (120 ms total)
────────────────────────────────────────────────────────────
Emotion inference (EfficientNet-B0):   ~40 ms  ██████████░░░░░░░░░░░░░░░░░░░░
Gesture planner (cue computation):     ~25 ms  ██████░░░░░░░░░░░░░░░░░░░░░░░░
Future multimodal features:            ~15 ms  ████░░░░░░░░░░░░░░░░░░░░░░░░░░
Thermal/overhead margin:               ~40 ms  ██████████░░░░░░░░░░░░░░░░░░░░
────────────────────────────────────────────────────────────
Total:                                 120 ms  ██████████████████████████████
```

Per requirements §7.1: *"Make sure this margin remains ≥2× after TensorRT optimization before clearing Gate B."*

If you switch to a larger model (e.g., EfficientNet-B2), the gesture planner and future features lose their budget. This is why B2 requires a full benchmark/validation cycle before approval (see §6.7).

Gate B validation is covered in the Phase 2 tutorials.

---

## 6. Export Checklist

Before considering export complete:

| Check | Status |
|-------|--------|
| Gate A passed | [ ] |
| ONNX file created | [ ] |
| ONNX model valid (checker) | [ ] |
| ONNX inference works | [ ] |
| PyTorch vs ONNX outputs match | [ ] |
| File size reasonable (<100 MB) | [ ] |
| Export metadata saved | [ ] |

---

## 7. Summary

### What You've Learned

1. ✅ Why we export to ONNX format
2. ✅ How to export a trained model
3. ✅ How to verify the exported model
4. ✅ The deployment pipeline overview
5. ✅ What comes next (Gate B on Jetson)

### Key Commands

```bash
# Export to ONNX
python trainer/train_efficientnet.py \
    --export-only \
    --resume outputs/checkpoints/best_model.pth \
    --export-path outputs/exports/

# Transfer to Jetson
scp outputs/exports/emotion_classifier.onnx jetson@10.0.4.150:/opt/reachy/models/
```

### Files Created

```
outputs/exports/
├── emotion_classifier.onnx    # ONNX model file
├── export_config.json         # Export configuration
└── export_log.txt             # Export log
```

---

## 8. Congratulations! 🎉

You've completed the Fine-Tuning Guide series!

### What You've Accomplished

| Guide | Topic | ✅ |
|-------|-------|---|
| 01 | What is Fine-Tuning | ✅ |
| 02 | Environment Setup | ✅ |
| 03 | Data Preparation | ✅ |
| 04 | Training Walkthrough | ✅ |
| 05 | Monitoring & Debugging | ✅ |
| 06 | Evaluation & Gate A | ✅ |
| 07 | Export & Deployment | ✅ |

### Skills Acquired

- ✅ Understand transfer learning and fine-tuning
- ✅ Set up training environment
- ✅ Prepare data for training
- ✅ Run and monitor training
- ✅ Debug common training issues
- ✅ Evaluate models against Gate A
- ✅ Export models for deployment

### Next Steps

1. **Practice**: Train models with different configurations
2. **Experiment**: Try different learning rates, batch sizes
3. **Improve**: Add more training data for better results
4. **Deploy**: Follow Phase 2 tutorials for Jetson deployment

---

*Great work completing the fine-tuning guides, Russ!* 🚀
