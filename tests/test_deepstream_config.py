"""
Tests for DeepStream configuration files and pipeline setup.
"""
import pytest
from pathlib import Path
import configparser


class TestDeepStreamConfigs:
    """Test DeepStream configuration files."""
    
    def test_pipeline_config_exists(self):
        """Test main pipeline config exists."""
        config_file = Path(__file__).parent.parent / "jetson/deepstream/emotion_pipeline.txt"
        assert config_file.exists(), "Pipeline config should exist"
    
    def test_inference_config_exists(self):
        """Test inference config exists."""
        config_file = Path(__file__).parent.parent / "jetson/deepstream/emotion_inference.txt"
        assert config_file.exists(), "Inference config should exist"
    
    def test_labels_file_exists(self):
        """Test labels file exists."""
        labels_file = Path(__file__).parent.parent / "jetson/deepstream/emotion_labels.txt"
        assert labels_file.exists(), "Labels file should exist"
    
    def test_labels_content(self):
        """Test labels file has correct emotions."""
        labels_file = Path(__file__).parent.parent / "jetson/deepstream/emotion_labels.txt"
        
        with open(labels_file) as f:
            labels = [line.strip() for line in f if line.strip()]
        
        assert 'happy' in labels
        assert 'sad' in labels
        assert len(labels) >= 2
    
    def test_pipeline_config_structure(self):
        """Test pipeline config has required sections."""
        config_file = Path(__file__).parent.parent / "jetson/deepstream/emotion_pipeline.txt"
        
        config = configparser.ConfigParser()
        config.read(config_file)
        
        # Check required sections
        assert 'application' in config.sections()
        assert 'source0' in config.sections()
        assert 'streammux' in config.sections()
        assert 'primary-gie' in config.sections()
    
    def test_pipeline_performance_settings(self):
        """Test pipeline has performance measurement enabled."""
        config_file = Path(__file__).parent.parent / "jetson/deepstream/emotion_pipeline.txt"
        
        config = configparser.ConfigParser()
        config.read(config_file)
        
        assert config.has_option('application', 'enable-perf-measurement')
        assert config.get('application', 'enable-perf-measurement') == '1'
    
    def test_streammux_config(self):
        """Test streammux configuration."""
        config_file = Path(__file__).parent.parent / "jetson/deepstream/emotion_pipeline.txt"
        
        config = configparser.ConfigParser()
        config.read(config_file)
        
        # Check batch size
        assert config.has_option('streammux', 'batch-size')
        batch_size = int(config.get('streammux', 'batch-size'))
        assert batch_size == 1, "Batch size should be 1 for real-time"
        
        # Check dimensions
        assert config.has_option('streammux', 'width')
        assert config.has_option('streammux', 'height')
        width = int(config.get('streammux', 'width'))
        height = int(config.get('streammux', 'height'))
        assert width == 224
        assert height == 224
    
    def test_primary_gie_config(self):
        """Test primary GIE configuration."""
        config_file = Path(__file__).parent.parent / "jetson/deepstream/emotion_pipeline.txt"
        
        config = configparser.ConfigParser()
        config.read(config_file)
        
        # Check engine file is specified
        assert config.has_option('primary-gie', 'model-engine-file')
        engine_file = config.get('primary-gie', 'model-engine-file')
        assert 'emotionnet' in engine_file.lower()
        
        # Check config file reference
        assert config.has_option('primary-gie', 'config-file')
        assert config.get('primary-gie', 'config-file') == 'emotion_inference.txt'
    
    def test_inference_config_structure(self):
        """Test inference config has required settings."""
        config_file = Path(__file__).parent.parent / "jetson/deepstream/emotion_inference.txt"
        
        config = configparser.ConfigParser()
        config.read(config_file)
        
        # Check property section
        assert 'property' in config.sections()
        
        # Check model engine
        assert config.has_option('property', 'model-engine-file')
        
        # Check batch size
        assert config.has_option('property', 'batch-size')
        batch_size = int(config.get('property', 'batch-size'))
        assert batch_size == 1
    
    def test_inference_precision_mode(self):
        """Test inference uses FP16 precision."""
        config_file = Path(__file__).parent.parent / "jetson/deepstream/emotion_inference.txt"
        
        config = configparser.ConfigParser()
        config.read(config_file)
        
        # Check network mode (2 = FP16)
        assert config.has_option('property', 'network-mode')
        network_mode = int(config.get('property', 'network-mode'))
        assert network_mode == 2, "Should use FP16 mode"
    
    def test_inference_input_dimensions(self):
        """Test inference input dimensions."""
        config_file = Path(__file__).parent.parent / "jetson/deepstream/emotion_inference.txt"
        
        config = configparser.ConfigParser()
        config.read(config_file)
        
        # Check infer-dims
        assert config.has_option('property', 'infer-dims')
        infer_dims = config.get('property', 'infer-dims')
        assert '224' in infer_dims, "Should have 224x224 input"
    
    def test_class_attributes(self):
        """Test class-specific attributes."""
        config_file = Path(__file__).parent.parent / "jetson/deepstream/emotion_inference.txt"
        
        config = configparser.ConfigParser()
        config.read(config_file)
        
        # Check class-attrs-all section
        assert 'class-attrs-all' in config.sections()
        
        # Check threshold
        assert config.has_option('class-attrs-all', 'pre-cluster-threshold')
        threshold = float(config.get('class-attrs-all', 'pre-cluster-threshold'))
        assert 0.0 <= threshold <= 1.0


class TestDeepStreamWrapper:
    """Test DeepStream wrapper functionality."""
    
    def test_wrapper_file_exists(self):
        """Test wrapper script exists."""
        wrapper_file = Path(__file__).parent.parent / "jetson/deepstream_wrapper.py"
        assert wrapper_file.exists()
    
    def test_wrapper_is_executable(self):
        """Test wrapper has shebang."""
        wrapper_file = Path(__file__).parent.parent / "jetson/deepstream_wrapper.py"
        
        with open(wrapper_file) as f:
            first_line = f.readline()
        
        assert first_line.startswith('#!'), "Should have shebang"
        assert 'python' in first_line.lower()


class TestConfigConsistency:
    """Test consistency between config files."""
    
    def test_engine_file_consistency(self):
        """Test engine file references are consistent."""
        pipeline_config = Path(__file__).parent.parent / "jetson/deepstream/emotion_pipeline.txt"
        inference_config = Path(__file__).parent.parent / "jetson/deepstream/emotion_inference.txt"
        
        pipeline_cfg = configparser.ConfigParser()
        pipeline_cfg.read(pipeline_config)
        
        inference_cfg = configparser.ConfigParser()
        inference_cfg.read(inference_config)
        
        # Both should reference emotionnet engine
        pipeline_engine = pipeline_cfg.get('primary-gie', 'model-engine-file')
        inference_engine = inference_cfg.get('property', 'model-engine-file')
        
        assert 'emotionnet' in pipeline_engine.lower()
        assert 'emotionnet' in inference_engine.lower()
    
    def test_labels_file_consistency(self):
        """Test labels file references are consistent."""
        pipeline_config = Path(__file__).parent.parent / "jetson/deepstream/emotion_pipeline.txt"
        inference_config = Path(__file__).parent.parent / "jetson/deepstream/emotion_inference.txt"
        
        pipeline_cfg = configparser.ConfigParser()
        pipeline_cfg.read(pipeline_config)
        
        inference_cfg = configparser.ConfigParser()
        inference_cfg.read(inference_config)
        
        # Both should reference same labels file
        pipeline_labels = pipeline_cfg.get('primary-gie', 'labelfile-path')
        inference_labels = inference_cfg.get('property', 'labelfile-path')
        
        assert pipeline_labels == inference_labels
        assert pipeline_labels == 'emotion_labels.txt'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
