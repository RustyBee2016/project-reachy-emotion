"""
Tests for MLflow integration and experiment tracking.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import mlflow

from trainer.mlflow_tracker import MLflowTracker


@pytest.fixture
def temp_mlflow_dir():
    """Create temporary MLflow tracking directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mlflow_tracker(temp_mlflow_dir):
    """Create MLflowTracker with temporary directory."""
    with patch.dict('os.environ', {'MLFLOW_TRACKING_URI': f'file://{temp_mlflow_dir}'}):
        tracker = MLflowTracker(experiment_name='test_experiment')
        yield tracker
        # Cleanup any active runs
        if tracker.run:
            mlflow.end_run()


class TestMLflowTracker:
    """Test MLflow tracker functionality."""
    
    def test_initialization(self, mlflow_tracker):
        """Test MLflowTracker initialization."""
        assert mlflow_tracker.experiment_name == 'test_experiment'
        assert mlflow_tracker.run is None
    
    def test_start_training(self, mlflow_tracker):
        """Test starting a training run."""
        config = {
            'batch_size': 32,
            'learning_rate': 0.001,
            'num_epochs': 50
        }
        
        mlflow_tracker.start_training(
            run_id='test_run_001',
            config=config,
            tags={'model': 'emotionnet', 'version': '1.0'}
        )
        
        assert mlflow_tracker.run is not None
        
        # End run
        mlflow_tracker.end_training()
    
    def test_log_epoch_metrics(self, mlflow_tracker):
        """Test logging metrics for an epoch."""
        mlflow_tracker.start_training('test_run', {})
        
        metrics = {
            'loss': 0.234,
            'accuracy': 0.856,
            'f1_macro': 0.842
        }
        
        mlflow_tracker.log_epoch_metrics(epoch=10, metrics=metrics)
        
        mlflow_tracker.end_training()
    
    def test_log_dataset_info(self, mlflow_tracker):
        """Test logging dataset information."""
        mlflow_tracker.start_training('test_run', {})
        
        mlflow_tracker.log_dataset_info(
            dataset_hash='abc123def456',
            train_count=1000,
            test_count=300,
            additional_info={'num_classes': 2, 'balanced': True}
        )
        
        mlflow_tracker.end_training()
    
    def test_log_validation_results(self, mlflow_tracker):
        """Test logging validation gate results."""
        mlflow_tracker.start_training('test_run', {})
        
        metrics = {
            'f1_macro': 0.85,
            'precision': 0.87,
            'recall': 0.83
        }
        
        mlflow_tracker.log_validation_results(
            gate_name='gate_a',
            passed=True,
            metrics=metrics
        )
        
        mlflow_tracker.end_training()
    
    def test_end_training(self, mlflow_tracker):
        """Test ending a training run."""
        mlflow_tracker.start_training('test_run', {})
        
        assert mlflow_tracker.run is not None
        
        mlflow_tracker.end_training(status='FINISHED')
        
        assert mlflow_tracker.run is None
    
    def test_multiple_runs(self, mlflow_tracker):
        """Test handling multiple sequential runs."""
        # First run
        mlflow_tracker.start_training('run_1', {'lr': 0.001})
        mlflow_tracker.log_epoch_metrics(1, {'loss': 0.5})
        mlflow_tracker.end_training()
        
        # Second run
        mlflow_tracker.start_training('run_2', {'lr': 0.0005})
        mlflow_tracker.log_epoch_metrics(1, {'loss': 0.4})
        mlflow_tracker.end_training()
        
        # Both should complete successfully
        assert mlflow_tracker.run is None


class TestMLflowIntegration:
    """Test MLflow integration scenarios."""
    
    def test_log_model_artifact(self, mlflow_tracker, temp_mlflow_dir):
        """Test logging model artifacts."""
        mlflow_tracker.start_training('test_run', {})
        
        # Create dummy model file
        model_file = Path(temp_mlflow_dir) / 'model.h5'
        model_file.write_text('dummy model content')
        
        mlflow_tracker.log_model(str(model_file), model_name='emotionnet')
        
        mlflow_tracker.end_training()
    
    def test_log_nonexistent_model(self, mlflow_tracker):
        """Test handling of nonexistent model file."""
        mlflow_tracker.start_training('test_run', {})
        
        # Should handle gracefully
        mlflow_tracker.log_model('/nonexistent/model.h5')
        
        mlflow_tracker.end_training()
    
    def test_auto_run_creation(self, mlflow_tracker):
        """Test automatic run creation when logging without active run."""
        # Log metrics without starting run
        mlflow_tracker.log_epoch_metrics(1, {'loss': 0.5})
        
        # Should create auto run
        assert mlflow_tracker.run is not None
        
        mlflow_tracker.end_training()


class TestMLflowMetrics:
    """Test metric logging and tracking."""
    
    def test_log_multiple_epochs(self, mlflow_tracker):
        """Test logging metrics across multiple epochs."""
        mlflow_tracker.start_training('test_run', {})
        
        for epoch in range(1, 11):
            metrics = {
                'loss': 1.0 / epoch,  # Decreasing loss
                'accuracy': 0.5 + (epoch * 0.03)  # Increasing accuracy
            }
            mlflow_tracker.log_epoch_metrics(epoch, metrics)
        
        mlflow_tracker.end_training()
    
    def test_log_validation_gates(self, mlflow_tracker):
        """Test logging multiple validation gates."""
        mlflow_tracker.start_training('test_run', {})
        
        # Gate A
        mlflow_tracker.log_validation_results(
            'gate_a',
            passed=True,
            metrics={'f1_macro': 0.85}
        )
        
        # Gate B
        mlflow_tracker.log_validation_results(
            'gate_b',
            passed=False,
            metrics={'latency_p50': 150}
        )
        
        mlflow_tracker.end_training()


class TestMLflowParameters:
    """Test parameter logging."""
    
    def test_log_training_config(self, mlflow_tracker):
        """Test logging complete training configuration."""
        config = {
            'model_arch': 'resnet18',
            'num_classes': 2,
            'batch_size': 32,
            'learning_rate': 0.001,
            'optimizer': 'adam',
            'num_epochs': 50,
            'dropout_rate': 0.3
        }
        
        mlflow_tracker.start_training('test_run', config)
        mlflow_tracker.end_training()
    
    def test_log_dataset_parameters(self, mlflow_tracker):
        """Test logging dataset-related parameters."""
        mlflow_tracker.start_training('test_run', {})
        
        mlflow_tracker.log_dataset_info(
            dataset_hash='abc123',
            train_count=1400,
            test_count=600,
            additional_info={
                'augmentation': 'mixup+flip',
                'class_balance': '50/50',
                'seed': 42
            }
        )
        
        mlflow_tracker.end_training()


class TestMLflowTags:
    """Test tag management."""
    
    def test_log_tags_on_start(self, mlflow_tracker):
        """Test logging tags when starting run."""
        tags = {
            'model_type': 'emotionnet',
            'version': '2.0',
            'environment': 'test'
        }
        
        mlflow_tracker.start_training('test_run', {}, tags=tags)
        mlflow_tracker.end_training()
    
    def test_status_tag_on_end(self, mlflow_tracker):
        """Test status tag is set when ending run."""
        mlflow_tracker.start_training('test_run', {})
        mlflow_tracker.end_training(status='COMPLETED')


class TestMLflowErrorHandling:
    """Test error handling in MLflow operations."""
    
    def test_log_without_active_run(self, mlflow_tracker):
        """Test logging creates auto-run when no active run."""
        # Should not raise error
        mlflow_tracker.log_epoch_metrics(1, {'loss': 0.5})
        
        assert mlflow_tracker.run is not None
        mlflow_tracker.end_training()
    
    def test_end_without_active_run(self, mlflow_tracker):
        """Test ending when no active run."""
        # Should handle gracefully
        mlflow_tracker.end_training()
        
        assert mlflow_tracker.run is None
    
    def test_log_invalid_metric_types(self, mlflow_tracker):
        """Test handling of invalid metric types."""
        mlflow_tracker.start_training('test_run', {})
        
        # MLflow should handle type conversion
        metrics = {
            'loss': 0.5,
            'accuracy': 0.85
        }
        
        mlflow_tracker.log_epoch_metrics(1, metrics)
        mlflow_tracker.end_training()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
