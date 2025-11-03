---
title: DeepStream-Only Runtime (No Triton on Jetson)
kind: decision
owners: [Russell Bray]
related: [requirements.md#6.2, requirements.md#21]
created: 2025-09-20
updated: 2025-10-04
status: active
---

# DeepStream-Only Runtime (No Triton on Jetson)

## Context
Jetson Xavier NX must perform real-time emotion classification on 30 FPS video streams with strict latency requirements (p50 ≤120 ms, p95 ≤250 ms). We evaluated two inference runtimes:
1. **NVIDIA DeepStream SDK** with `gst-nvinfer` (GStreamer-based)
2. **NVIDIA Triton Inference Server** (standalone or embedded in DeepStream)

Key constraints:
- Jetson Xavier NX 16GB RAM, limited thermal budget
- ActionRecognitionNet (ResNet18 3D RGB, 16-32 frames)
- TensorRT FP16 engine (optional INT8 with calibration)
- Must sustain ≥25 FPS throughput, ≤100 ms latency
- Minimal container footprint for OTA updates

## Decision
**Use DeepStream SDK with `gst-nvinfer` only; skip Triton on Jetson for v0.8.3.**

### Architecture
- **DeepStream pipeline**: `uridecodebin` → `nvvideoconvert` → `nvinfer` (ActionRecognitionNet `.engine`) → `nvdsosd` → `fakesink`
- **TensorRT engine**: Loaded directly by `gst-nvinfer` via config file (`config_infer_primary.txt`)
- **Output**: JSON emotion events emitted via `nvmsgconv` + `nvmsgbroker` or custom probe
- **No Triton**: Avoid additional HTTP/gRPC server overhead and memory footprint

### Rationale
- **Simplicity**: DeepStream is purpose-built for video analytics; single pipeline config.
- **Performance**: `gst-nvinfer` has lower overhead than Triton HTTP/gRPC for single-model use case.
- **Memory**: Triton adds ~500 MB baseline memory; DeepStream-only keeps footprint minimal.
- **Latency**: Direct TensorRT invocation avoids serialization/deserialization overhead.
- **Ops**: Simpler container (no Triton dependencies); faster OTA updates.

## Consequences
### Positive
- **Lower latency**: Direct TensorRT invocation meets p50 ≤120 ms, p95 ≤250 ms targets.
- **Smaller footprint**: Container ~1.5 GB vs. ~2.5 GB with Triton.
- **Simpler config**: Single DeepStream config file vs. Triton model repository + DeepStream config.
- **Faster updates**: Smaller OTA payloads; quicker rollback.

### Negative
- **Single model**: Cannot easily serve multiple models concurrently (acceptable for current scope).
- **No dynamic batching**: Triton's dynamic batching unavailable (not needed for real-time stream).
- **No model versioning**: Must manage engine versions manually (mitigated by MLflow + ZFS snapshots).

### Follow-Up Actions
- Document DeepStream config template in runbook.
- Add engine swap procedure (stop pipeline → copy `.engine` → update config → restart).
- Monitor GPU memory, thermals, and latency in production; adjust precision if needed.

## Alternatives Considered
### 1. Triton Inference Server (Standalone)
- **Pros**: Multi-model serving, dynamic batching, model versioning, HTTP/gRPC API.
- **Cons**: Higher memory footprint (~500 MB baseline), added latency (serialization), more complex config, larger container.
- **Verdict**: Over-engineered for single-model real-time stream; revisit if multi-model or batch inference needed.

### 2. Triton Embedded in DeepStream
- **Pros**: Unified pipeline with Triton's model management.
- **Cons**: Still adds memory/latency overhead; config complexity; not needed for single model.
- **Verdict**: Defer until multi-model use case emerges.

## Related
- **[requirements.md §6.2](../requirements.md#62-software-dependencies)**: DeepStream SDK 6.x + TensorRT 8.6+.
- **[requirements.md §7.2](../requirements.md#72-performance-requirements)**: Latency p50 ≤120 ms, p95 ≤250 ms; throughput ≥20 decisions/sec.
- **[requirements.md §21](../requirements.md#21-model-packaging--serving-on-jetson)**: DeepStream `gst-nvinfer` loads TensorRT `.engine`; no Triton for v0.8.3.

## Notes
- If multi-model serving is required (e.g., face detection + emotion classification), revisit Triton.
- If batch inference is needed (e.g., offline video processing), consider Triton on Ubuntu 1 (not Jetson).
- Monitor thermal throttling; if GPU temp >80°C sustained, reduce frame window or adjust precision.

---

**Last Updated**: 2025-10-04  
**Owner**: Russell Bray
