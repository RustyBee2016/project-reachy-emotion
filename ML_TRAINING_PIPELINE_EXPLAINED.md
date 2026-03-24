# ML Training Pipeline — Comprehensive Script Explanations

**Project:** Reachy_EQ_PPE_Degree_Mini_01 (v0.09.2)  
**Date:** 2026-03-24  
**Purpose:** Detailed explanation of the 5 core ML training pipeline scripts

---

## Table of Contents

1. [Overview](#overview)
2. [Script 1: train_efficientnet.py](#script-1-train_efficientnetpy)
3. [Script 2: run_efficientnet_pipeline.py](#script-2-run_efficientnet_pipelinepy)
4. [Script 3: prepare_dataset.py](#script-3-prepare_datasetpy)
5. [Script 4: gate_a_validator.py](#script-4-gate_a_validatorpy)
6. [Script 5: mlflow_tracker.py](#script-5-mlflow_trackerpy)
7. [Workflow Integration](#workflow-integration)
8. [Data Flow Diagram](#data-flow-diagram)

---

## Overview

The ML training pipeline consists of 5 interconnected Python scripts that orchestrate the complete workflow from dataset preparation through model training, validation, and deployment. These scripts support **Agent 5 (Training Orchestrator)** and **Agent 6 (Evaluation Agent)** in the n8n agentic system.

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ML Training Pipeline                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. prepare_dataset.py                                          │
│     └─> Extract 10 random frames per video                     │
│     └─> Generate JSONL manifests                               │
│     └─> Calculate dataset hash                                 │
│                                                                  │
│  2. train_efficientnet.py (CLI entry point)                    │
│     └─> Load config YAML                                       │
│     └─> Initialize EfficientNetTrainer                         │
│     └─> Run two-phase training loop                            │
│     └─> Export ONNX if Gate A passes                           │
│                                                                  │
│  3. run_efficientnet_pipeline.py (orchestrator)                │
│     └─> Coordinate train → evaluate → validate → export        │
│     └─> Emit Agent 5/6 contract events to gateway              │
│     └─> Write dashboard payload files                          │
│                                                                  │
│  4. gate_a_validator.py                                        │
│     └─> Compute F1, balanced accuracy, ECE, Brier              │
│     └─> Validate against thresholds                            │
│     └─> Generate gate_a.json report                            │
│                                                                  │
│  5. mlflow_tracker.py                                          │
│     └─> Log hyperparameters, metrics, artifacts                │
│     └─> Track dataset hash for reproducibility                 │
│     └─> Enable experiment comparison                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Separation of Concerns**: Each script has a single, well-defined responsibility
2. **Reproducibility**: Dataset hashing, MLflow tracking, and manifest generation ensure runs are reproducible
3. **Quality Gates**: Gate A validation prevents low-quality models from reaching deployment
4. **Observability**: Contract events, MLflow metrics, and dashboard payloads enable real-time monitoring
5. **Modularity**: Scripts can be invoked independently or orchestrated together

---

## Script 1: train_efficientnet.py

**Location:** `trainer/train_efficientnet.py`  
**Role:** CLI entry point for EfficientNet-B0 emotion classifier training  
**Invoked By:** Streamlit UI (03_Train.py), n8n Agent 5, manual CLI

### Purpose

This script is the primary interface for training EfficientNet-B0 models. It handles:
- Configuration loading from YAML specs
- Model initialization with HSEmotion pretrained weights
- Two-phase training execution (frozen backbone → selective unfreezing)
- Checkpoint management (save/resume)
- Conditional ONNX export when Gate A passes

### Key Components

#### 1. CLI Argument Parsing

```python
--config         # Path to training config YAML (e.g., efficientnet_b0_emotion_3cls.yaml)
--run-id         # Unique identifier for this training run
--resume         # Path to checkpoint for warm-starting
--export-only    # Skip training, only export existing checkpoint to ONNX
--weights-path   # Override default HSEmotion pretrained weight location
```

**Usage Examples:**

```bash
# Train from scratch with 3-class config
python train_efficientnet.py --config fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml

# Resume interrupted training
python train_efficientnet.py --config <config.yaml> --resume checkpoints/epoch_10.pth

# Export existing checkpoint to ONNX
python train_efficientnet.py --export-only --resume checkpoints/best_model.pth
```

#### 2. Run ID Generation

If no `--run-id` is provided, generates a timestamped identifier:

```python
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
run_id = f"efficientnet_b0_emotion_{timestamp}"
```

This run ID ties together:
- MLflow experiment tracking
- Dataset manifests (`run_XXXX_train.jsonl`)
- Dashboard payload files
- n8n workflow correlation IDs

#### 3. Configuration Loading

Loads YAML training specs with CLI overrides:

```python
config = TrainingConfig.from_yaml(str(config_path))

# Apply CLI overrides
if args.data_dir:
    config.data.data_root = args.data_dir
if args.output_dir:
    config.checkpoint_dir = args.output_dir
```

**Config Structure (efficientnet_b0_emotion_3cls.yaml):**

```yaml
model:
  architecture: efficientnet_b0
  num_classes: 3
  input_size: 224
  pretrained_weights: /path/to/enet_b0_8_best_vgaf.pt

data:
  data_root: /media/rusty_admin/project_data/reachy_emotion/videos/train
  class_names: [happy, sad, neutral]
  batch_size: 32
  frames_per_video: 10

training:
  epochs: 20
  learning_rate: 0.001
  optimizer: adamw
  scheduler: cosine_warmup
  freeze_epochs: 5  # Phase 1: backbone frozen
```

#### 4. Two-Phase Training

**Phase 1 (Epochs 1-5):** Backbone frozen, only classification head trains  
**Phase 2 (Epochs 6+):** Selectively unfreeze `blocks.5`, `blocks.6`, `conv_head`

```python
trainer = EfficientNetTrainer(config, weights_path=args.weights_path)
results = trainer.train(run_id=args.run_id, resume_epoch=resume_epoch)
```

The trainer automatically:
- Loads HSEmotion pretrained weights (VGGFace2 + AffectNet)
- Applies mixup augmentation
- Uses mixed precision (FP16) training
- Saves checkpoints (`best_model.pth`, `latest.pth`)
- Logs metrics to MLflow

#### 5. Conditional ONNX Export

If training completes and Gate A passes (`status == 'completed_gate_passed'`):

```python
export_results = export_efficientnet_for_deployment(
    checkpoint_path=str(checkpoint_path),
    output_dir=export_path,
    model_name=f"emotion_efficientnet_{args.run_id}",
    precision="fp16",
    input_size=config.model.input_size,
    num_classes=config.model.num_classes,
)
```

The ONNX file is later converted to TensorRT by **Agent 7 (Deployment Agent)** on the Jetson.

#### 6. Exit Code Convention

```python
if results['status'] in ['completed', 'completed_gate_passed']:
    sys.exit(0)  # Success
elif results['status'] == 'completed_gate_failed':
    sys.exit(0)  # Training succeeded, but gates failed (not an error)
else:
    sys.exit(1)  # Actual training error
```

This convention allows n8n workflows and `training_control.py` to distinguish between:
- Successful training (exit 0)
- Failed gates (exit 0, but different status)
- Training errors (exit 1)

### Integration Points

- **Called By:** Streamlit UI (`03_Train.py`), n8n Agent 5, manual CLI
- **Calls:** `EfficientNetTrainer`, `export_efficientnet_for_deployment`, MLflow
- **Outputs:** Checkpoints, ONNX files, MLflow run records

---

## Script 2: run_efficientnet_pipeline.py

**Location:** `trainer/run_efficientnet_pipeline.py`  
**Role:** End-to-end pipeline orchestrator (train → evaluate → validate → export)  
**Invoked By:** n8n Agent 5/6, CI/CD pipelines, manual testing

### Purpose

This script coordinates the complete ML workflow, handling both training mode (default) and evaluation-only mode (`--skip-train`). It emits structured contract events to the FastAPI gateway for n8n tracking.

### Key Components

#### 1. Gateway Contract Client

Posts structured event payloads to the FastAPI gateway at `/api/training/status/<run_id>`:

```python
class GatewayContractClient:
    def post_training_status(self, run_id: str, payload: Dict[str, Any]) -> None:
        url = f"{self.base_url}/api/training/status/{run_id}"
        response = self.session.post(url, json=payload, timeout=self.timeout_seconds)
        response.raise_for_status()
```

**Event Types Emitted:**
- `training.started`
- `training.completed`
- `training.failed`
- `evaluation.started`
- `evaluation.completed`

These events are persisted to Postgres and forwarded to n8n workflows (Agent 5 & 6) for orchestration tracking.

#### 2. CLI Arguments

```python
--config              # Training config YAML
--run-id              # Unique identifier for this pipeline run
--skip-train          # Evaluate existing checkpoint without training
--checkpoint          # Path to checkpoint (required with --skip-train)
--variant             # Model variant slug (variant_1, variant_2, etc.)
--run-type            # training | validation | test
--gateway-base        # FastAPI gateway URL for contract events
--no-contract-updates # Disable gateway event emission
```

**Usage Examples:**

```bash
# Full train → evaluate → validate → export pipeline
python run_efficientnet_pipeline.py \
  --config trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml \
  --run-id run_0042 \
  --variant variant_1 \
  --run-type training

# Evaluation-only mode (test existing checkpoint)
python run_efficientnet_pipeline.py \
  --skip-train \
  --checkpoint checkpoints/best_model.pth \
  --run-id run_0042_test \
  --variant variant_1 \
  --run-type test
```

#### 3. Training Phase

If `--skip-train` is NOT set:

```python
trainer = EfficientNetTrainer(config)
train_result = trainer.train(run_id=args.run_id, resume_epoch=0)

if train_result["status"] not in {"completed", "completed_gate_passed", "completed_gate_failed"}:
    _emit_training_failed(contract_client, run_id=args.run_id, error_message=f"Training failed: {train_result}")
    raise SystemExit(f"Training failed: {train_result}")
```

Emits `training.started` and `training.completed` events to the gateway.

#### 4. Evaluation Phase

Collects predictions from the validation dataset:

```python
preds = _collect_predictions(
    checkpoint_path=checkpoint_path,
    data_root=config.data.data_root,
    class_names=config.data.class_names,
    input_size=config.model.input_size,
    batch_size=config.data.batch_size,
    num_workers=0,
    run_id=args.run_id,
    frames_per_video=max(1, int(config.data.frames_per_video)),
)
```

Returns:
```python
{
    "y_true": np.array([0, 1, 2, ...]),  # Ground truth labels
    "y_pred": np.array([0, 1, 2, ...]),  # Predicted labels
    "y_prob": np.array([[0.8, 0.1, 0.1], ...])  # Softmax probabilities
}
```

#### 5. Gate A Validation

```python
gate_report = evaluate_predictions(
    preds["y_true"],
    preds["y_pred"],
    preds["y_prob"],
    config.data.class_names,
    GateAThresholds(),
)
```

Returns a structured report with:
- All computed metrics (F1, balanced accuracy, ECE, Brier)
- Per-class F1 scores
- Pass/fail status for each gate
- Overall pass/fail determination

#### 6. Conditional ONNX Export

If `gate_report["overall_pass"]` is True:

```python
export_result = export_efficientnet_for_deployment(
    checkpoint_path=str(checkpoint_path),
    output_dir=str(export_dir),
    num_classes=len(config.data.class_names),
    input_size=config.model.input_size,
)
onnx_path = export_result.get("onnx_path")
```

#### 7. Dashboard Payload Generation

Writes a JSON payload consumed by Streamlit dashboard (`06_Dashboard.py`):

```python
dashboard_payload = {
    "run_id": run_id,
    "model_variant": variant,
    "run_type": run_type,
    "gate_a_metrics": gate_report.get("metrics", {}),
    "gate_a_gates": gate_report.get("gates", {}),
    "overall_pass": bool(gate_report.get("overall_pass")),
    "artifacts": {
        "predictions_npz": str(predictions_path),
        "gate_a_report_json": str(gate_path),
        "onnx_path": onnx_path,
    },
}
```

Saved to: `stats/results/dashboard_runs/<variant>/<run_type>/<run_id>.json`

#### 8. Artifact Directory Organization

Outputs are organized by variant/run_type/run_id hierarchy:

```
stats/results/
  variant_1/
    training/
      run_0042/
        predictions.npz
        gate_a.json
        export/
          emotion_efficientnet_run_0042.onnx
    validation/
      run_0043/
        ...
  variant_2/
    training/
      run_0044/
        ...
```

This enables A/B testing and clean separation of training vs validation runs.

### Integration Points

- **Called By:** n8n Agent 5/6, CI/CD pipelines, manual testing
- **Calls:** `EfficientNetTrainer`, `gate_a_validator`, `export_efficientnet_for_deployment`, Gateway API
- **Outputs:** Predictions (.npz), Gate A reports (JSON), ONNX files, dashboard payloads

---

## Script 3: prepare_dataset.py

**Location:** `trainer/prepare_dataset.py`  
**Role:** Frame extraction and dataset preparation for training runs  
**Invoked By:** n8n Agent 3, Streamlit UI (03_Train.py), `run_efficientnet_pipeline.py`

### Purpose

The `DatasetPreparer` class orchestrates the frame extraction workflow, converting source videos into frame-based datasets for training. It handles:
- Random frame sampling (10 frames per video by default)
- Optional face detection and cropping (OpenCV DNN SSD)
- JSONL manifest generation with frame metadata
- Train/valid dataset splitting (90/10 default)
- Dataset hash calculation for reproducibility

### Directory Structure

```
/videos/train/
  happy/*.mp4          <- Source videos (promoted from temp by Agent 2)
  sad/*.mp4
  neutral/*.mp4
  run/
    run_0001/          <- Extracted frames (flat directory)
      happy_video1_f00_idx00042.jpg
      happy_video1_f01_idx00123.jpg
      ...
      train_ds_run_0001/  <- Training frames (after split)
      valid_ds_run_0001/  <- Validation frames (after split)
    run_0002/
    ...

/videos/manifests/
  run_0001_train.jsonl              <- Frame metadata (pre-split)
  run_0001_train_ds.jsonl           <- Training frames (post-split)
  run_0001_valid_ds_labeled.jsonl   <- Validation frames (with labels)
  run_0001_valid_ds_unlabeled.jsonl <- Validation frames (no labels)
```

### Key Components

#### 1. Class Constants

```python
EMOTIONS = ("happy", "sad", "neutral")  # 3-class taxonomy
FRAMES_PER_VIDEO = 10                   # Random frames extracted per video
RUN_ID_PATTERN = re.compile(r"^run_\d{4}$")  # Enforces run_XXXX naming
FACE_DETECTOR_NAME = "opencv_dnn_res10_ssd"  # Face detector identifier
```

#### 2. Face Detection (Optional)

When `face_crop=True`, uses OpenCV DNN SSD face detector:

```python
def _detect_face_bbox(self, frame: np.ndarray, *, face_confidence: float, margin_ratio: float = 0.2):
    net = self._get_face_net()
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
    net.setInput(blob)
    detections = net.forward()
    
    # Find highest-confidence face
    best = None
    for idx in range(detections.shape[2]):
        confidence = float(detections[0, 0, idx, 2])
        if confidence >= face_confidence and (best is None or confidence > best["confidence"]):
            best = extract_bbox(detections, idx)
    
    # Expand bbox by margin_ratio (default 20%)
    return expand_bbox(best, margin_ratio)
```

Model files required:
- `trainer/models/face_detector/deploy.prototxt`
- `trainer/models/face_detector/res10_300x300_ssd_iter_140000.caffemodel`

#### 3. Frame Extraction Workflow

```python
def prepare_training_dataset(self, run_id=None, seed=None, face_crop=False, target_size=224, face_confidence=0.6):
    # 1. Validate or auto-generate run_id
    normalized_run_id = self.resolve_run_id(run_id)
    
    # 2. Collect source videos from train/<emotion>/*.mp4
    source_videos = self._collect_source_videos()
    self._validate_source_videos(source_videos)  # Ensure all classes have videos
    
    # 3. Extract N random frames per video
    consolidated_frames = self._extract_run_frames(
        run_id=normalized_run_id,
        rng=random.Random(seed),
        source_videos=source_videos,
        face_crop=face_crop,
        target_size=target_size,
        face_confidence=face_confidence,
    )
    
    # 4. Generate JSONL manifests
    self._generate_manifests(normalized_run_id, consolidated_frames, test_entries=[])
    
    # 5. Calculate dataset hash
    dataset_hash = self.calculate_dataset_hash(run_id=normalized_run_id)
    
    return {
        'run_id': normalized_run_id,
        'train_count': len(consolidated_frames),
        'videos_processed': sum(len(videos) for videos in source_videos.values()),
        'frames_per_video': self.FRAMES_PER_VIDEO,
        'dataset_hash': dataset_hash,
        'face_crop': bool(face_crop),
    }
```

#### 4. Random Frame Sampling

```python
def _extract_random_frames_from_video(self, *, video_path, num_frames, output_dir, label, rng, face_crop, target_size, face_confidence):
    cap = cv2.VideoCapture(str(video_path))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Sample N random frame indices
    if total_frames >= num_frames:
        selected = sorted(rng.sample(range(total_frames), num_frames))
    else:
        selected = sorted(rng.randrange(total_frames) for _ in range(num_frames))
    
    entries = []
    for order_idx, frame_idx in enumerate(selected):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        success, frame = cap.read()
        if not success:
            continue
        
        # Optional face detection/cropping
        if face_crop:
            face_bbox = self._detect_face_bbox(frame, face_confidence=face_confidence)
            if face_bbox is None:
                continue  # Skip frames without detected faces
            crop = frame[face_bbox["y1"]:face_bbox["y2"], face_bbox["x1"]:face_bbox["x2"]]
            frame = cv2.resize(crop, (target_size, target_size))
        
        # Save frame with structured naming
        frame_name = f"{label}_{video_path.stem}_f{order_idx:02d}_idx{frame_idx:05d}.jpg"
        frame_path = output_dir / frame_name
        cv2.imwrite(str(frame_path), frame)
        
        entries.append({
            "video_id": video_path.stem,
            "path": str(frame_path),
            "label": label,
            "source_video": str(video_path),
            "face_bbox": face_bbox if face_crop else None,
        })
    
    cap.release()
    return entries
```

#### 5. Train/Valid Dataset Splitting

After frame extraction, `split_run_dataset()` moves frames into separate directories:

```python
def split_run_dataset(self, run_id, *, train_ratio=0.9, seed=None, strip_valid_labels=True):
    run_root = self.train_runs_path / run_id
    train_ds_dir = run_root / f"train_ds_{run_id}"
    valid_ds_dir = run_root / f"valid_ds_{run_id}"
    
    # Load flat frames from run_root
    flat_frames = sorted([p for p in run_root.glob("*.jpg") if p.is_file()])
    
    # Bucket frames by emotion class
    label_map = self._load_run_train_labels(run_id)
    buckets = {label: [] for label in self.EMOTIONS}
    for frame_path in flat_frames:
        label = label_map.get(str(frame_path.relative_to(self.base_path)))
        buckets[label].append(frame_path)
    
    # Stratified split (90/10 default)
    train_frames = []
    valid_frames = []
    for label, bucket in buckets.items():
        rng.shuffle(bucket)
        split_idx = max(1, min(len(bucket) - 1, int(len(bucket) * train_ratio)))
        train_frames.extend((path, label) for path in bucket[:split_idx])
        valid_frames.extend((path, label) for path in bucket[split_idx:])
    
    # Move files and generate manifests
    for src_path, label in train_frames:
        dst_path = train_ds_dir / src_path.name
        shutil.move(str(src_path), str(dst_path))
    
    for src_path, label in valid_frames:
        # Strip label prefix from validation filenames (optional)
        target_name = self._strip_label_prefix(src_path.name) if strip_valid_labels else src_path.name
        dst_path = valid_ds_dir / target_name
        shutil.move(str(src_path), str(dst_path))
    
    # Generate 3 manifests:
    #   1. train_ds.jsonl (labeled training frames)
    #   2. valid_ds_labeled.jsonl (validation frames WITH labels)
    #   3. valid_ds_unlabeled.jsonl (validation frames WITHOUT labels)
```

The unlabeled manifest prevents label leakage during training.

#### 6. Dataset Hash Calculation

```python
def calculate_dataset_hash(self, run_id=None):
    hasher = hashlib.sha256()
    
    if run_id:
        dataset_root = self.train_runs_path / run_id
    else:
        dataset_root = self.train_path
    
    all_files = sorted(dataset_root.rglob('*.jpg'))
    
    for file_path in all_files:
        rel_path = file_path.relative_to(dataset_root)
        hasher.update(str(rel_path).encode())
        hasher.update(str(file_path.stat().st_size).encode())
    
    return hasher.hexdigest()
```

**Important:** This is a path+size hash, NOT a content hash. Two files with identical paths and sizes but different pixel data will produce the same hash. This is a deliberate speed/accuracy tradeoff for large image datasets.

### Integration Points

- **Called By:** n8n Agent 3, Streamlit UI (`03_Train.py`), `run_efficientnet_pipeline.py`
- **Calls:** OpenCV DNN (face detection), filesystem operations
- **Outputs:** Frame images (.jpg), JSONL manifests, dataset hash

---

## Script 4: gate_a_validator.py

**Location:** `trainer/gate_a_validator.py`  
**Role:** Quality gate validation for model deployment readiness  
**Invoked By:** `run_efficientnet_pipeline.py`, n8n Agent 6, Streamlit UI (06_Dashboard.py)

### Purpose

Implements Gate A validation logic that determines whether a trained model meets minimum performance thresholds for deployment to the Jetson. Prevents low-quality models from reaching production.

### Gate A Thresholds (Default)

```python
@dataclass
class GateAThresholds:
    macro_f1: float = 0.84              # Macro-averaged F1 score
    balanced_accuracy: float = 0.85     # Balanced accuracy (accounts for class imbalance)
    per_class_f1: float = 0.75          # Minimum F1 for each individual class
    per_class_floor: float = 0.70       # Absolute minimum F1 across all classes
    ece: float = 0.08                   # Expected Calibration Error (confidence reliability)
    brier: float = 0.16                 # Brier score (probabilistic accuracy)
```

These thresholds are aligned with `requirements.md` §8.1 and ensure models are sufficiently accurate and well-calibrated.

### Key Components

#### 1. Core Evaluation Function

```python
def evaluate_predictions(y_true, y_pred, y_prob, class_names, thresholds):
    # Compute classification metrics (F1, balanced accuracy, etc.)
    metrics = compute_metrics(y_true.tolist(), y_pred.tolist(), class_names=class_names)
    
    # Compute calibration metrics (ECE, Brier)
    if y_prob is not None:
        metrics.update(compute_calibration_metrics(y_true.tolist(), y_prob))
    
    # Extract per-class F1 scores
    per_class = _per_class_f1(metrics, class_names)
    per_class_passes = {k: (v >= thresholds.per_class_f1) for k, v in per_class.items()}
    per_class_min = min(per_class.values()) if per_class else 0.0
    
    # Evaluate each gate
    gates = {
        "macro_f1": float(metrics.get("f1_macro", 0.0)) >= thresholds.macro_f1,
        "balanced_accuracy": float(metrics.get("balanced_accuracy", 0.0)) >= thresholds.balanced_accuracy,
        "per_class_f1": all(per_class_passes.values()) and per_class_min >= thresholds.per_class_floor,
        "ece": float(metrics.get("ece", 1.0)) <= thresholds.ece,
        "brier": float(metrics.get("brier", 1.0)) <= thresholds.brier,
    }
    
    # Overall pass requires ALL gates to pass
    overall_pass = all(gates.values())
    
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "class_names": class_names,
        "thresholds": asdict(thresholds),
        "metrics": metrics,
        "per_class_f1": per_class,
        "gates": gates,
        "overall_pass": overall_pass,
    }
```

#### 2. Prediction Loading

Loads saved predictions from `.npz` files (output of `_collect_predictions` in `run_efficientnet_pipeline.py`):

```python
def _load_predictions(path):
    payload = np.load(path, allow_pickle=True)
    y_true = payload["y_true"]
    y_pred = payload["y_pred"]
    y_prob = payload["y_prob"] if "y_prob" in payload.files else None
    class_names = [str(x) for x in payload["class_names"].tolist()] if "class_names" in payload.files else ["happy", "sad", "neutral"]
    return y_true, y_pred, y_prob, class_names
```

#### 3. CLI Entry Point

Standalone script for validating Gate A metrics:

```bash
python gate_a_validator.py \
  --predictions stats/results/variant_1/training/run_0042/predictions.npz \
  --output stats/results/gate_a_validation.json \
  --macro-f1-threshold 0.84 \
  --ece-threshold 0.08
```

Outputs:
- JSON report written to `--output` path
- Exit code 0 (validation complete, regardless of pass/fail)

#### 4. Gate A Report Structure

```json
{
  "timestamp_utc": "2026-03-24T18:42:13.123456+00:00",
  "class_names": ["happy", "sad", "neutral"],
  "thresholds": {
    "macro_f1": 0.84,
    "balanced_accuracy": 0.85,
    "per_class_f1": 0.75,
    "per_class_floor": 0.70,
    "ece": 0.08,
    "brier": 0.16
  },
  "metrics": {
    "accuracy": 0.89,
    "f1_macro": 0.87,
    "f1_class_0": 0.91,
    "f1_class_1": 0.85,
    "f1_class_2": 0.86,
    "balanced_accuracy": 0.88,
    "ece": 0.06,
    "brier": 0.12
  },
  "per_class_f1": {
    "happy": 0.91,
    "sad": 0.85,
    "neutral": 0.86
  },
  "gates": {
    "macro_f1": true,
    "balanced_accuracy": true,
    "per_class_f1": true,
    "ece": true,
    "brier": true
  },
  "overall_pass": true
}
```

### Integration Points

- **Called By:** `run_efficientnet_pipeline.py`, n8n Agent 6, Streamlit UI (`06_Dashboard.py`)
- **Calls:** `compute_metrics`, `compute_calibration_metrics` (from `fer_finetune/evaluate.py`)
- **Outputs:** Gate A JSON reports

---

## Script 5: mlflow_tracker.py

**Location:** `trainer/mlflow_tracker.py`  
**Role:** Experiment tracking and reproducibility management  
**Invoked By:** `EfficientNetTrainer`, `run_efficientnet_pipeline.py`

### Purpose

Provides a wrapper class (`MLflowTracker`) for logging training experiments, metrics, hyperparameters, and model artifacts to MLflow. Enables reproducibility tracking, experiment comparison, and model versioning.

### Key Features

1. **Automatic experiment creation and run management**
2. **Epoch-level metric logging** (loss, accuracy, F1, etc.)
3. **Hyperparameter and config logging**
4. **Dataset hash tracking** for reproducibility
5. **Model artifact logging** (checkpoints, ONNX exports)
6. **Gate A validation result tracking**

### MLflow Tracking URI

- **Default:** `file:///media/rusty_admin/project_data/reachy_emotion/mlruns`
- **Override:** Set `MLFLOW_TRACKING_URI` environment variable

### Key Components

#### 1. Initialization

```python
class MLflowTracker:
    def __init__(self, experiment_name='emotion_classification'):
        self.experiment_name = experiment_name
        self.run = None
        
        # Set tracking URI
        tracking_uri = os.getenv('MLFLOW_TRACKING_URI', 'file:///media/rusty_admin/project_data/reachy_emotion/mlruns')
        mlflow.set_tracking_uri(tracking_uri)
        
        # Create or set experiment
        mlflow.set_experiment(experiment_name)
```

All runs are grouped under a single experiment (`emotion_classification`).

#### 2. Training Run Lifecycle

```python
# Start run
tracker.start_training(
    run_id='run_0042',
    config={'learning_rate': 0.001, 'batch_size': 32, ...},
    tags={'variant': 'variant_1', 'run_type': 'training'}
)

# Log epoch metrics
tracker.log_epoch_metrics(
    epoch=10,
    metrics={'train_loss': 0.23, 'val_f1': 0.87, 'learning_rate': 0.0005}
)

# Log dataset info
tracker.log_dataset_info(
    dataset_hash='a3f2b1c4...',
    train_count=1200,
    test_count=300,
    additional_info={'frames_per_video': 10}
)

# Log model artifacts
tracker.log_model(
    model_path='checkpoints/best_model.pth',
    model_name='best_checkpoint'
)

# Log Gate A results
tracker.log_validation_results(
    gate_name='gate_a',
    passed=True,
    metrics={'f1_macro': 0.87, 'ece': 0.06}
)

# End run
tracker.end_training(status='FINISHED')
```

#### 3. Dataset Hash Tracking

Critical for detecting dataset drift between runs:

```python
tracker.log_dataset_info(
    dataset_hash=dataset_preparer.calculate_dataset_hash(run_id='run_0042'),
    train_count=1200,
    test_count=300
)
```

If two runs have different hashes, their datasets differ (new videos, re-extraction, etc.).

#### 4. Metric Visualization

MLflow UI enables:
- Comparing metrics across runs
- Filtering by tags (variant, run_type)
- Visualizing learning curves
- Tracking hyperparameter impact

Access via: `mlflow ui --backend-store-uri file:///media/rusty_admin/project_data/reachy_emotion/mlruns`

### Integration Points

- **Called By:** `EfficientNetTrainer`, `run_efficientnet_pipeline.py`
- **Calls:** MLflow Python API
- **Outputs:** MLflow run records, artifacts, metrics

---

## Workflow Integration

### n8n Agent 5 (Training Orchestrator)

```json
{
  "workflow": "05_training_orchestrator_efficientnet.json",
  "trigger": "Manual or scheduled",
  "steps": [
    "1. Check dataset balance (min 20 samples per class)",
    "2. Generate run_id (run_XXXX)",
    "3. Call prepare_dataset.py (frame extraction)",
    "4. Call train_efficientnet.py (training)",
    "5. Emit training.completed event to gateway",
    "6. Trigger Agent 6 if training succeeded"
  ]
}
```

### n8n Agent 6 (Evaluation Agent)

```json
{
  "workflow": "06_evaluation_agent_efficientnet.json",
  "trigger": "training.completed event from Agent 5",
  "steps": [
    "1. Call run_efficientnet_pipeline.py --skip-train",
    "2. Load checkpoint and collect predictions",
    "3. Call gate_a_validator.py",
    "4. Emit evaluation.completed event to gateway",
    "5. If gates passed, trigger Agent 7 (Deployment)"
  ]
}
```

### Streamlit UI Integration

**03_Train.py** (Training Page):
```python
# Prepare dataset
preparer = DatasetPreparer(base_path='/media/rusty_admin/project_data/reachy_emotion/videos')
result = preparer.prepare_training_dataset(run_id='run_0042', face_crop=True)

# Launch training
subprocess.run([
    'python', 'trainer/train_efficientnet.py',
    '--config', 'fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml',
    '--run-id', 'run_0042'
])
```

**06_Dashboard.py** (Results Dashboard):
```python
# Load dashboard payload
payload_path = 'stats/results/dashboard_runs/variant_1/training/run_0042.json'
with open(payload_path) as f:
    data = json.load(f)

# Display Gate A metrics
st.metric("Macro F1", data['gate_a_metrics']['f1_macro'])
st.metric("ECE", data['gate_a_metrics']['ece'])
st.metric("Overall Pass", "✅ PASS" if data['overall_pass'] else "❌ FAIL")
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Data Flow Overview                           │
└─────────────────────────────────────────────────────────────────┘

1. Video Promotion (Agent 2 → Agent 3)
   /videos/temp/*.mp4  →  /videos/train/<emotion>/*.mp4

2. Frame Extraction (prepare_dataset.py)
   /videos/train/<emotion>/*.mp4  →  /videos/train/run/<run_id>/*.jpg
   
3. Manifest Generation
   Frames  →  /videos/manifests/run_XXXX_train.jsonl

4. Dataset Splitting
   run_XXXX/*.jpg  →  train_ds_run_XXXX/*.jpg + valid_ds_run_XXXX/*.jpg

5. Training (train_efficientnet.py)
   train_ds + valid_ds  →  checkpoints/best_model.pth + MLflow metrics

6. Evaluation (run_efficientnet_pipeline.py)
   best_model.pth + valid_ds  →  predictions.npz

7. Gate A Validation (gate_a_validator.py)
   predictions.npz  →  gate_a.json

8. ONNX Export (if gates pass)
   best_model.pth  →  emotion_efficientnet_run_XXXX.onnx

9. Dashboard Payload
   gate_a.json + predictions.npz  →  dashboard_runs/<variant>/<run_type>/<run_id>.json

10. TensorRT Conversion (Agent 7, on Jetson)
    emotion_efficientnet.onnx  →  emotion_efficientnet.engine
```

---

## Summary

The ML training pipeline is a robust, modular system that orchestrates the complete workflow from dataset preparation through model deployment. Each of the 5 core scripts has a well-defined responsibility and integrates seamlessly with the n8n agentic system, Streamlit web UI, and MLflow experiment tracking.

**Key Takeaways:**

1. **train_efficientnet.py**: CLI entry point for model training with HSEmotion pretrained weights
2. **run_efficientnet_pipeline.py**: End-to-end orchestrator with gateway contract events
3. **prepare_dataset.py**: Frame extraction and dataset preparation with optional face detection
4. **gate_a_validator.py**: Quality gate validation ensuring deployment readiness
5. **mlflow_tracker.py**: Experiment tracking and reproducibility management

All scripts include comprehensive block-by-block comments explaining their role in the project context.
