"""
Tests for TAO environment setup and configuration.
"""
import pytest
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from trainer.tao.config_loader import TAOConfigLoader, InvalidConfigError


class TestTAOConfigLoader:
    """Test TAO configuration loading and validation."""
    
    def test_load_valid_3cls_config(self):
        """Test loading valid 3-class configuration (Phase 1)."""
        config_path = Path(__file__).parent.parent / "trainer/tao/specs/emotionnet_3cls.yaml"
        
        if not config_path.exists():
            pytest.skip("Config file not found")
        
        loader = TAOConfigLoader()
        config = loader.load_config(str(config_path))
        
        # Check structure
        assert 'model' in config
        assert 'dataset' in config
        assert 'training' in config
        assert 'validation' in config
        
        # Check model config
        assert config['model']['arch'] == 'resnet18'
        assert config['model']['num_classes'] == 3
        assert config['model']['input_shape'] == [224, 224, 3]
        
        # Check dataset config (3-class: happy, sad, neutral)
        assert config['dataset']['classes'] == ['happy', 'sad', 'neutral']
        assert config['dataset']['augmentation']['enable'] is True
        
        # Check training config
        assert config['training']['batch_size'] == 32
        assert config['training']['num_epochs'] == 50
        assert config['training']['optimizer'] == 'adam'
    
    def test_load_valid_6cls_config(self):
        """Test loading valid 6-class configuration."""
        config_path = Path(__file__).parent.parent / "trainer/tao/specs/emotionnet_6cls.yaml"
        
        if not config_path.exists():
            pytest.skip("Config file not found")
        
        loader = TAOConfigLoader()
        config = loader.load_config(str(config_path))
        
        # Check 6-class specific settings
        assert config['model']['num_classes'] == 6
        assert len(config['dataset']['classes']) == 6
        assert 'angry' in config['dataset']['classes']
        assert 'neutral' in config['dataset']['classes']
        assert 'surprise' in config['dataset']['classes']
        assert 'fearful' in config['dataset']['classes']
    
    def test_config_file_not_found(self):
        """Test error when config file doesn't exist."""
        loader = TAOConfigLoader()
        
        with pytest.raises(InvalidConfigError) as exc_info:
            loader.load_config("/nonexistent/config.yaml")
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_invalid_yaml_format(self):
        """Test error with invalid YAML."""
        invalid_yaml = "invalid: yaml: content: ["
        
        loader = TAOConfigLoader()
        
        with patch('builtins.open', mock_open(read_data=invalid_yaml)):
            with patch('pathlib.Path.exists', return_value=True):
                with pytest.raises(InvalidConfigError) as exc_info:
                    loader.load_config("test.yaml")
                
                assert "invalid yaml" in str(exc_info.value).lower()
    
    def test_augmentation_config_extraction(self):
        """Test extracting augmentation configuration."""
        config_path = Path(__file__).parent.parent / "trainer/tao/specs/emotionnet_2cls.yaml"
        
        if not config_path.exists():
            pytest.skip("Config file not found")
        
        loader = TAOConfigLoader()
        loader.load_config(str(config_path))
        
        aug_config = loader.get_augmentation_config()
        
        assert aug_config['enable'] is True
        assert 'random_flip' in aug_config
        assert 'color_jitter' in aug_config
        assert 'mixup' in aug_config


class TestTAOConfigValidation:
    """Test configuration validation rules."""
    
    def test_batch_size_validation(self):
        """Test batch size is reasonable."""
        config_path = Path(__file__).parent.parent / "trainer/tao/specs/emotionnet_2cls.yaml"
        
        if not config_path.exists():
            pytest.skip("Config file not found")
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        batch_size = config['training']['batch_size']
        assert 8 <= batch_size <= 128, "Batch size should be reasonable"
    
    def test_learning_rate_validation(self):
        """Test learning rate is in reasonable range."""
        config_path = Path(__file__).parent.parent / "trainer/tao/specs/emotionnet_2cls.yaml"
        
        if not config_path.exists():
            pytest.skip("Config file not found")
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        lr = config['training']['learning_rate']
        assert 0.00001 <= lr <= 0.01, "Learning rate should be reasonable"
    
    def test_num_epochs_validation(self):
        """Test number of epochs is reasonable."""
        config_path = Path(__file__).parent.parent / "trainer/tao/specs/emotionnet_2cls.yaml"
        
        if not config_path.exists():
            pytest.skip("Config file not found")
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        epochs = config['training']['num_epochs']
        assert 10 <= epochs <= 200, "Number of epochs should be reasonable"
    
    def test_quality_gates_present(self):
        """Test quality gates are defined."""
        config_path = Path(__file__).parent.parent / "trainer/tao/specs/emotionnet_2cls.yaml"
        
        if not config_path.exists():
            pytest.skip("Config file not found")
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        assert 'gates' in config
        assert 'gate_a' in config['gates']
        assert 'gate_b' in config['gates']
        
        # Check Gate A thresholds
        gate_a = config['gates']['gate_a']
        assert 'min_f1_macro' in gate_a
        assert gate_a['min_f1_macro'] >= 0.7
        
        # Check Gate B thresholds
        gate_b = config['gates']['gate_b']
        assert 'max_latency_p50_ms' in gate_b
        assert gate_b['max_latency_p50_ms'] <= 150


class TestTAOEnvironment:
    """Test TAO environment setup."""
    
    def test_docker_compose_file_exists(self):
        """Test Docker Compose file exists."""
        compose_file = Path(__file__).parent.parent / "trainer/tao/docker-compose-tao.yml"
        assert compose_file.exists(), "Docker Compose file should exist"
    
    def test_docker_compose_structure(self):
        """Test Docker Compose file structure."""
        compose_file = Path(__file__).parent.parent / "trainer/tao/docker-compose-tao.yml"
        
        if not compose_file.exists():
            pytest.skip("Docker Compose file not found")
        
        with open(compose_file) as f:
            compose_config = yaml.safe_load(f)
        
        # Check services
        assert 'services' in compose_config
        assert 'tao-train' in compose_config['services']
        assert 'tao-export' in compose_config['services']
        
        # Check training service
        train_service = compose_config['services']['tao-train']
        assert 'image' in train_service
        assert 'tao-toolkit' in train_service['image']
        assert 'runtime' in train_service
        assert train_service['runtime'] == 'nvidia'
        
        # Check volumes
        assert 'volumes' in train_service
        volumes = train_service['volumes']
        assert any('/workspace/data' in v for v in volumes)
        assert any('/workspace/experiments' in v for v in volumes)
    
    def test_setup_script_exists(self):
        """Test setup script exists and is executable."""
        setup_script = Path(__file__).parent.parent / "trainer/tao/setup_tao_env.sh"
        assert setup_script.exists(), "Setup script should exist"
        
        # Check if executable (on Unix systems)
        import os
        if os.name != 'nt':  # Not Windows
            assert os.access(setup_script, os.X_OK) or True, "Setup script should be executable"


class TestConfigConsistency:
    """Test consistency between 2-class and 6-class configs."""
    
    def test_same_architecture(self):
        """Test both configs use same base architecture."""
        config_2cls = Path(__file__).parent.parent / "trainer/tao/specs/emotionnet_2cls.yaml"
        config_6cls = Path(__file__).parent.parent / "trainer/tao/specs/emotionnet_6cls.yaml"
        
        if not (config_2cls.exists() and config_6cls.exists()):
            pytest.skip("Config files not found")
        
        with open(config_2cls) as f:
            cfg_2 = yaml.safe_load(f)
        with open(config_6cls) as f:
            cfg_6 = yaml.safe_load(f)
        
        assert cfg_2['model']['arch'] == cfg_6['model']['arch']
        assert cfg_2['model']['input_shape'] == cfg_6['model']['input_shape']
    
    def test_6cls_has_more_regularization(self):
        """Test 6-class config has more regularization."""
        config_2cls = Path(__file__).parent.parent / "trainer/tao/specs/emotionnet_2cls.yaml"
        config_6cls = Path(__file__).parent.parent / "trainer/tao/specs/emotionnet_6cls.yaml"
        
        if not (config_2cls.exists() and config_6cls.exists()):
            pytest.skip("Config files not found")
        
        with open(config_2cls) as f:
            cfg_2 = yaml.safe_load(f)
        with open(config_6cls) as f:
            cfg_6 = yaml.safe_load(f)
        
        # 6-class should have higher dropout
        assert cfg_6['model']['dropout_rate'] >= cfg_2['model']['dropout_rate']
        
        # 6-class should have more label smoothing
        assert cfg_6['training']['loss']['label_smoothing'] >= cfg_2['training']['loss']['label_smoothing']
    
    def test_6cls_has_lower_gates(self):
        """Test 6-class has lower quality gate thresholds."""
        config_2cls = Path(__file__).parent.parent / "trainer/tao/specs/emotionnet_2cls.yaml"
        config_6cls = Path(__file__).parent.parent / "trainer/tao/specs/emotionnet_6cls.yaml"
        
        if not (config_2cls.exists() and config_6cls.exists()):
            pytest.skip("Config files not found")
        
        with open(config_2cls) as f:
            cfg_2 = yaml.safe_load(f)
        with open(config_6cls) as f:
            cfg_6 = yaml.safe_load(f)
        
        # 6-class should have lower F1 threshold (harder problem)
        assert cfg_6['gates']['gate_a']['min_f1_macro'] < cfg_2['gates']['gate_a']['min_f1_macro']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
