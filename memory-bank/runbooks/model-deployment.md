---
title: Model Deployment (Gate A/B/C Validation + Engine Export)
kind: runbook
owners: [Russell Bray]
related: [requirements.md#7, requirements.md#21]
created: 2025-10-04
updated: 2025-10-04
status: active
---

# Runbook: Model Deployment

## Purpose
Step-by-step guide for deploying a fine-tuned ActionRecognitionNet model to Jetson with Gate A/B/C validation, TensorRT engine export, and DeepStream config update.

## Prerequisites
- Trained model checkpoint (`.tlt` or `.etlt` from TAO)
- Access to Ubuntu 1 (training host) and Jetson (edge device)
- Valid JWT token with `deploy:write` scope
- MLflow run ID with `dataset_hash` and metrics

## Deployment Gates
Models must pass three gates before production rollout:

### Gate A — Offline Validation (Pre-Robot)
**Environment**: Ubuntu 1 (validation set)

**Criteria**:
- Macro F1 (val): ≥ 0.84
- Per-class F1: ≥ 0.75 (all classes)
- No class F1 < 0.70
- Balanced accuracy: ≥ 0.85
- Calibration: ECE ≤ 0.08, Brier ≤ 0.16

**Procedure**:
```bash
# Run evaluation on validation set
curl -X POST http://ubuntu1:8081/api/evaluate \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "model_path": "/opt/models/actionrecog-0.8.3.tlt",
    "manifest": "/videos/manifests/val_2025-10-04.jsonl",
    "mlflow_run_id": "abc123..."
  }'
```

**Expected Response**:
```json
{
  "status": "pass",
  "metrics": {
    "macro_f1": 0.86,
    "balanced_accuracy": 0.87,
    "per_class_f1": {
      "happy": 0.88,
      "sad": 0.84,
      "angry": 0.82,
      "neutral": 0.89,
      "surprise": 0.85,
      "fearful": 0.78
    },
    "calibration": {
      "ece": 0.06,
      "brier": 0.14
    }
  },
  "gate_a": "PASS"
}
```

**If FAIL**: Do not proceed. Investigate low-performing classes, retrain with more data, or adjust hyperparameters.

### Gate B — Robot Shadow Mode
**Environment**: Jetson (shadow deployment, no user-visible impact)

**Criteria**:
- On-device latency: p50 ≤ 120 ms, p95 ≤ 250 ms
- GPU memory ≤ 2.5 GB
- Macro F1 ≥ 0.80
- Per-class F1: ≥ 0.72 (all classes)
- No class F1 < 0.68

**Procedure**:
```bash
# Export TensorRT engine (FP16)
tao action_recognition export \
  -e /workspace/experiment.yaml \
  -m /workspace/actionrecog-0.8.3.tlt \
  -k $TAO_KEY \
  --engine_file /workspace/actionrecog-0.8.3.engine \
  --batch_size 1 \
  --data_type fp16

# Copy engine to Jetson
scp /workspace/actionrecog-0.8.3.engine jetson:/opt/reachy/models/shadow/

# Update DeepStream config (shadow pipeline)
ssh jetson
sudo nano /opt/reachy/deepstream/config_infer_shadow.txt
# Update: model-engine-file=/opt/reachy/models/shadow/actionrecog-0.8.3.engine

# Start shadow pipeline
docker run -d --name deepstream-shadow \
  --runtime nvidia \
  -v /opt/reachy/models:/models \
  -v /opt/reachy/deepstream:/config \
  nvcr.io/nvidia/deepstream:6.3-devel \
  deepstream-app -c /config/deepstream_shadow.txt

# Monitor metrics (30 min)
curl http://jetson:9100/metrics | grep -E "inference_latency|gpu_memory|f1_score"
```

**Expected Metrics**:
```
inference_latency_p50_ms 95
inference_latency_p95_ms 220
gpu_memory_used_mb 2100
macro_f1 0.82
```

**If FAIL**: Optimize engine (reduce batch size, adjust precision, lower frame window), or rollback.

### Gate C — Limited User Rollout
**Environment**: Jetson (canary deployment, 10% of sessions)

**Criteria**:
- User-visible latency ≤ 300 ms end-to-end
- Abstention rate ≤ 20%
- User complaints < 1% of sessions
- No safety incidents

**Procedure**:
```bash
# Enable canary routing (10% traffic)
curl -X POST http://ubuntu2:8080/api/routing \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "canary_weight": 0.1,
    "canary_engine": "/opt/reachy/models/shadow/actionrecog-0.8.3.engine"
  }'

# Monitor for 7 days
# - User feedback (UI surveys, support tickets)
# - Latency (p50, p95, p99)
# - Abstention rate (confidence < threshold)
# - Safety incidents (false positives causing inappropriate LLM responses)

# Check metrics
curl http://ubuntu2:8080/metrics | grep -E "canary_latency|canary_abstention|canary_complaints"
```

**Expected Metrics**:
```
canary_latency_p50_ms 180
canary_latency_p95_ms 280
canary_abstention_rate 0.15
canary_complaints_rate 0.005
```

**If FAIL**: Rollback canary, investigate user feedback, adjust confidence threshold, or retrain.

## Full Rollout

### 1. Promote Engine
If Gate C passes, promote to production.

```bash
# Copy engine to production path
ssh jetson
sudo cp /opt/reachy/models/shadow/actionrecog-0.8.3.engine \
        /opt/reachy/models/action_recognition.engine

# Update DeepStream config
sudo nano /opt/reachy/deepstream/config_infer_primary.txt
# Update: model-engine-file=/opt/reachy/models/action_recognition.engine
```

### 2. Update MLflow
Mark run as promoted.

```bash
curl -X POST http://ubuntu1:8081/api/mlflow/promote \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "run_id": "abc123...",
    "promoted": true,
    "promoted_at": "2025-10-04T12:34:56Z",
    "gate_a": "PASS",
    "gate_b": "PASS",
    "gate_c": "PASS"
  }'
```

### 3. Restart DeepStream
Restart primary pipeline with new engine.

```bash
ssh jetson

# Stop primary pipeline
docker stop deepstream-primary

# Start with new engine
docker run -d --name deepstream-primary \
  --runtime nvidia \
  --restart unless-stopped \
  -v /opt/reachy/models:/models \
  -v /opt/reachy/deepstream:/config \
  nvcr.io/nvidia/deepstream:6.3-devel \
  deepstream-app -c /config/deepstream_primary.txt

# Verify pipeline running
docker logs deepstream-primary | tail -20
```

### 4. Monitor Production
Watch metrics for 24 hours.

```bash
# Check latency
curl http://jetson:9100/metrics | grep inference_latency_p95_ms

# Check GPU memory
curl http://jetson:9100/metrics | grep gpu_memory_used_mb

# Check F1 score (if ground truth available)
curl http://jetson:9100/metrics | grep macro_f1

# Check abstention rate
curl http://jetson:9100/metrics | grep abstention_rate
```

**Alerts**:
- Latency p95 > 250 ms → investigate
- GPU memory > 2.5 GB → investigate
- Abstention rate > 20% → investigate
- F1 drop > 5% → consider rollback

### 5. Document Deployment
Log deployment in release notes.

```markdown
## Release: actionrecog-0.8.3

**Date**: 2025-10-04  
**Operator**: Russell Bray  
**MLflow Run**: abc123...  
**Dataset Hash**: sha256:d4e5f6...  
**Engine**: /opt/reachy/models/action_recognition.engine (FP16, 1.2 GB)

**Gate A (Offline Validation)**:
- Macro F1: 0.86 (target ≥ 0.84) ✅
- Balanced Accuracy: 0.87 (target ≥ 0.85) ✅
- Calibration ECE: 0.06 (target ≤ 0.08) ✅

**Gate B (Shadow Mode)**:
- Latency p50: 95 ms (target ≤ 120 ms) ✅
- Latency p95: 220 ms (target ≤ 250 ms) ✅
- GPU Memory: 2.1 GB (target ≤ 2.5 GB) ✅
- Macro F1: 0.82 (target ≥ 0.80) ✅

**Gate C (Canary)**:
- User Latency p95: 280 ms (target ≤ 300 ms) ✅
- Abstention Rate: 15% (target ≤ 20%) ✅
- Complaints: 0.5% (target < 1%) ✅

**Status**: ✅ DEPLOYED TO PRODUCTION
```

## Rollback

### Emergency Rollback (Production Issues)
```bash
ssh jetson

# Stop primary pipeline
docker stop deepstream-primary

# Revert to previous engine
sudo cp /opt/reachy/models/action_recognition.engine.bak \
        /opt/reachy/models/action_recognition.engine

# Restart pipeline
docker start deepstream-primary

# Verify rollback
docker logs deepstream-primary | tail -20
curl http://jetson:9100/metrics | grep inference_latency_p95_ms
```

### Rollback MLflow
```bash
curl -X POST http://ubuntu1:8081/api/mlflow/promote \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "run_id": "abc123...",
    "promoted": false,
    "rollback_reason": "Production latency spike"
  }'
```

## Error Handling

### Error: Gate A FAIL (Low F1)
**Resolution**:
1. Inspect confusion matrix: identify low-performing classes.
2. Collect more training data for weak classes.
3. Adjust class weights or augmentation.
4. Retrain and re-evaluate.

### Error: Gate B FAIL (High Latency)
**Resolution**:
1. Profile engine: `tao action_recognition inference --profile`
2. Reduce frame window (32 → 16 frames).
3. Try INT8 quantization with calibration set.
4. Lower input resolution (224x224 → 160x160).

### Error: Gate C FAIL (User Complaints)
**Resolution**:
1. Review user feedback: identify common issues.
2. Adjust confidence threshold (increase to reduce false positives).
3. Retrain with more diverse data.
4. Consider rollback if complaints > 1%.

### Error: DeepStream Pipeline Crash
**Resolution**:
1. Check logs: `docker logs deepstream-primary`
2. Verify engine compatibility: `tao action_recognition validate --engine ...`
3. Check GPU memory: `nvidia-smi`
4. Restart pipeline; if crash persists, rollback.

## Monitoring
- **Prometheus metrics**: `inference_latency_p50_ms`, `inference_latency_p95_ms`, `gpu_memory_used_mb`, `macro_f1`, `abstention_rate`, `complaints_rate`
- **Alerts**:
  - Latency p95 > 250 ms → investigate
  - GPU memory > 2.5 GB → investigate
  - F1 drop > 5% → consider rollback
  - Abstention rate > 20% → investigate
  - Complaints rate > 1% → escalate

## Related
- **[requirements.md §7](../requirements.md#7-model-deployment--quality-gates)**: Deployment gates A/B/C.
- **[requirements.md §21](../requirements.md#21-model-packaging--serving-on-jetson)**: DeepStream `gst-nvinfer` with TensorRT engine.
- **[Decision: DeepStream-Only Runtime](../decisions/002-deepstream-only-runtime.md)**: Rationale for skipping Triton.

---

**Last Updated**: 2025-10-04  
**Owner**: Russell Bray
