---
title: Model Deployment (Gate A/B/C Validation + Engine Export)
kind: runbook
owners: [Russell Bray]
related: [requirements.md#7, requirements.md#21, decisions/011-two-tier-gate-a-v1-deployment.md]
created: 2025-10-04
updated: 2026-04-14
status: active
---

# Runbook: Model Deployment

## Purpose
Step-by-step guide for deploying a fine-tuned EfficientNet-B0 emotion classifier (3-class:
`happy`, `sad`, `neutral`) to Jetson Xavier NX with Gate A/B/C validation, ONNX export,
TensorRT engine conversion, and DeepStream config update.

## Prerequisites
- Trained model checkpoint (`.pth` from PyTorch, e.g. `best_model.pth`)
- Checkpoint path example: `/media/rusty_admin/project_data/reachy_emotion/checkpoints/variant_1/var1_run_0107/best_model.pth`
- Access to Ubuntu 1 (`10.0.4.130`, training host) and Jetson (`10.0.4.150`, edge device)
- MLflow run ID with `dataset_hash` and metrics logged
- Python venv activated: `source /home/rusty_admin/projects/reachy_08.4.2/venv/bin/activate`

## Deployment Gates
Models must pass three gates before production rollout:

### Gate A — Offline Validation (Pre-Robot)

Gate A uses a **two-tier** system (see [ADR 011](../decisions/011-two-tier-gate-a-v1-deployment.md)):

| Sub-gate | Context | F1 macro | bAcc | Per-class F1 | ECE | Brier |
|----------|---------|----------|------|-------------|------|-------|
| **Gate A-val** | Synthetic validation | ≥ 0.84 | ≥ 0.85 | ≥ 0.75, floor ≥ 0.70 | ≤ 0.12 | ≤ 0.16 |
| **Gate A-deploy** | Real-world test (AffectNet) | ≥ 0.75 | ≥ 0.75 | ≥ 0.70, floor ≥ 0.65 | ≤ 0.12 | — |

- **Gate A-val** gates ONNX export during training.
- **Gate A-deploy** gates Jetson deployment.

**Procedure — Validation tier** (runs automatically at end of training):
```bash
# Automatic: run_efficientnet_pipeline.py calls gate_a_validator after training
# Manual re-evaluation:
python -m trainer.gate_a_validator \
  --predictions /media/rusty_admin/project_data/reachy_emotion/results/train/run_0107/predictions.npz \
  --tier validation \
  --output stats/results/gate_a_validation.json
```

**Procedure — Deploy tier** (against real-world AffectNet test set):
```bash
python -m trainer.gate_a_validator \
  --predictions /media/rusty_admin/project_data/reachy_emotion/results/test/run_0107/predictions.npz \
  --tier deploy \
  --output stats/results/gate_a_deploy_validation.json
```

**Expected Output** (`gate_a_deploy_validation.json`):
```json
{
  "thresholds": {"macro_f1": 0.75, "balanced_accuracy": 0.75, "per_class_f1": 0.70, "ece": 0.12},
  "metrics": {"f1_macro": 0.781, "balanced_accuracy": 0.780, "ece": 0.102},
  "per_class_f1": {"happy": 0.74, "sad": 0.85, "neutral": 0.76},
  "overall_pass": true
}
```

**If FAIL**: Investigate per-class confusion matrix, collect more diverse training data,
try hyperparameter sweep, or apply temperature scaling for calibration.

### Gate B — Robot Shadow Mode
**Environment**: Jetson Xavier NX (`10.0.4.150`), shadow deployment

**Criteria**:
- On-device latency: p50 ≤ 120 ms, p95 ≤ 250 ms
- GPU memory ≤ 2.5 GB
- Macro F1 ≥ 0.80; per-class F1 ≥ 0.72, floor ≥ 0.68

**Procedure**:
```bash
# 1. Export ONNX from checkpoint (on Ubuntu 1)
python -m trainer.fer_finetune.export \
  --checkpoint /media/rusty_admin/project_data/reachy_emotion/checkpoints/variant_1/var1_run_0107/best_model.pth \
  --output /media/rusty_admin/project_data/reachy_emotion/results/train/run_0107/export/model.onnx \
  --num-classes 3

# 2. Transfer ONNX to Jetson
scp /media/rusty_admin/project_data/reachy_emotion/results/train/run_0107/export/model.onnx \
    jetson:/opt/reachy/models/staging/emotion_efficientnet.onnx

# 3. Convert ONNX → TensorRT on Jetson (FP16)
ssh jetson
/usr/src/tensorrt/bin/trtexec \
  --onnx=/opt/reachy/models/staging/emotion_efficientnet.onnx \
  --saveEngine=/opt/reachy/models/staging/emotion_efficientnet.engine \
  --fp16 --workspace=1024

# 4. Backup existing production engine
sudo cp /opt/reachy/models/emotion_efficientnet.engine \
        /opt/reachy/models/emotion_efficientnet.engine.bak

# 5. Deploy to shadow path and update DeepStream shadow config
sudo cp /opt/reachy/models/staging/emotion_efficientnet.engine \
        /opt/reachy/models/shadow/emotion_efficientnet.engine
# Edit /opt/reachy/deepstream/emotion_inference_shadow.txt:
#   model-engine-file=/opt/reachy/models/shadow/emotion_efficientnet.engine

# 6. Start shadow pipeline and monitor (30 min)
sudo systemctl restart deepstream-shadow
curl http://localhost:9100/metrics | grep -E "inference_latency|gpu_memory"
```

**If FAIL**: Optimize via INT8 quantization, reduce input resolution, or rollback.

### Gate C — Limited User Rollout
**Environment**: Jetson (canary, 10% of sessions)

**Criteria**:
- User-visible latency ≤ 300 ms end-to-end
- Abstention rate ≤ 20%
- User complaints < 1% of sessions

**Procedure**:
```bash
# Enable canary routing (10% traffic)
# Monitor for 7 days: latency, abstention, user feedback
# If stable, proceed to full rollout
```

**If FAIL**: Rollback canary, investigate feedback, adjust confidence threshold.

## Full Rollout

### 1. Promote Engine
```bash
ssh jetson
sudo cp /opt/reachy/models/shadow/emotion_efficientnet.engine \
        /opt/reachy/models/emotion_efficientnet.engine
```

### 2. Update DeepStream Config
```bash
# Edit /opt/reachy/deepstream/emotion_inference.txt:
#   model-engine-file=/opt/reachy/models/emotion_efficientnet.engine
#   num-detected-classes=3
#   labelfile-path=/opt/reachy/models/labels_3cls.txt
sudo systemctl restart deepstream-primary
```

### 3. Verify
```bash
# Check pipeline running
sudo systemctl status deepstream-primary
curl http://localhost:9100/metrics | grep -E "inference_latency_p95|gpu_memory|macro_f1"
```

### 4. Record Deployment
```bash
# Log to MLflow
python -c "
import mlflow
mlflow.set_tracking_uri('file:///media/rusty_admin/project_data/reachy_emotion/mlruns')
with mlflow.start_run(run_id='<MLFLOW_RUN_ID>'):
    mlflow.set_tag('deployed', 'true')
    mlflow.set_tag('deployment_date', '2026-04-14')
    mlflow.set_tag('gate_a_deploy', 'PASS')
    mlflow.set_tag('gate_b', 'PASS')
    mlflow.set_tag('gate_c', 'PASS')
"
```

### 5. Document Deployment
```markdown
## Release: efficientnet-b0-hsemotion Variant 1 run_0107

**Date**: 2026-04-14
**Operator**: Russell Bray
**Model**: EfficientNet-B0 (HSEmotion, frozen backbone, 3-class head)
**Checkpoint**: variant_1/var1_run_0107/best_model.pth
**Engine**: /opt/reachy/models/emotion_efficientnet.engine (FP16)

**Gate A-deploy (AffectNet test_dataset_01, 894 images)**:
- Macro F1: 0.781 (target ≥ 0.75) ✅
- Balanced Accuracy: 0.780 (target ≥ 0.75) ✅
- ECE: 0.102 (target ≤ 0.12) ✅

**Gate B (Shadow Mode)**:
- Latency p50: TBD ms (target ≤ 120 ms)
- GPU Memory: TBD GB (target ≤ 2.5 GB)

**Status**: PENDING GATE B/C
```

## Rollback

### Emergency Rollback
```bash
ssh jetson

# Restore backup engine
sudo cp /opt/reachy/models/emotion_efficientnet.engine.bak \
        /opt/reachy/models/emotion_efficientnet.engine
sudo systemctl restart deepstream-primary

# Verify
curl http://localhost:9100/metrics | grep inference_latency_p95_ms
```

## Error Handling

### Error: Gate A FAIL (Low F1)
1. Inspect confusion matrix (`stats/results/runs/analysis_run_0107.md`).
2. Check per-class error patterns (V1: happy→neutral; V2: neutral→sad).
3. Increase training data diversity (more AffectNet images, domain adaptation).
4. Run hyperparameter sweep (`trainer/sweep_variant2.py`).

### Error: Gate B FAIL (High Latency)
1. Profile engine: `trtexec --loadEngine=... --warmUp=500 --avgRuns=100`
2. Try INT8 quantization with calibration set.
3. Lower input resolution (224×224 → 160×160).

### Error: Gate C FAIL (User Complaints)
1. Review user feedback for common misclassification patterns.
2. Increase confidence threshold (raise abstention to reduce false positives).
3. Consider rollback if complaints > 1%.

### Error: DeepStream Pipeline Crash
1. Check logs: `journalctl -u deepstream-primary -n 50`
2. Verify engine: `trtexec --loadEngine=/opt/reachy/models/emotion_efficientnet.engine`
3. Check GPU: `nvidia-smi`
4. Restart; if crash persists, rollback to `.engine.bak`.

## Monitoring
- **Prometheus**: `inference_latency_p50_ms`, `inference_latency_p95_ms`, `gpu_memory_used_mb`, `macro_f1`, `abstention_rate`
- **Alerts**: latency p95 > 250 ms, GPU > 2.5 GB, F1 drop > 5%, abstention > 20%

## Related
- **[requirements.md §7](../requirements.md#7-model-deployment--quality-gates)**: Two-tier Gate A, Gate B/C.
- **[ADR 011](../decisions/011-two-tier-gate-a-v1-deployment.md)**: Two-tier Gate A rationale.
- **[requirements.md §21](../requirements.md#21-model-packaging--serving-on-jetson)**: DeepStream config.
- **[Decision: DeepStream-Only Runtime](../decisions/002-deepstream-only-runtime.md)**: No Triton on Jetson.
- **[Run 0107 Analysis](../../stats/results/runs/analysis_run_0107.md)**: V1 deployment candidate metrics.

---

**Last Updated**: 2026-04-14  
**Owner**: Russell Bray
