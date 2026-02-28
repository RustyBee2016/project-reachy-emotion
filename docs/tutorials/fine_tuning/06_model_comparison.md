# Tutorial 06: Model Comparison & Selection Guide

## Overview

This guide compares the three training paths available for the Reachy emotion
recognition pipeline and provides decision criteria for choosing between them.

---

## Head-to-Head Comparison

### Architecture & Accuracy

| Aspect | TAO EmotionNet (Path A) | HSEmotion / EmotiEffLib (Path B) | Multimodal (Path C) |
|--------|------------------------|----------------------------------|---------------------|
| **Backbone** | ResNet-18 | EfficientNet-B0/B2, MobileFaceNet, MobileViT | EfficientNet + Wav2Vec2/VGGish |
| **Parameters** | ~11.2 M | ~5.3 M (B0) / ~9.1 M (B2) / ~3.4 M (MBF) | ~15-25 M (combined) |
| **Pretrained on** | ImageNet (generic) | AffectNet (emotion-specific) | AffectNet + audio datasets |
| **AffectNet accuracy** | N/A (not benchmarked) | 61% (B0) / 63% (B2) / 66.5% (B2-7cls) | ~45% F1 (Aff-Wild2) |
| **Model size** | ~44 MB (.tlt) | ~20 MB (B0) / ~30 MB (B2) / ~14 MB (MBF) | ~80-120 MB (combined) |
| **Input size** | 224×224 | 224×224 (B0) / 260×260 (B2) / 112×112 (MBF) | 224×224 + audio |
| **Classes supported** | Configurable (2, 6, custom) | 7 or 8 (fine-tunable to any) | 8 (configurable) |

### Infrastructure & Tooling

| Aspect | TAO EmotionNet (Path A) | HSEmotion / EmotiEffLib (Path B) | Multimodal (Path C) |
|--------|------------------------|----------------------------------|---------------------|
| **Installation** | Docker + NGC CLI + TAO containers | `pip install emotiefflib[torch]` | Manual (clone repos) |
| **Training framework** | TAO CLI (YAML configs) | Native PyTorch | Native PyTorch |
| **Docker required** | Yes (TAO 4.x + 5.3) | No | No |
| **GPU required** | Yes (training + export) | Recommended (CPU possible) | Yes |
| **Export format** | .etlt → TensorRT | ONNX → TensorRT | ONNX → TensorRT |
| **DeepStream compat** | Native (TAO integration) | Via ONNX → trtexec | Requires custom plugin |
| **MLflow integration** | Built-in (existing scripts) | Manual (straightforward) | Manual |
| **Disk space** | ~20 GB (containers) | ~2 GB (models + deps) | ~5 GB (models + audio) |

### Development Experience

| Aspect | TAO EmotionNet (Path A) | HSEmotion / EmotiEffLib (Path B) | Multimodal (Path C) |
|--------|------------------------|----------------------------------|---------------------|
| **Setup time** | ~2 hours (containers, NGC) | ~5 minutes (pip install) | ~30 minutes (repos + deps) |
| **Training iteration** | Slow (container startup + CLI) | Fast (native Python/Jupyter) | Medium (feature extraction) |
| **Jupyter support** | Limited (TAO CLI-centric) | Extensive (15+ notebooks) | 2 notebooks |
| **Debugging** | Opaque (Docker logs) | Transparent (standard PyTorch) | Standard PyTorch |
| **Community** | NVIDIA forums | GitHub + academic papers | Small (thesis projects) |
| **License** | TAO EULA (NGC account) | Apache-2.0 (fully open) | MIT / Apache-2.0 |
| **Active development** | TAO evolving (version compat issues) | EmotiEffLib v1.1.1 (Sep 2025) | Archived |

---

## Decision Matrix

### Choose Path A (TAO EmotionNet) when:

- The TAO + DeepStream pipeline is already running on the Jetson
- You need to retrain with new labeled data without changing the serving stack
- Your organization has NVIDIA enterprise support
- The 2-class or 6-class config meets accuracy requirements
- You prefer YAML-driven configuration over writing Python training code

### Choose Path B (HSEmotion / EmotiEffLib) when:

- You want faster iteration cycles (no Docker startup)
- You need higher baseline accuracy (AffectNet-pretrained backbone)
- You want to use Jupyter notebooks for interactive development
- You're fine-tuning with a small dataset (emotion-pretrained features help)
- You need a lighter model (5 MB vs 44 MB)
- You want a fully open-source pipeline (Apache-2.0)
- You want to compare multiple backbones (B0, B2, MobileFaceNet, MobileViT)

### Choose Path C (Multimodal) when:

- You have access to audio alongside video
- Visual-only accuracy is insufficient for your use case
- You're doing offline analysis (not real-time)
- You're researching emotion recognition approaches
- Latency constraints are relaxed (no Gate B requirement)

---

## Recommended Approach for the Reachy Project

### Phase 1: Use Both A and B

1. **Production (Path A)**: Keep the TAO EmotionNet pipeline for the existing
   Jetson deployment. It's proven and integrated.
2. **Experimentation (Path B)**: Use EmotiEffLib for rapid experimentation,
   model comparison, and dataset quality assessment. Export the best model to
   ONNX → TRT when ready.

### Phase 2: Evaluate B as Production Alternative

1. Fine-tune an EfficientNet-B0 model using the approach in
   [03_hsemotion_finetuning.md](03_hsemotion_finetuning.md).
2. Export to ONNX → TensorRT.
3. Run side-by-side evaluation against the TAO model on the same test set.
4. If Path B meets Gate A and Gate B requirements, consider migrating to
   simplify the training infrastructure.

### Phase 3: Explore Multimodal (optional)

If the Reachy robot gains microphone capability, evaluate audiovisual fusion
offline to quantify the accuracy improvement over visual-only.

---

## Notebook Ecosystem Summary

The HSEmotion/EmotiEffLib ecosystem provides an extensive collection of Jupyter
notebooks that can be adapted for the Reachy project:

### EmotiEffLib Training Notebooks

| Notebook | Purpose | Reachy relevance |
|----------|---------|------------------|
| `affectnet/train_emotions-pytorch.ipynb` | Core PyTorch training | **High** — adapt for 2/6-class |
| `affectnet/evaluate_affectnet_march2021_pytorch.ipynb` | Model evaluation | **High** — evaluation pipeline |
| `affectnet/train_emotions-pytorch-afew-vgaf.ipynb` | Video dataset training | **Medium** — video-aware training |
| `display_emotions.ipynb` | GradCAM visualization | **High** — model interpretability |
| `video_summarizer.ipynb` | Video emotion analysis | **Medium** — offline analysis |
| `train_faces_torch.ipynb` | VGGFace2 pretraining | **Low** — only if custom pretraining |
| `ABAW/abaw*_train.ipynb` | Competition benchmarks | **Low** — reference only |
| `personalized_models/*.ipynb` | User-specific adaptation | **Medium** — personalized responses |

### HSEmotion Demo Notebook

| Notebook | Purpose | Reachy relevance |
|----------|---------|------------------|
| `demo/test_hsemotion_package.ipynb` | API demo + face detection | **High** — quick validation |

### Multimodal Notebooks

| Notebook | Purpose | Reachy relevance |
|----------|---------|------------------|
| `audiovisual_emo_reg.ipynb` (bichuyen99) | AV fusion training | **Low** — research reference |
| `testing.ipynb` (bichuyen99) | AV model evaluation | **Low** — research reference |

---

## Performance Benchmarks (Estimated)

These are estimated performance figures based on published benchmarks and model
characteristics. Actual performance depends on the Reachy dataset.

### Inference latency (Jetson Xavier NX, FP16)

| Model | Latency (est.) | Meets Gate B (<120ms P50) |
|-------|----------------|---------------------------|
| TAO EmotionNet (ResNet-18) | ~15-25 ms | Yes |
| EfficientNet-B0 (ONNX→TRT) | ~10-20 ms | Yes |
| EfficientNet-B2 (ONNX→TRT) | ~25-40 ms | Yes |
| MobileFaceNet (ONNX→TRT) | ~5-10 ms | Yes |
| Multimodal (visual + audio) | ~80-150 ms | Marginal |

### Memory footprint (Jetson Xavier NX)

| Model | GPU Memory (est.) | Meets Gate B (<2.5 GB) |
|-------|-------------------|------------------------|
| TAO EmotionNet | ~0.8-1.2 GB | Yes |
| EfficientNet-B0 | ~0.4-0.6 GB | Yes |
| EfficientNet-B2 | ~0.6-0.9 GB | Yes |
| MobileFaceNet | ~0.2-0.4 GB | Yes |
| Multimodal | ~1.5-2.5 GB | Marginal |

---

## Summary

| Criterion | Best Option |
|-----------|-------------|
| Fastest to production | Path A (TAO — already deployed) |
| Highest accuracy potential | Path B (HSEmotion — AffectNet-pretrained) |
| Fastest iteration | Path B (pip install, Jupyter, no Docker) |
| Lightest model | Path B (MobileFaceNet — 3.4M params, 14 MB) |
| Best with audio | Path C (audiovisual fusion) |
| Most notebooks/tutorials | Path B (15+ notebooks from EmotiEffLib) |
| Simplest infrastructure | Path B (pip install only) |
| Best Jetson integration | Path A (native TAO → DeepStream) |

The recommended strategy is to **use Path A for production** and **Path B for
experimentation**, with Path B potentially replacing Path A once validated
against the quality gates.
