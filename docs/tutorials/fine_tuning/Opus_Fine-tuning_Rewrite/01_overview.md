# Fine-Tuning Tutorials: Overview

## Purpose

These tutorials cover the complete set of fine-tuning approaches available for
the Reachy emotion recognition pipeline. The project originally relied
exclusively on NVIDIA TAO Toolkit with the EmotionNet architecture (ResNet-18
backbone). Recent advances in lightweight facial emotion models — notably the
**HSEmotion** family and its production-ready successor **EmotiEffLib** — provide
alternative and complementary paths that are easier to iterate on, require no
Docker/TAO infrastructure, and achieve state-of-the-art accuracy on standard
benchmarks (AffectNet, FER2013, RAF-DB).

This index describes the three training paths, when to use each one, and how
they fit into the Reachy deployment topology.

---

## Tutorial Index

| # | Tutorial | Path | Audience |
|---|----------|------|----------|
| 01 | **This overview** | `01_overview.md` | Everyone |
| 02 | [TAO EmotionNet Quick-Start](02_tao_emotionnet_quickstart.md) | TAO 4.x + Docker | Operators running the existing Jetson pipeline |
| 03 | [HSEmotion Fine-Tuning (PyTorch)](03_hsemotion_finetuning.md) | PyTorch native | ML engineers iterating on model accuracy |
| 04 | [EmotiEffLib Integration Guide](04_emotiefflib_guide.md) | `pip install emotiefflib` | Developers needing a drop-in inference API |
| 05 | [Multimodal Emotion Recognition](05_multimodal_emotion.md) | Audio + Visual | Researchers exploring audiovisual fusion |
| 06 | [Model Comparison & Selection](06_model_comparison.md) | Reference | Decision-makers choosing an approach |

---

## Three Training Paths at a Glance

### Path A — NVIDIA TAO EmotionNet (existing)

- **Architecture**: ResNet-18 (ImageNet-pretrained), configurable class count
- **Toolchain**: TAO 4.x for training, TAO 5.3 for ONNX/TRT export
- **Infrastructure**: Requires Docker containers (`reachy-tao-train`, `reachy-tao-export`)
- **Deployment**: TensorRT engine on Jetson Xavier NX via DeepStream 6.x
- **When to use**: Production deployments where the TAO + DeepStream pipeline is
  already running and you want to retrain with new labeled data without changing
  the serving stack.

### Path B — HSEmotion / EmotiEffLib (new)

- **Architecture**: EfficientNet-B0/B2, MobileFaceNet, MobileViT
- **Toolchain**: Pure PyTorch (or ONNX Runtime) — no Docker required
- **Infrastructure**: Any GPU machine (or even CPU for inference)
- **Deployment**: ONNX export → TensorRT via `trtexec`, or direct ONNX Runtime
  inference
- **When to use**: Rapid experimentation, higher baseline accuracy on standard
  benchmarks, lighter model footprint, or when TAO infrastructure is
  unavailable.
- **Key repositories**:
  - [av-savchenko/hsemotion](https://github.com/av-savchenko/hsemotion) — PyTorch training code and pretrained weights
  - [sb-ai-lab/EmotiEffLib](https://github.com/sb-ai-lab/EmotiEffLib) — Production library with Torch + ONNX backends

### Path C — Multimodal (audiovisual fusion) (exploratory)

- **Architecture**: Visual backbone + audio encoder + fusion head
- **Toolchain**: PyTorch, librosa/torchaudio
- **When to use**: Research scenarios where audio context (speech prosody, tone)
  improves emotion classification beyond face-only models.
- **Key repositories**:
  - [bichuyen99/Audiovisual_emotion_recognition](https://github.com/bichuyen99/Audiovisual_emotion_recognition)
  - [She-yh/End-to-End-Multimodal-emotion-recognition](https://github.com/She-yh/End-to-End-Multimodal-emotion-recognition)

---

## How They Fit into the Reachy Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Ubuntu 1 (Model Host)                        │
│                                                                  │
│  ┌─────────────┐   ┌─────────────────┐   ┌──────────────────┐  │
│  │ Path A: TAO │   │ Path B: PyTorch │   │ Path C: Multi-   │  │
│  │ train →     │   │ hsemotion /     │   │ modal research   │  │
│  │ export TRT  │   │ emotiefflib     │   │ (audio+visual)   │  │
│  └──────┬──────┘   └───────┬─────────┘   └───────┬──────────┘  │
│         │                  │                      │              │
│         ▼                  ▼                      ▼              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │               MLflow Experiment Tracking                 │   │
│  │  (all paths log metrics, artifacts, dataset hashes)      │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                  │                                     │
│         ▼                  ▼                                     │
│  ┌──────────────────────────────────────┐                       │
│  │  TensorRT Engine (.engine / .onnx)   │                       │
│  └──────────────────┬───────────────────┘                       │
│                     │                                            │
└─────────────────────┼────────────────────────────────────────────┘
                      │  scp / API deploy
┌─────────────────────┼────────────────────────────────────────────┐
│                     ▼         Jetson Xavier NX (Edge)            │
│  ┌──────────────────────────────────────┐                       │
│  │  DeepStream 6.x pipeline             │                       │
│  │  PGIE (face detect) → tracker →      │                       │
│  │  SGIE (emotion classify)             │                       │
│  └──────────────────────────────────────┘                       │
└──────────────────────────────────────────────────────────────────┘
```

Both Path A and Path B can produce TensorRT engines that slot into the same
DeepStream pipeline on Jetson. Path B models are exported to ONNX first, then
converted via `trtexec` — the DeepStream `nvinfer` plugin can consume ONNX
models directly.

---

## Prerequisites

| Requirement | Path A (TAO) | Path B (HSEmotion) | Path C (Multimodal) |
|-------------|-------------|--------------------|--------------------|
| GPU | Required (CUDA) | Recommended | Required |
| Docker | Required (TAO containers) | Not required | Not required |
| Python | 3.8+ | 3.8+ | 3.8+ |
| PyTorch | Via TAO container | 1.13+ | 1.13+ |
| ONNX Runtime | — | Optional (for ONNX backend) | — |
| TAO Toolkit | 4.x + 5.3 | Not required | Not required |
| MLflow | Recommended | Recommended | Recommended |
| Disk space | ~20 GB (containers + models) | ~2 GB (models) | ~5 GB (models + audio) |

---

## Recommended Reading Order

1. Start with [06_model_comparison.md](06_model_comparison.md) if you need to
   **choose** between approaches.
2. For the existing TAO pipeline, follow [02_tao_emotionnet_quickstart.md](02_tao_emotionnet_quickstart.md).
3. For HSEmotion fine-tuning from scratch, follow
   [03_hsemotion_finetuning.md](03_hsemotion_finetuning.md).
4. For quick inference with a pretrained model, follow
   [04_emotiefflib_guide.md](04_emotiefflib_guide.md).
5. For research-oriented multimodal work, see
   [05_multimodal_emotion.md](05_multimodal_emotion.md).

---

## Related Project Resources

- Training orchestrator: `trainer/train_emotionnet.py`
- TAO specs: `trainer/tao/specs/emotionnet_2cls.yaml`, `trainer/tao/specs/emotionnet_6cls.yaml`
- Dataset preparation: `trainer/prepare_dataset.py`
- TensorRT export: `trainer/export_to_trt.py`
- MLflow tracking: `trainer/mlflow_tracker.py`
- Architecture decision: `memory-bank/decisions/004-emotionnet-tao-toolchain.md`
- DeepStream deployment: `docs/gpt/2025-10-15-DeepStream emotion classification.md`
