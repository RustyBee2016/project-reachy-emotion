---
title: EmotionNet Toolchain — TAO 4.x (Training) and TAO 5.3 (Export)
kind: decision
owners: [rustybee255]
related: ["../requirements.md", "../index.md", "../../AGENTS_08.4.2.md"]
created: 2025-10-17
updated: 2025-10-17
status: active
---

# EmotionNet Toolchain — TAO 4.x (Training) and TAO 5.3 (Export)

## Context
EmotionNet fine-tuning requires NVIDIA TAO Toolkit 4.x. Exporting deployable TensorRT engines for DeepStream is performed with TAO 5.3. Using TAO 6.x for training is incompatible with our EmotionNet training flow and risks artifact mismatch.

## Decision / Content
- Training/fine-tuning MUST use **TAO 4.x**.
- Conversion/export to TensorRT engine MUST use **TAO 5.3**.
- Deployment targets **DeepStream 6.x / TensorRT 8.6+** on Jetson Xavier NX.
- CI/CD should enforce version checks to prevent accidental use of TAO 6.x for training.

## Consequences
- Two container environments are maintained (TAO 4.x for training; TAO 5.3 for export).
- Training specs (`emotion_train_2cls.yaml`) use TAO 4.x syntax. Export specs (`emotion_convert.yaml`, `emotion_export.yaml`) use TAO 5.3.
- Documentation and Makefile targets must clearly separate `train` (TAO 4.x) and `export` (TAO 5.3).

## Alternatives Considered
- TAO 6.x for training and export — rejected due to model/tooling incompatibility for EmotionNet in this project phase.

## Related
- Requirements: `memory-bank/requirements.md` (§6.2 Software Dependencies; §21 Model Packaging & Serving)
- Agents/Gates: `AGENTS_08.4.2.md` (deployment gates)

## Notes
Add a compatibility matrix to `requirements.md` and ensure DeepStream `nvinfer` configs are validated against the TAO 5.3-exported engine.

---

**Last Updated**: 2025-10-17  
**Owner**: Russell Bray
