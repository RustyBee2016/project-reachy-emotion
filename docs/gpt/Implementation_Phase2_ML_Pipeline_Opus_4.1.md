# Phase 2: ML Pipeline Implementation
**Weeks 3-5 | Machine Learning Pipeline**

## Overview
Setup TAO Toolkit environment, implement EmotionNet fine-tuning, create dataset preparation scripts, integrate MLflow tracking.

## Components to Implement

### 2.1 TAO Environment Setup (`trainer/tao/`)
- Docker Compose for TAO 4.x (training) and 5.3 (export)
- GPU passthrough configuration
- Volume mounts for datasets and models
- Environment initialization script

### 2.2 EmotionNet Configuration (`trainer/tao/specs/`)
- `emotionnet_6cls.yaml` - Full 6-class emotion model
- `emotionnet_2cls.yaml` - Binary happy/sad model
- Augmentation pipeline configuration
- Learning rate schedules
- Early stopping criteria

### 2.3 Dataset Preparation (`trainer/prepare_dataset.py`)
- Balanced sampling from dataset_all
- Stratified train/test split generation
- Run ID tracking in database
- JSONL manifest creation
- Dataset hash calculation for reproducibility

### 2.4 Training Orchestrator (`trainer/train_emotionnet.py`)
- TAO CLI wrapper
- MLflow experiment tracking
- Hyperparameter logging
- Metric collection per epoch
- Model checkpointing
- Validation gate checks (F1 >= 0.84)

### 2.5 TensorRT Export (`trainer/export_to_trt.py`)
- TAO 5.3 model conversion
- FP16/INT8 optimization
- Engine verification
- Calibration data generation
- Performance profiling

### 2.6 MLflow Integration (`trainer/mlflow_tracker.py`)
- Automatic experiment creation
- Parameter and metric logging
- Artifact storage (models, plots)
- Model registry integration
- Dataset versioning

## EmotionNet Fine-Tuning Process

### Architecture
- Base: ResNet18 (pretrained on ImageNet)
- Input: 224x224 RGB images
- Output: 6 emotion classes
- Freeze blocks: [0, 1, 2] (early layers)

### Training Strategy
1. **Stage 1**: Train classifier head only (10 epochs)
2. **Stage 2**: Fine-tune last 2 blocks (20 epochs)
3. **Stage 3**: Fine-tune entire network (30 epochs)

### Data Augmentation
- Random horizontal flip (p=0.5)
- Random rotation (±15°, p=0.3)
- Color jitter (brightness=0.3, contrast=0.3)
- Random crop (0.8-1.0 ratio)
- MixUp (alpha=0.2, p=0.3)

### Optimization
- Optimizer: Adam (lr=0.001)
- Scheduler: Cosine annealing with warm restarts
- Loss: Categorical crossentropy with label smoothing (0.1)
- Class weights: Balanced based on frequency

## Testing Strategy

### Unit Tests
```python
# tests/test_dataset_prep.py
- test_balanced_sampling
- test_stratified_split
- test_manifest_generation
- test_dataset_hash_consistency

# tests/test_training.py
- test_config_loading
- test_checkpoint_saving
- test_metric_calculation
- test_early_stopping
```

### Integration Tests
```python
# tests/test_ml_pipeline.py
- test_end_to_end_training
- test_mlflow_logging
- test_model_export
- test_validation_gates
```

## Implementation Order
1. TAO Docker environment setup
2. Dataset preparation scripts
3. Training configuration files
4. MLflow integration
5. Training orchestrator
6. TensorRT export pipeline

## Success Criteria
- [ ] TAO containers running with GPU access
- [ ] Dataset splits are balanced (50/50 ±5%)
- [ ] Training achieves >84% F1 macro score
- [ ] Model exports to TensorRT successfully
- [ ] MLflow tracks all experiments
- [ ] Tests pass with >75% coverage
