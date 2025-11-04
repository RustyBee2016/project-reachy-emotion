"""
TAO configuration loader and validator.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class InvalidConfigError(Exception):
    """Raised when TAO config is invalid."""
    pass


class TAOConfigLoader:
    """Load and validate TAO training configurations."""
    
    # Required fields for valid config
    REQUIRED_MODEL_FIELDS = ['arch', 'num_classes']
    REQUIRED_TRAINING_FIELDS = ['batch_size', 'num_epochs']
    
    def __init__(self):
        """Initialize config loader."""
        self.config = None
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load TAO configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
        
        Returns:
            Parsed configuration dictionary
        
        Raises:
            InvalidConfigError: If config is invalid or missing required fields
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise InvalidConfigError(f"Config file not found: {config_file}")
        
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise InvalidConfigError(f"Invalid YAML format: {e}")
        
        # Validate required fields
        self._validate_config(config)
        
        self.config = config
        return config
    
    def _validate_config(self, config: Dict[str, Any]):
        """
        Validate configuration has required fields.
        
        Args:
            config: Configuration dictionary to validate
        
        Raises:
            InvalidConfigError: If required fields are missing
        """
        # Check model config
        if 'model_config' in config:
            model_config = config['model_config']
            for field in self.REQUIRED_MODEL_FIELDS:
                if field not in model_config:
                    raise InvalidConfigError(f"Missing required model field: {field}")
        
        # Check training config
        if 'training_config' in config:
            training_config = config['training_config']
            for field in self.REQUIRED_TRAINING_FIELDS:
                if field not in training_config:
                    raise InvalidConfigError(f"Missing required training field: {field}")
    
    def get_augmentation_config(self) -> Dict[str, Any]:
        """
        Get data augmentation configuration.
        
        Returns:
            Augmentation configuration dictionary
        """
        if not self.config:
            return {}
        
        # Try both 'dataset_config' and 'dataset' keys
        dataset = self.config.get('dataset_config') or self.config.get('dataset', {})
        return dataset.get('augmentation', {})
    
    def get_model_config(self) -> Dict[str, Any]:
        """
        Get model configuration.
        
        Returns:
            Model configuration dictionary
        """
        if not self.config:
            return {}
        
        return self.config.get('model_config', {})
    
    def get_training_config(self) -> Dict[str, Any]:
        """
        Get training configuration.
        
        Returns:
            Training configuration dictionary
        """
        if not self.config:
            return {}
        
        return self.config.get('training_config', {})
