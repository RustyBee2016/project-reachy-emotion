"""
EfficientNet-B0 Emotion Classifier Model (HSEmotion)

Architecture:
- Backbone: EfficientNet-B0 (HSEmotion enet_b0_8_best_vgaf pretrained on VGGFace2 + AffectNet)
- Head: Dropout → FC → num_classes
- Optional: Multi-task head (emotions + valence/arousal)

Model source: HSEmotion / EmotiEffLib
Storage path: /media/rusty_admin/project_data/ml_models/efficientnet_b0

Performance characteristics (Jetson Xavier NX):
- Latency: ~40ms p50 (3× headroom vs 120ms budget)
- Memory: ~0.8 GB GPU (3× headroom vs 2.5 GB budget)
- Accuracy: Comparable to ResNet-50 with HSEmotion pretraining
"""

import torch
import torch.nn as nn
from typing import Optional, Dict, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Model constants
MODEL_NAME = "enet_b0_8_best_vgaf"
MODEL_STORAGE_PATH = "/media/rusty_admin/project_data/ml_models/efficientnet_b0"

# HSEmotion class mapping (8-class)
HSEMOTION_CLASSES = [
    "anger", "contempt", "disgust", "fear", 
    "happy", "neutral", "sad", "surprise"
]

# 3-class mapping for Phase 1 (happy, sad, neutral)
PHASE1_CLASSES = ["happy", "sad", "neutral"]
PHASE1_TO_HSEMOTION = {"happy": 4, "sad": 6, "neutral": 5}  # Indices in HSEMOTION_CLASSES


class HSEmotionEfficientNet(nn.Module):
    """
    EfficientNet-B0 emotion classifier using HSEmotion pretrained weights.
    
    HSEmotion provides video-optimized weights trained on VGGFace2 + AffectNet,
    specifically designed for facial emotion recognition tasks.
    
    Supports:
    - 3-class classification (happy/sad/neutral) for Phase 1
    - Multi-class classification (8 emotions) for Phase 2+
    - Optional multi-task learning (emotions + valence/arousal)
    
    Transfer learning strategy:
    1. Phase 1: Freeze backbone, train classification head
    2. Phase 2: Unfreeze final blocks, fine-tune with lower LR
    """
    
    def __init__(
        self,
        num_classes: int = 3,
        dropout_rate: float = 0.3,
        pretrained_weights: str = MODEL_NAME,
        use_multi_task: bool = False,
        weights_path: Optional[str] = None,
    ):
        """
        Initialize HSEmotion EfficientNet-B0 classifier.
        
        Args:
            num_classes: Number of emotion classes (3 for Phase 1, 8 for full)
            dropout_rate: Dropout probability before classification head
            pretrained_weights: Weight source - MODEL_NAME or "imagenet"
            use_multi_task: Enable multi-task head (emotions + VA regression)
            weights_path: Optional explicit path to weights file
        """
        super().__init__()
        
        self.num_classes = num_classes
        self.pretrained_weights = pretrained_weights
        self.use_multi_task = use_multi_task
        
        # Load backbone
        self.backbone, self.feature_dim = self._create_backbone(
            pretrained_weights, weights_path
        )
        
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
        
        logger.info(f"HSEmotionEfficientNet initialized: {num_classes} classes")
        logger.info(f"Pretrained weights: {pretrained_weights}")
        logger.info(f"Feature dimension: {self.feature_dim}")
        logger.info(f"Multi-task: {use_multi_task}")
    
    def _create_backbone(
        self, 
        pretrained_weights: str,
        weights_path: Optional[str]
    ) -> tuple:
        """
        Create EfficientNet-B0 backbone with HSEmotion weights.
        
        Priority:
        1. Explicit weights_path if provided
        2. HSEmotion weights from emotiefflib
        3. timm pretrained weights
        4. ImageNet fallback via torchvision
        
        Returns:
            Tuple of (backbone_module, feature_dimension)
        """
        feature_dim = 1280  # EfficientNet-B0 feature dimension
        
        # Try explicit weights path first
        if weights_path and Path(weights_path).exists():
            logger.info(f"Loading weights from explicit path: {weights_path}")
            return self._load_from_checkpoint(weights_path), feature_dim
        
        # Try HSEmotion / emotiefflib
        if pretrained_weights == MODEL_NAME:
            backbone = self._try_hsemotion_weights()
            if backbone is not None:
                return backbone, feature_dim
        
        # Try timm
        backbone = self._try_timm_backbone(pretrained_weights)
        if backbone is not None:
            return backbone, feature_dim
        
        # Fallback to torchvision
        logger.warning("Using torchvision EfficientNet-B0 (ImageNet weights)")
        return self._create_torchvision_backbone(), feature_dim
    
    def _try_hsemotion_weights(self) -> Optional[nn.Module]:
        """Try loading HSEmotion weights via emotiefflib."""
        try:
            from hsemotion.facial_emotions import HSEmotionRecognizer
            
            logger.info("Loading HSEmotion enet_b0_8_best_vgaf weights")
            
            # HSEmotion provides a recognizer with the model
            recognizer = HSEmotionRecognizer(model_name='enet_b0_8_best_vgaf')
            
            # Extract the backbone (EfficientNet without final FC)
            model = recognizer.model
            
            # Remove the classification head - we'll add our own
            if hasattr(model, 'classifier'):
                model.classifier = nn.Identity()
            elif hasattr(model, 'fc'):
                model.fc = nn.Identity()
            
            logger.info("HSEmotion weights loaded successfully")
            return model
            
        except ImportError:
            logger.warning("emotiefflib/hsemotion not installed, trying alternatives")
            return None
        except Exception as e:
            logger.warning(f"Failed to load HSEmotion weights: {e}")
            return None
    
    def _try_timm_backbone(self, pretrained_weights: str) -> Optional[nn.Module]:
        """Try creating backbone using timm library."""
        try:
            import timm
            
            # Use ImageNet pretrained if HSEmotion not available
            use_pretrained = pretrained_weights in [MODEL_NAME, "imagenet"]
            
            logger.info(f"Loading EfficientNet-B0 via timm (pretrained={use_pretrained})")
            
            model = timm.create_model(
                'efficientnet_b0',
                pretrained=use_pretrained,
                num_classes=0,  # Remove classification head
            )
            
            logger.info("timm EfficientNet-B0 loaded successfully")
            return model
            
        except ImportError:
            logger.warning("timm not installed, trying torchvision")
            return None
        except Exception as e:
            logger.warning(f"Failed to load timm model: {e}")
            return None
    
    def _create_torchvision_backbone(self) -> nn.Module:
        """Create backbone using torchvision (fallback)."""
        from torchvision import models
        from torchvision.models import EfficientNet_B0_Weights
        
        model = models.efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)
        
        # Remove classification head
        model.classifier = nn.Identity()
        
        return model
    
    def _load_from_checkpoint(self, checkpoint_path: str) -> nn.Module:
        """Load model from a saved checkpoint."""
        try:
            import timm
            model = timm.create_model('efficientnet_b0', pretrained=False, num_classes=0)
        except ImportError:
            from torchvision import models
            model = models.efficientnet_b0(weights=None)
            model.classifier = nn.Identity()
        
        checkpoint = torch.load(checkpoint_path, map_location='cpu')
        
        # Handle different checkpoint formats
        if 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
        elif 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
        else:
            state_dict = checkpoint
        
        # Remove 'module.' prefix if present (from DataParallel)
        state_dict = {k.replace('module.', ''): v for k, v in state_dict.items()}
        
        # Filter out classifier weights (we'll use our own head)
        state_dict = {k: v for k, v in state_dict.items() 
                     if not k.startswith('classifier') and not k.startswith('fc')}
        
        missing, unexpected = model.load_state_dict(state_dict, strict=False)
        
        if missing:
            logger.debug(f"Missing keys (expected for head): {len(missing)}")
        if unexpected:
            logger.warning(f"Unexpected keys: {unexpected[:5]}...")
        
        logger.info(f"Loaded checkpoint from {checkpoint_path}")
        return model
    
    def _init_head(self):
        """Initialize classification head weights."""
        nn.init.xavier_uniform_(self.fc.weight)
        nn.init.zeros_(self.fc.bias)
        
        if self.va_head is not None:
            for module in self.va_head.modules():
                if isinstance(module, nn.Linear):
                    nn.init.xavier_uniform_(module.weight)
                    nn.init.zeros_(module.bias)
    
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Forward pass.
        
        Args:
            x: Input tensor [B, 3, H, W] (expected 224x224)
        
        Returns:
            Dictionary with:
            - 'logits': Classification logits [B, num_classes]
            - 'features': Backbone features [B, feature_dim]
            - 'va' (optional): Valence/arousal predictions [B, 2]
        """
        # Extract features
        features = self.backbone(x)
        
        # Handle tuple output (some models return tuple)
        if isinstance(features, tuple):
            features = features[0]
        
        # Flatten if needed
        if features.dim() > 2:
            features = features.mean(dim=[2, 3])  # Global average pooling
        
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
        """Simple forward returning only logits (for inference/ONNX export)."""
        return self.forward(x)['logits']
    
    def freeze_backbone(self):
        """Freeze all backbone parameters for Phase 1 training."""
        for param in self.backbone.parameters():
            param.requires_grad = False
        logger.info("Backbone frozen - only classification head will train")
    
    def unfreeze_backbone(self):
        """Unfreeze all backbone parameters."""
        for param in self.backbone.parameters():
            param.requires_grad = True
        logger.info("Backbone fully unfrozen")
    
    def unfreeze_layers(self, layer_patterns: List[str]):
        """
        Selectively unfreeze specific layers for Phase 2 training.
        
        For EfficientNet-B0, typical patterns:
        - "blocks.6" — Final MBConv block
        - "blocks.5" — Second-to-last block
        - "conv_head" — Final convolution
        
        Args:
            layer_patterns: List of layer name patterns to unfreeze
        """
        unfrozen_count = 0
        for name, param in self.backbone.named_parameters():
            for pattern in layer_patterns:
                if pattern in name:
                    param.requires_grad = True
                    unfrozen_count += 1
                    break
        
        logger.info(f"Unfrozen {unfrozen_count} parameters matching: {layer_patterns}")
    
    def get_trainable_params(self) -> int:
        """Count trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
    
    def get_total_params(self) -> int:
        """Count total parameters."""
        return sum(p.numel() for p in self.parameters())
    
    def get_param_groups(self, base_lr: float) -> List[Dict]:
        """
        Get parameter groups with differential learning rates.
        
        Backbone uses 10x lower LR than head for fine-tuning.
        
        Args:
            base_lr: Base learning rate for head
        
        Returns:
            List of param group dicts for optimizer
        """
        groups = [
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
        ]
        
        if self.va_head is not None:
            groups.append({
                'params': self.va_head.parameters(),
                'lr': base_lr,
                'name': 'va_head'
            })
        
        return groups


def create_efficientnet_model(
    num_classes: int = 3,
    dropout_rate: float = 0.3,
    pretrained: bool = True,
    weights_path: Optional[str] = None,
    use_multi_task: bool = False,
) -> HSEmotionEfficientNet:
    """
    Factory function to create HSEmotion EfficientNet-B0 model.
    
    Args:
        num_classes: Number of output classes
        dropout_rate: Dropout rate for regularization
        pretrained: Whether to use pretrained weights
        weights_path: Optional explicit path to weights
        use_multi_task: Enable multi-task learning
    
    Returns:
        Configured HSEmotionEfficientNet model
    """
    pretrained_weights = MODEL_NAME if pretrained else None
    
    return HSEmotionEfficientNet(
        num_classes=num_classes,
        dropout_rate=dropout_rate,
        pretrained_weights=pretrained_weights,
        use_multi_task=use_multi_task,
        weights_path=weights_path,
    )


def load_pretrained_model(
    checkpoint_path: str,
    num_classes: int = 3,
    device: str = "cuda",
    dropout_rate: float = 0.3,
    use_multi_task: bool = False,
    weights_path: Optional[str] = None,
) -> HSEmotionEfficientNet:
    """Load a trained EfficientNet-B0 model from checkpoint."""
    import torch

    checkpoint = torch.load(checkpoint_path, map_location=device)
    config = checkpoint.get("config", {})

    model = create_efficientnet_model(
        num_classes=config.get("num_classes", num_classes),
        dropout_rate=config.get("dropout_rate", dropout_rate),
        pretrained=False,
        weights_path=weights_path,
        use_multi_task=config.get("use_multi_task", use_multi_task),
    )

    if "model_state_dict" in checkpoint:
        state_dict = checkpoint["model_state_dict"]
    elif "state_dict" in checkpoint:
        state_dict = checkpoint["state_dict"]
    else:
        state_dict = checkpoint

    state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    logger.info(f"Loaded EfficientNet checkpoint: {checkpoint_path}")
    return model


def get_hsemotion_class_mapping(target_classes: List[str]) -> Dict[int, int]:
    """
    Get mapping from HSEmotion 8-class indices to target class indices.
    
    Useful when using full HSEmotion weights for binary classification.
    
    Args:
        target_classes: List of target class names (e.g., ["happy", "sad"])
    
    Returns:
        Dict mapping HSEmotion index to target index
    """
    mapping = {}
    for target_idx, class_name in enumerate(target_classes):
        if class_name.lower() in [c.lower() for c in HSEMOTION_CLASSES]:
            hsemotion_idx = [c.lower() for c in HSEMOTION_CLASSES].index(class_name.lower())
            mapping[hsemotion_idx] = target_idx
    
    return mapping
