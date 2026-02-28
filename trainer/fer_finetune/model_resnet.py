"""
ResNet-50 Emotion Classifier Model

Architecture:
- Backbone: ResNet-50 (ImageNet → AffectNet+RAF-DB pretrained)
- Head: Dropout → FC → num_classes
- Optional: Multi-task head (emotions + valence/arousal)

Model placeholder: resnet50-affectnet-raf-db
Storage path: /media/rusty_admin/project_data/ml_models/resnet50
"""

import torch
import torch.nn as nn
from typing import Optional, Dict, Tuple, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Model placeholder constant
MODEL_PLACEHOLDER = "resnet50-affectnet-raf-db"
MODEL_STORAGE_PATH = "/media/rusty_admin/project_data/ml_models/resnet50"


class EmotionClassifier(nn.Module):
    """
    ResNet-50 based emotion classifier with AffectNet+RAF-DB pretraining.
    
    Supports:
    - 3-class classification (happy/sad/neutral) for Phase 1
    - Multi-class classification (8 emotions) for Phase 2+
    - Optional multi-task learning (emotions + valence/arousal)
    
    Transfer learning strategy:
    1. Phase 1: Freeze backbone, train classification head
    2. Phase 2: Unfreeze layer4 + fc, fine-tune with lower LR
    """
    
    def __init__(
        self,
        backbone: str = "resnet50",
        num_classes: int = 3,
        dropout_rate: float = 0.3,
        pretrained_weights: str = MODEL_PLACEHOLDER,
        use_multi_task: bool = False,
    ):
        """
        Initialize emotion classifier.
        
        Args:
            backbone: Backbone architecture ("resnet50", "resnet18", "efficientnet_b0")
            num_classes: Number of emotion classes (3 for Phase 1, 8 for full)
            dropout_rate: Dropout probability before classification head
            pretrained_weights: Weight source - MODEL_PLACEHOLDER or path to .pth
            use_multi_task: Enable multi-task head (emotions + VA regression)
        """
        super().__init__()
        
        self.backbone_name = backbone
        self.num_classes = num_classes
        self.pretrained_weights = pretrained_weights
        self.use_multi_task = use_multi_task
        
        # Load backbone
        self.backbone = self._create_backbone(backbone, pretrained_weights)
        
        # Get feature dimension from backbone
        self.feature_dim = self._get_feature_dim()
        
        # Classification head
        self.dropout = nn.Dropout(p=dropout_rate)
        self.fc = nn.Linear(self.feature_dim, num_classes)
        
        # Optional multi-task head for valence/arousal regression
        if use_multi_task:
            self.va_head = nn.Sequential(
                nn.Dropout(p=dropout_rate),
                nn.Linear(self.feature_dim, 64),
                nn.ReLU(inplace=True),
                nn.Linear(64, 2),  # valence, arousal
                nn.Tanh(),  # VA typically in [-1, 1]
            )
        else:
            self.va_head = None
        
        # Initialize classification head
        self._init_head()
        
        logger.info(f"EmotionClassifier initialized: {backbone}, {num_classes} classes")
        logger.info(f"Pretrained weights: {pretrained_weights}")
        logger.info(f"Multi-task: {use_multi_task}")
    
    def _create_backbone(self, backbone: str, pretrained_weights: str) -> nn.Module:
        """
        Create backbone network with appropriate pretrained weights.
        
        Args:
            backbone: Architecture name
            pretrained_weights: Weight source
        
        Returns:
            Backbone module (without classification head)
        """
        try:
            import timm
            use_timm = True
        except ImportError:
            use_timm = False
            logger.warning("timm not available, using torchvision")
        
        if use_timm:
            return self._create_timm_backbone(backbone, pretrained_weights)
        else:
            return self._create_torchvision_backbone(backbone, pretrained_weights)
    
    def _create_timm_backbone(self, backbone: str, pretrained_weights: str) -> nn.Module:
        """Create backbone using timm library."""
        import timm
        
        # Map backbone names to timm model names
        timm_names = {
            "resnet50": "resnet50",
            "resnet18": "resnet18",
            "efficientnet_b0": "efficientnet_b0",
            "mobilenetv3": "mobilenetv3_small_100",
        }
        
        model_name = timm_names.get(backbone, backbone)
        
        # Check if we should load custom weights or ImageNet
        if pretrained_weights == MODEL_PLACEHOLDER:
            # Placeholder: start with ImageNet, custom weights loaded separately
            logger.info(f"Using placeholder '{MODEL_PLACEHOLDER}' - loading ImageNet weights")
            logger.info(f"Custom AffectNet+RAF-DB weights should be loaded from: {MODEL_STORAGE_PATH}")
            model = timm.create_model(model_name, pretrained=True, num_classes=0)
        elif Path(pretrained_weights).exists():
            # Load custom weights from file
            logger.info(f"Loading custom weights from: {pretrained_weights}")
            model = timm.create_model(model_name, pretrained=False, num_classes=0)
            self._load_custom_weights(model, pretrained_weights)
        else:
            # Fallback to ImageNet
            logger.info(f"Loading ImageNet pretrained weights for {model_name}")
            model = timm.create_model(model_name, pretrained=True, num_classes=0)
        
        return model
    
    def _create_torchvision_backbone(self, backbone: str, pretrained_weights: str) -> nn.Module:
        """Create backbone using torchvision (fallback)."""
        from torchvision import models
        from torchvision.models import ResNet50_Weights, ResNet18_Weights
        
        if backbone == "resnet50":
            if pretrained_weights == MODEL_PLACEHOLDER or pretrained_weights == "imagenet":
                model = models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V1)
            else:
                model = models.resnet50(weights=None)
                if Path(pretrained_weights).exists():
                    self._load_custom_weights(model, pretrained_weights)
            
            # Remove classification head
            model.fc = nn.Identity()
            
        elif backbone == "resnet18":
            if pretrained_weights == MODEL_PLACEHOLDER or pretrained_weights == "imagenet":
                model = models.resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
            else:
                model = models.resnet18(weights=None)
                if Path(pretrained_weights).exists():
                    self._load_custom_weights(model, pretrained_weights)
            
            model.fc = nn.Identity()
        else:
            raise ValueError(f"Unsupported backbone: {backbone}")
        
        return model
    
    def _load_custom_weights(self, model: nn.Module, weights_path: str):
        """Load custom pretrained weights (e.g., AffectNet+RAF-DB)."""
        checkpoint = torch.load(weights_path, map_location='cpu', weights_only=False)
        
        # Handle different checkpoint formats
        if 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
        elif 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
        else:
            state_dict = checkpoint
        
        # Remove 'module.' prefix if present (from DataParallel)
        state_dict = {k.replace('module.', ''): v for k, v in state_dict.items()}
        
        # Load with strict=False to handle head mismatch
        missing, unexpected = model.load_state_dict(state_dict, strict=False)
        
        if missing:
            logger.warning(f"Missing keys when loading weights: {missing[:5]}...")
        if unexpected:
            logger.warning(f"Unexpected keys when loading weights: {unexpected[:5]}...")
        
        logger.info(f"Loaded custom weights from {weights_path}")
    
    def _get_feature_dim(self) -> int:
        """Determine backbone output feature dimension."""
        with torch.no_grad():
            dummy = torch.zeros(1, 3, 224, 224)
            features = self.backbone(dummy)
            if isinstance(features, tuple):
                features = features[0]
            return features.shape[1]
    
    def _init_head(self):
        """Initialize classification head weights."""
        nn.init.xavier_uniform_(self.fc.weight)
        nn.init.zeros_(self.fc.bias)
        
        if self.va_head is not None:
            for module in self.va_head.modules():
                if isinstance(module, nn.Linear):
                    nn.init.xavier_uniform_(module.weight)
                    nn.init.zeros_(module.bias)
    
    def forward(
        self, 
        x: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass.
        
        Args:
            x: Input tensor [B, 3, H, W]
        
        Returns:
            Dictionary with:
            - 'logits': Classification logits [B, num_classes]
            - 'features': Backbone features [B, feature_dim]
            - 'va' (optional): Valence/arousal predictions [B, 2]
        """
        # Extract features
        features = self.backbone(x)
        if isinstance(features, tuple):
            features = features[0]
        
        # Classification
        x_drop = self.dropout(features)
        logits = self.fc(x_drop)
        
        output = {
            'logits': logits,
            'features': features,
        }
        
        # Multi-task VA prediction
        if self.va_head is not None:
            va = self.va_head(features)
            output['va'] = va
        
        return output
    
    def forward_simple(self, x: torch.Tensor) -> torch.Tensor:
        """Simple forward returning only logits (for inference)."""
        return self.forward(x)['logits']
    
    def freeze_backbone(self):
        """Freeze all backbone parameters for Phase 1 training."""
        for param in self.backbone.parameters():
            param.requires_grad = False
        logger.info("Backbone frozen")
    
    def unfreeze_backbone(self):
        """Unfreeze all backbone parameters."""
        for param in self.backbone.parameters():
            param.requires_grad = True
        logger.info("Backbone unfrozen")
    
    def unfreeze_layers(self, layer_names: List[str]):
        """
        Selectively unfreeze specific layers for Phase 2 training.
        
        Args:
            layer_names: List of layer name patterns to unfreeze
                        e.g., ["layer4", "fc"] for ResNet
        """
        unfrozen_count = 0
        for name, param in self.backbone.named_parameters():
            for layer_name in layer_names:
                if layer_name in name:
                    param.requires_grad = True
                    unfrozen_count += 1
                    break
        
        logger.info(f"Unfrozen {unfrozen_count} parameters in layers: {layer_names}")
    
    def get_trainable_params(self) -> int:
        """Count trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
    
    def get_total_params(self) -> int:
        """Count total parameters."""
        return sum(p.numel() for p in self.parameters())
    
    def get_param_groups(self, base_lr: float) -> List[Dict]:
        """
        Get parameter groups with differential learning rates.
        
        Backbone uses 10x lower LR than head.
        
        Args:
            base_lr: Base learning rate for head
        
        Returns:
            List of param group dicts for optimizer
        """
        return [
            {
                'params': self.backbone.parameters(),
                'lr': base_lr * 0.1,
                'name': 'backbone'
            },
            {
                'params': self.fc.parameters(),
                'lr': base_lr,
                'name': 'fc_head'
            },
        ] + ([{
            'params': self.va_head.parameters(),
            'lr': base_lr,
            'name': 'va_head'
        }] if self.va_head is not None else [])


def load_pretrained_model(
    checkpoint_path: str,
    num_classes: int = 3,
    device: str = "cuda",
) -> EmotionClassifier:
    """
    Load a trained EmotionClassifier from checkpoint.
    
    Args:
        checkpoint_path: Path to checkpoint .pth file
        num_classes: Number of classes (must match checkpoint)
        device: Target device
    
    Returns:
        Loaded model in eval mode
    """
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    
    # Extract config from checkpoint
    config = checkpoint.get('config', {})
    
    model = EmotionClassifier(
        backbone=config.get('backbone', 'resnet50'),
        num_classes=num_classes,
        dropout_rate=config.get('dropout_rate', 0.3),
        pretrained_weights="imagenet",  # Weights come from checkpoint
        use_multi_task=config.get('use_multi_task', False),
    )
    
    # Load state dict
    if 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)
    
    model.to(device)
    model.eval()
    
    logger.info(f"Loaded model from {checkpoint_path}")
    return model


class StudentEmotionClassifier(EmotionClassifier):
    """
    Lightweight student model for knowledge distillation.
    
    Uses ResNet-18 or MobileNetV3 as backbone for faster
    inference on Jetson Xavier NX.
    """
    
    def __init__(
        self,
        backbone: str = "resnet18",
        num_classes: int = 3,
        dropout_rate: float = 0.2,
        pretrained_weights: str = "imagenet",
    ):
        super().__init__(
            backbone=backbone,
            num_classes=num_classes,
            dropout_rate=dropout_rate,
            pretrained_weights=pretrained_weights,
            use_multi_task=False,  # Students don't use multi-task
        )
        
        logger.info(f"StudentEmotionClassifier initialized: {backbone}")


class DistillationLoss(nn.Module):
    """
    Knowledge distillation loss combining hard and soft targets.
    
    Loss = α * CE(student, hard_labels) + (1-α) * KL(student_soft, teacher_soft)
    """
    
    def __init__(
        self,
        temperature: float = 4.0,
        alpha: float = 0.5,
    ):
        """
        Args:
            temperature: Softmax temperature for soft targets
            alpha: Weight for hard label loss (1-alpha for soft)
        """
        super().__init__()
        self.temperature = temperature
        self.alpha = alpha
        self.ce_loss = nn.CrossEntropyLoss()
        self.kl_loss = nn.KLDivLoss(reduction='batchmean')
    
    def forward(
        self,
        student_logits: torch.Tensor,
        teacher_logits: torch.Tensor,
        labels: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute distillation loss.
        
        Args:
            student_logits: Student model outputs [B, C]
            teacher_logits: Teacher model outputs [B, C]
            labels: Ground truth labels [B]
        
        Returns:
            Combined loss scalar
        """
        # Hard label loss
        hard_loss = self.ce_loss(student_logits, labels)
        
        # Soft label loss (KL divergence)
        student_soft = nn.functional.log_softmax(
            student_logits / self.temperature, dim=1
        )
        teacher_soft = nn.functional.softmax(
            teacher_logits / self.temperature, dim=1
        )
        soft_loss = self.kl_loss(student_soft, teacher_soft) * (self.temperature ** 2)
        
        # Combined loss
        return self.alpha * hard_loss + (1 - self.alpha) * soft_loss
