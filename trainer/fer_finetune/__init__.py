"""
FER Fine-tuning Module for Reachy_Local_08.4.2

ResNet-50 emotion classifier fine-tuned on AffectNet + RAF-DB datasets
for binary (happy/sad) or multi-class emotion classification.

Model path: /media/rusty_admin/project_data/ml_models/resnet50
Model placeholder: resnet50-affectnet-raf-db
"""

from .config import TrainingConfig, ModelConfig, DataConfig
from .model import EmotionClassifier, load_pretrained_model
from .dataset import EmotionDataset, get_train_transforms, get_val_transforms, validate_dataset
from .train import Trainer, train_model
from .evaluate import compute_metrics, expected_calibration_error
from .export import export_to_onnx, convert_to_tensorrt, export_efficientnet_for_deployment

__all__ = [
    # Config
    "TrainingConfig",
    "ModelConfig", 
    "DataConfig",
    # Model
    "EmotionClassifier",
    "load_pretrained_model",
    # Dataset
    "EmotionDataset",
    "get_train_transforms",
    "get_val_transforms",
    "validate_dataset",
    # Training
    "Trainer",
    "train_model",
    # Evaluation
    "compute_metrics",
    "expected_calibration_error",
    # Export
    "export_to_onnx",
    "convert_to_tensorrt",
    "export_efficientnet_for_deployment",
]

__version__ = "0.8.4.2"
