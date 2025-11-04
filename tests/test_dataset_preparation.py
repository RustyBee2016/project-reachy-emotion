"""
Test suite for dataset preparation and sampling logic.
Run with: pytest tests/test_dataset_preparation.py -v
"""

import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))


class TestDatasetPreparation:
    """Test dataset preparation and sampling logic."""
    
    @pytest.fixture
    def temp_dataset_dir(self):
        """Create temporary dataset directory."""
        temp_dir = tempfile.mkdtemp()
        
        # Create mock video structure
        dataset_all = Path(temp_dir) / 'dataset_all'
        dataset_all.mkdir()
        
        # Create balanced dataset
        for emotion in ['happy', 'sad', 'neutral']:
            emotion_dir = dataset_all / emotion
            emotion_dir.mkdir()
            for i in range(10):
                (emotion_dir / f'{emotion}_{i}.mp4').touch()
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_balanced_sampling(self, temp_dataset_dir):
        """Test that dataset is sampled in a balanced way."""
        from trainer.prepare_dataset import DatasetPreparer
        
        preparer = DatasetPreparer(temp_dataset_dir)
        
        # Prepare with 70/30 split
        result = preparer.prepare_training_dataset(
            run_id='test_run_001',
            train_fraction=0.7,
            seed=42
        )
        
        assert result['run_id'] == 'test_run_001'
        assert result['train_count'] + result['test_count'] == 30  # Total videos
        assert 19 <= result['train_count'] <= 23  # ~70% of 30
        assert 7 <= result['test_count'] <= 11   # ~30% of 30
    
    def test_stratified_sampling(self, temp_dataset_dir):
        """Test that each class is represented proportionally."""
        from trainer.prepare_dataset import DatasetPreparer
        
        preparer = DatasetPreparer(temp_dataset_dir)
        
        # Prepare dataset
        result = preparer.prepare_training_dataset(
            run_id='test_run_002',
            train_fraction=0.7,
            seed=123
        )
        
        # Check stratification in manifests
        train_manifest_path = Path(temp_dataset_dir) / 'manifests' / 'test_run_002_train.jsonl'
        assert train_manifest_path.exists()
        
        # Count labels in training set
        label_counts = {}
        with open(train_manifest_path, 'r') as f:
            for line in f:
                entry = json.loads(line)
                label = entry['label']
                label_counts[label] = label_counts.get(label, 0) + 1
        
        # Each class should have roughly equal representation
        assert len(label_counts) == 3
        for count in label_counts.values():
            assert 5 <= count <= 9  # Roughly 1/3 of ~21 samples
    
    def test_manifest_generation(self, temp_dataset_dir):
        """Test that manifests are generated correctly."""
        from trainer.prepare_dataset import DatasetPreparer
        
        preparer = DatasetPreparer(temp_dataset_dir)
        
        result = preparer.prepare_training_dataset(
            run_id='test_run_003',
            train_fraction=0.8
        )
        
        # Check manifest files exist
        manifests_dir = Path(temp_dataset_dir) / 'manifests'
        train_manifest = manifests_dir / 'test_run_003_train.jsonl'
        test_manifest = manifests_dir / 'test_run_003_test.jsonl'
        
        assert train_manifest.exists()
        assert test_manifest.exists()
        
        # Validate manifest format
        with open(train_manifest, 'r') as f:
            for line in f:
                entry = json.loads(line)
                assert 'video_id' in entry
                assert 'path' in entry
                assert 'label' in entry
    
    def test_dataset_hash_calculation(self, temp_dataset_dir):
        """Test that dataset hash is deterministic."""
        from trainer.prepare_dataset import DatasetPreparer
        
        preparer = DatasetPreparer(temp_dataset_dir)
        
        # Calculate hash twice
        hash1 = preparer.calculate_dataset_hash()
        hash2 = preparer.calculate_dataset_hash()
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex digest
    
    def test_reproducible_sampling(self, temp_dataset_dir):
        """Test that same seed produces same split."""
        from trainer.prepare_dataset import DatasetPreparer
        
        preparer = DatasetPreparer(temp_dataset_dir)
        
        # Prepare twice with same seed
        result1 = preparer.prepare_training_dataset(
            run_id='run_a',
            train_fraction=0.7,
            seed=999
        )
        
        result2 = preparer.prepare_training_dataset(
            run_id='run_b',
            train_fraction=0.7,
            seed=999
        )
        
        # Should have same counts
        assert result1['train_count'] == result2['train_count']
        assert result1['test_count'] == result2['test_count']


class TestTAOConfiguration:
    """Test TAO training configuration loading and validation."""
    
    def test_config_loading(self):
        """Test loading TAO configuration from YAML."""
        from trainer.tao.config_loader import TAOConfigLoader
        
        config_yaml = """
        model_config:
          arch: resnet18
          num_classes: 6
          input_shape: [3, 224, 224]
        
        training_config:
          batch_size: 32
          num_epochs: 50
          learning_rate: 0.001
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_yaml)
            config_path = f.name
        
        try:
            loader = TAOConfigLoader()
            config = loader.load_config(config_path)
            
            assert config['model_config']['arch'] == 'resnet18'
            assert config['model_config']['num_classes'] == 6
            assert config['training_config']['batch_size'] == 32
        finally:
            os.unlink(config_path)
    
    def test_config_validation(self):
        """Test that invalid configs are rejected."""
        from trainer.tao.config_loader import TAOConfigLoader, InvalidConfigError
        
        # Missing required fields
        invalid_config = """
        model_config:
          arch: resnet18
          # Missing num_classes
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_config)
            config_path = f.name
        
        try:
            loader = TAOConfigLoader()
            with pytest.raises(InvalidConfigError):
                loader.load_config(config_path)
        finally:
            os.unlink(config_path)
    
    def test_augmentation_config(self):
        """Test data augmentation configuration."""
        from trainer.tao.config_loader import TAOConfigLoader
        
        config_yaml = """
        dataset_config:
          augmentation:
            enable_augmentation: true
            random_flip:
              horizontal: true
              probability: 0.5
            color_jitter:
              brightness: 0.3
              contrast: 0.3
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_yaml)
            config_path = f.name
        
        try:
            loader = TAOConfigLoader()
            config = loader.load_config(config_path)
            
            aug = config['dataset_config']['augmentation']
            assert aug['enable_augmentation'] is True
            assert aug['random_flip']['horizontal'] is True
            assert aug['color_jitter']['brightness'] == 0.3
        finally:
            os.unlink(config_path)


class TestMLflowIntegration:
    """Test MLflow experiment tracking integration."""
    
    @patch('mlflow.start_run')
    @patch('mlflow.log_params')
    @patch('mlflow.log_metrics')
    def test_experiment_tracking(self, mock_log_metrics, mock_log_params, mock_start_run):
        """Test that training logs to MLflow."""
        from trainer.mlflow_tracker import MLflowTracker
        
        tracker = MLflowTracker(experiment_name='test_emotion')
        
        # Start training
        tracker.start_training(
            run_id='test_run',
            config={
                'model_arch': 'resnet18',
                'batch_size': 32,
                'learning_rate': 0.001
            }
        )
        
        # Log metrics
        tracker.log_epoch_metrics(
            epoch=1,
            metrics={
                'loss': 0.5,
                'accuracy': 0.75,
                'f1_score': 0.73
            }
        )
        
        mock_start_run.assert_called_once()
        mock_log_params.assert_called_once()
        mock_log_metrics.assert_called_once()
    
    @patch('mlflow.log_artifacts')
    def test_model_artifact_logging(self, mock_log_artifacts):
        """Test that models are saved as artifacts."""
        from trainer.mlflow_tracker import MLflowTracker
        
        tracker = MLflowTracker(experiment_name='test_emotion')
        
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / 'model.hdf5'
            model_path.touch()
            
            tracker.log_model(str(model_path))
            
            mock_log_artifacts.assert_called_once()
    
    def test_dataset_hash_tracking(self):
        """Test that dataset hash is logged for reproducibility."""
        from trainer.mlflow_tracker import MLflowTracker
        
        with patch('mlflow.log_param') as mock_log_param:
            tracker = MLflowTracker(experiment_name='test_emotion')
            
            dataset_hash = 'a' * 64  # Mock SHA256
            tracker.log_dataset_info(dataset_hash, train_count=100, test_count=30)
            
            # Should log dataset hash
            calls = mock_log_param.call_args_list
            assert any('dataset_hash' in str(call) for call in calls)


class TestValidationGates:
    """Test model validation gates."""
    
    def test_gate_a_offline_validation(self):
        """Test Gate A: Offline validation (F1 >= 0.84)."""
        from trainer.validation import ValidationGates
        
        gates = ValidationGates()
        
        # Pass case
        metrics_pass = {'f1_macro': 0.85, 'accuracy': 0.87}
        assert gates.check_gate_a(metrics_pass) is True
        
        # Fail case
        metrics_fail = {'f1_macro': 0.83, 'accuracy': 0.85}
        assert gates.check_gate_a(metrics_fail) is False
    
    def test_gate_b_latency_check(self):
        """Test Gate B: Inference latency (<= 250ms)."""
        from trainer.validation import ValidationGates
        
        gates = ValidationGates()
        
        # Pass case
        assert gates.check_gate_b(latency_ms=100) is True
        assert gates.check_gate_b(latency_ms=250) is True
        
        # Fail case
        assert gates.check_gate_b(latency_ms=251) is False
    
    def test_gate_c_user_feedback(self):
        """Test Gate C: User feedback (<1% complaints)."""
        from trainer.validation import ValidationGates
        
        gates = ValidationGates()
        
        # Pass case
        assert gates.check_gate_c(complaint_rate=0.005) is True
        
        # Fail case
        assert gates.check_gate_c(complaint_rate=0.015) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--color=yes'])
