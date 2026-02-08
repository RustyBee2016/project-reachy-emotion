"""
FER Fine-tuning Module for Reachy_Local_08.4.2

EfficientNet-B0 emotion classifier with HSEmotion pretrained weights
for 3-class (happy/sad/neutral) or 8-class emotion classification.

Model path: /media/rusty_admin/project_data/ml_models/efficientnet_b0
Model placeholder: efficientnet-b0-hsemotion
"""

from .config import TrainingConfig, ModelConfig, DataConfig
from .model_efficientnet import (
    HSEmotionEfficientNet,
    create_efficientnet_model,
    load_pretrained_model,
    PHASE1_CLASSES,
)
# Legacy ResNet model (for backward compatibility)
from .model_resnet import EmotionClassifier
from .dataset import EmotionDataset, get_train_transforms, get_val_transforms, validate_dataset
from .train import Trainer, train_model
from .evaluate import compute_metrics, expected_calibration_error
from .export import export_to_onnx, convert_to_tensorrt, export_efficientnet_for_deployment

__all__ = [
    # Config
    "TrainingConfig",
    "ModelConfig", 
    "DataConfig",
    # Model (EfficientNet - primary)
    "HSEmotionEfficientNet",
    "create_efficientnet_model",
    "load_pretrained_model",
    "PHASE1_CLASSES",
    # Model (ResNet - legacy)
    "EmotionClassifier",
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
