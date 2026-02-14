"""
Configuration module for ResNet-50 emotion classifier fine-tuning.

Supports:
- AffectNet + RAF-DB pre-trained weights
- Multi-stage training (frozen backbone → selective unfreezing)
- Quality gates aligned with requirements_08.4.2.md
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
import yaml
import json


@dataclass
class ModelConfig:
    """Model architecture configuration."""
    
    # Architecture
    backbone: str = "resnet50"
    pretrained_weights: str = "resnet50-affectnet-raf-db"  # Placeholder for AffectNet+RAF-DB weights
    num_classes: int = 3  # Ternary: happy, sad, neutral (expandable to 8)
    input_size: int = 224
    
    # Classification head
    dropout_rate: float = 0.3
    use_multi_task: bool = False  # Optional: emotions + valence/arousal
    
    # Transfer learning
    freeze_backbone_epochs: int = 5
    unfreeze_layers: List[str] = field(default_factory=lambda: ["layer4", "fc"])
    
    # Model storage path on Ubuntu 1
    model_storage_path: str = "/media/rusty_admin/project_data/ml_models/resnet50"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "backbone": self.backbone,
            "pretrained_weights": self.pretrained_weights,
            "num_classes": self.num_classes,
            "input_size": self.input_size,
            "dropout_rate": self.dropout_rate,
            "use_multi_task": self.use_multi_task,
            "freeze_backbone_epochs": self.freeze_backbone_epochs,
            "unfreeze_layers": self.unfreeze_layers,
            "model_storage_path": self.model_storage_path,
        }


@dataclass
class DataConfig:
    """Dataset configuration."""
    
    # Paths
    data_root: str = "/media/project_data/reachy_emotion/videos"
    train_dir: str = "train"
    val_dir: str = "test"
    
    # Class mapping (binary default, expandable)
    class_names: List[str] = field(default_factory=lambda: ["happy", "sad", "neutral"])
    
    # For multi-class expansion
    full_class_names: List[str] = field(default_factory=lambda: [
        "neutral", "happy", "sad", "anger", "fear", "disgust", "surprise", "contempt"
    ])
    
    # Data loading
    batch_size: int = 32
    num_workers: int = 4
    pin_memory: bool = True
    
    # Frame extraction from videos
    frame_sampling: str = "middle"  # "middle", "random", "multi"
    frames_per_video: int = 1  # For "multi" sampling
    
    # Augmentation
    augmentation_enabled: bool = True
    mixup_alpha: float = 0.2
    mixup_probability: float = 0.3
    
    # Normalization (ImageNet stats - used by AffectNet pretrained models)
    image_mean: List[float] = field(default_factory=lambda: [0.485, 0.456, 0.406])
    image_std: List[float] = field(default_factory=lambda: [0.229, 0.224, 0.225])
    
    # Real-world test set distribution (reflects actual usage patterns)
    # Training uses 1:1:1 balanced, but real-world evaluation should reflect
    # that users are neutral ~75% of the time
    realworld_test_distribution: Dict[str, float] = field(default_factory=lambda: {
        "neutral": 0.75,  # Most common state
        "happy": 0.15,    # Occasional positive
        "sad": 0.10,      # Less frequent negative
    })
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_root": self.data_root,
            "train_dir": self.train_dir,
            "val_dir": self.val_dir,
            "class_names": self.class_names,
            "batch_size": self.batch_size,
            "num_workers": self.num_workers,
            "frame_sampling": self.frame_sampling,
            "augmentation_enabled": self.augmentation_enabled,
            "mixup_alpha": self.mixup_alpha,
        }


@dataclass
class TrainingConfig:
    """Complete training configuration."""
    
    # Sub-configs
    model: ModelConfig = field(default_factory=ModelConfig)
    data: DataConfig = field(default_factory=DataConfig)
    
    # Training hyperparameters
    num_epochs: int = 50
    learning_rate: float = 1e-4
    weight_decay: float = 1e-4
    
    # Learning rate schedule
    lr_scheduler: str = "cosine"  # "cosine", "step", "plateau"
    warmup_epochs: int = 3
    min_lr: float = 1e-6
    
    # Regularization
    label_smoothing: float = 0.1
    gradient_clip_norm: float = 1.0
    
    # Class imbalance handling
    use_class_weights: bool = True  # Weight loss by inverse class frequency
    class_weight_power: float = 0.5  # Dampening factor (1.0 = full inverse, 0.5 = sqrt)
    
    # Early stopping
    early_stopping_enabled: bool = True
    patience: int = 10
    min_delta: float = 0.001
    monitor_metric: str = "val_f1_macro"
    
    # Mixed precision
    mixed_precision: bool = True
    
    # Checkpointing
    checkpoint_dir: str = "/workspace/checkpoints"
    save_best_only: bool = True
    save_interval: int = 5
    
    # Quality gates (from requirements_08.4.2.md)
    gate_a_min_f1_macro: float = 0.84
    gate_a_min_per_class_f1: float = 0.75
    gate_a_min_balanced_accuracy: float = 0.85
    gate_a_max_ece: float = 0.08
    gate_a_max_brier: float = 0.16
    
    gate_b_max_latency_p50_ms: float = 120.0
    gate_b_max_latency_p95_ms: float = 250.0
    gate_b_max_gpu_memory_gb: float = 2.5
    gate_b_min_f1_macro: float = 0.80
    gate_b_min_per_class_f1: float = 0.72
    
    # MLflow tracking
    mlflow_tracking_uri: str = "file:///workspace/mlruns"
    mlflow_experiment_name: str = "resnet50_emotion_finetune"
    
    # Reproducibility
    seed: int = 42
    deterministic: bool = True
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> "TrainingConfig":
        """Load configuration from YAML file."""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        
        model_config = ModelConfig(**data.get('model', {}))
        data_config = DataConfig(**data.get('data', {}))
        
        # Remove nested configs from data dict
        data.pop('model', None)
        data.pop('data', None)
        
        return cls(model=model_config, data=data_config, **data)
    
    def to_yaml(self, yaml_path: str):
        """Save configuration to YAML file."""
        data = {
            'model': self.model.to_dict(),
            'data': self.data.to_dict(),
            'num_epochs': self.num_epochs,
            'learning_rate': self.learning_rate,
            'weight_decay': self.weight_decay,
            'lr_scheduler': self.lr_scheduler,
            'warmup_epochs': self.warmup_epochs,
            'min_lr': self.min_lr,
            'label_smoothing': self.label_smoothing,
            'gradient_clip_norm': self.gradient_clip_norm,
            'early_stopping_enabled': self.early_stopping_enabled,
            'patience': self.patience,
            'min_delta': self.min_delta,
            'monitor_metric': self.monitor_metric,
            'mixed_precision': self.mixed_precision,
            'checkpoint_dir': self.checkpoint_dir,
            'save_best_only': self.save_best_only,
            'save_interval': self.save_interval,
            'gate_a_min_f1_macro': self.gate_a_min_f1_macro,
            'gate_a_min_per_class_f1': self.gate_a_min_per_class_f1,
            'gate_a_min_balanced_accuracy': self.gate_a_min_balanced_accuracy,
            'gate_a_max_ece': self.gate_a_max_ece,
            'gate_a_max_brier': self.gate_a_max_brier,
            'mlflow_tracking_uri': self.mlflow_tracking_uri,
            'mlflow_experiment_name': self.mlflow_experiment_name,
            'seed': self.seed,
            'deterministic': self.deterministic,
        }
        
        with open(yaml_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MLflow logging."""
        return {
            **self.model.to_dict(),
            **self.data.to_dict(),
            'num_epochs': self.num_epochs,
            'learning_rate': self.learning_rate,
            'weight_decay': self.weight_decay,
            'lr_scheduler': self.lr_scheduler,
            'warmup_epochs': self.warmup_epochs,
            'label_smoothing': self.label_smoothing,
            'mixed_precision': self.mixed_precision,
            'seed': self.seed,
        }


# Default configuration for 3-class emotion classification (happy, sad, neutral)
DEFAULT_CONFIG = TrainingConfig()

# Configuration for 8-class emotion classification
MULTICLASS_CONFIG = TrainingConfig(
    model=ModelConfig(
        num_classes=8,
        use_multi_task=True,
    ),
    data=DataConfig(
        class_names=["neutral", "happy", "sad", "anger", "fear", "disgust", "surprise", "contempt"],
    ),
)
