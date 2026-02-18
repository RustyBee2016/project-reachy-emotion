"""
Tests for training orchestrator and TensorRT export pipeline.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

import cv2
import numpy as np

from trainer.train_emotionnet import TrainingOrchestrator
from trainer.export_to_trt import TensorRTExporter


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    temp_base = tempfile.mkdtemp()
    base_path = Path(temp_base)
    
    # Create directory structure
    dataset_dir = base_path / 'dataset'
    train_root = dataset_dir / 'train'
    train_root.mkdir(parents=True)
    
    # Create sample videos (3-class: happy, sad, neutral)
    for emotion in ['happy', 'sad', 'neutral']:
        emotion_dir = train_root / emotion
        emotion_dir.mkdir()
        for i in range(5):
            _write_test_video(emotion_dir / f'{emotion}_{i}.mp4')
    
    output_dir = base_path / 'output'
    output_dir.mkdir()
    
    # Create sample config
    config_file = base_path / 'config.yaml'
    config_file.write_text("""
model:
  arch: resnet18
  num_classes: 3
  model_name: emotionnet_test
dataset:
  classes: [happy, sad, neutral]
training:
  batch_size: 32
  num_epochs: 50
  learning_rate: 0.001
  optimizer: adam
gates:
  gate_a:
    min_f1_macro: 0.84
""")
    
    yield {
        'base': base_path,
        'dataset': dataset_dir,
        'output': output_dir,
        'config': config_file
    }
    
    # Cleanup
    shutil.rmtree(temp_base)


class TestTrainingOrchestrator:
    """Test training orchestrator functionality."""
    
    def test_initialization(self, temp_dirs):
        """Test orchestrator initialization."""
        orchestrator = TrainingOrchestrator(
            config_path=str(temp_dirs['config']),
            dataset_path=str(temp_dirs['dataset']),
            output_path=str(temp_dirs['output'])
        )
        
        assert orchestrator.config_path == temp_dirs['config']
        assert orchestrator.dataset_path == temp_dirs['dataset']
        assert orchestrator.output_path == temp_dirs['output']
        assert orchestrator.config is not None
    
    def test_prepare_dataset(self, temp_dirs):
        """Test dataset preparation."""
        orchestrator = TrainingOrchestrator(
            config_path=str(temp_dirs['config']),
            dataset_path=str(temp_dirs['dataset']),
            output_path=str(temp_dirs['output'])
        )
        
        dataset_info = orchestrator.prepare_dataset(
            run_id='epoch_01',
            train_fraction=0.7,
            seed=42
        )
        
        assert 'train_count' in dataset_info
        assert 'test_count' in dataset_info
        assert 'dataset_hash' in dataset_info
        assert dataset_info['train_count'] == 150
        assert dataset_info['test_count'] == 0
    
    def test_parse_training_output(self, temp_dirs):
        """Test parsing TAO training output."""
        orchestrator = TrainingOrchestrator(
            config_path=str(temp_dirs['config']),
            dataset_path=str(temp_dirs['dataset']),
            output_path=str(temp_dirs['output'])
        )
        
        # Sample TAO output
        output = """
Epoch 1/50 - loss: 0.693 - accuracy: 0.520 - f1: 0.510
Epoch 25/50 - loss: 0.234 - accuracy: 0.856 - f1: 0.842
Epoch 50/50 - loss: 0.123 - accuracy: 0.912 - f1: 0.905
Training completed successfully
"""
        
        metrics = orchestrator._parse_training_output(output)
        
        assert metrics['epochs_completed'] == 50
        assert metrics['final_loss'] == 0.123
        assert metrics['final_accuracy'] == 0.912
        assert metrics['final_f1'] == 0.905
    
    def test_validate_gates_pass(self, temp_dirs):
        """Test validation gates passing."""
        orchestrator = TrainingOrchestrator(
            config_path=str(temp_dirs['config']),
            dataset_path=str(temp_dirs['dataset']),
            output_path=str(temp_dirs['output'])
        )
        
        # Mock MLflow tracker
        orchestrator.mlflow_tracker = Mock()
        
        metrics = {
            'final_f1': 0.85,
            'final_accuracy': 0.87
        }
        
        gate_results = orchestrator.validate_gates('test_run', metrics)
        
        assert 'gate_a' in gate_results
        assert gate_results['gate_a'] is True
    
    def test_validate_gates_fail(self, temp_dirs):
        """Test validation gates failing."""
        orchestrator = TrainingOrchestrator(
            config_path=str(temp_dirs['config']),
            dataset_path=str(temp_dirs['dataset']),
            output_path=str(temp_dirs['output'])
        )
        
        orchestrator.mlflow_tracker = Mock()
        
        metrics = {
            'final_f1': 0.75,  # Below threshold of 0.84
            'final_accuracy': 0.80
        }
        
        gate_results = orchestrator.validate_gates('test_run', metrics)
        
        assert 'gate_a' in gate_results
        assert gate_results['gate_a'] is False


class TestTensorRTExporter:
    """Test TensorRT export functionality."""
    
    def test_initialization(self, temp_dirs):
        """Test exporter initialization."""
        model_path = temp_dirs['output'] / 'model.hdf5'
        model_path.write_text('dummy model')
        
        exporter = TensorRTExporter(
            model_path=str(model_path),
            output_dir=str(temp_dirs['output'] / 'engines')
        )
        
        assert exporter.model_path == model_path
        assert exporter.output_dir.exists()
    
    def test_parse_trtexec_output(self, temp_dirs):
        """Test parsing trtexec performance output."""
        model_path = temp_dirs['output'] / 'model.hdf5'
        model_path.write_text('dummy')
        
        exporter = TensorRTExporter(
            model_path=str(model_path),
            output_dir=str(temp_dirs['output'])
        )
        
        # Sample trtexec output
        output = """
[I] GPU Compute
[I] min: 42.1 ms
[I] max: 48.3 ms
[I] mean: 45.2 ms
[I] median: 44.8 ms
[I] percentile(50%): 44.8 ms
[I] percentile(95%): 47.1 ms
[I] percentile(99%): 47.9 ms
[I] throughput: 22.1 qps
"""
        
        metrics = exporter._parse_trtexec_output(output)
        
        assert metrics['latency_mean_ms'] == 45.2
        assert metrics['latency_p50_ms'] == 44.8
        assert metrics['latency_p95_ms'] == 47.1
        assert metrics['latency_p99_ms'] == 47.9
        assert metrics['throughput_qps'] == 22.1
    
    @patch('subprocess.run')
    def test_export_fp16_success(self, mock_run, temp_dirs):
        """Test successful FP16 export."""
        model_path = temp_dirs['output'] / 'model.hdf5'
        model_path.write_text('dummy')
        
        exporter = TensorRTExporter(
            model_path=str(model_path),
            output_dir=str(temp_dirs['output'] / 'engines')
        )
        
        # Mock successful export
        mock_run.return_value = Mock(returncode=0, stdout='Export successful', stderr='')
        
        # Create dummy engine file
        engine_path = exporter.output_dir / 'test_model_fp16.engine'
        engine_path.write_text('dummy engine')
        
        result = exporter.export_fp16('test_model', batch_size=1)
        
        assert result['success'] is True
        assert result['precision'] == 'fp16'
        assert result['batch_size'] == 1
        assert 'size_mb' in result
    
    @patch('subprocess.run')
    def test_export_fp16_failure(self, mock_run, temp_dirs):
        """Test failed FP16 export."""
        model_path = temp_dirs['output'] / 'model.hdf5'
        model_path.write_text('dummy')
        
        exporter = TensorRTExporter(
            model_path=str(model_path),
            output_dir=str(temp_dirs['output'] / 'engines')
        )
        
        # Mock failed export
        mock_run.return_value = Mock(returncode=1, stdout='', stderr='Export failed')
        
        result = exporter.export_fp16('test_model', batch_size=1)
        
        assert result['success'] is False
        assert 'error' in result
    
    @patch('subprocess.run')
    def test_verify_engine_success(self, mock_run, temp_dirs):
        """Test successful engine verification."""
        model_path = temp_dirs['output'] / 'model.hdf5'
        model_path.write_text('dummy')
        
        exporter = TensorRTExporter(
            model_path=str(model_path),
            output_dir=str(temp_dirs['output'] / 'engines')
        )
        
        # Create dummy engine
        engine_path = exporter.output_dir / 'test.engine'
        engine_path.write_text('dummy engine')
        
        # Mock successful verification
        mock_run.return_value = Mock(
            returncode=0,
            stdout='mean = 45.2 ms\npercentile(95%): 47.1 ms',
            stderr=''
        )
        
        result = exporter.verify_engine(str(engine_path))
        
        assert result['success'] is True
        assert 'metrics' in result


class TestTrainingPipeline:
    """Test complete training pipeline integration."""
    
    @patch('subprocess.run')
    def test_pipeline_with_mocked_training(self, mock_run, temp_dirs):
        """Test pipeline with mocked TAO training."""
        orchestrator = TrainingOrchestrator(
            config_path=str(temp_dirs['config']),
            dataset_path=str(temp_dirs['dataset']),
            output_path=str(temp_dirs['output'])
        )
        
        # Mock successful training
        training_output = """
Epoch 50/50 - loss: 0.123 - accuracy: 0.912 - f1: 0.905
Training completed
"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=training_output,
            stderr=''
        )
        
        # Mock MLflow
        orchestrator.mlflow_tracker = Mock()
        
        # Run pipeline (will skip actual training due to mock)
        results = orchestrator.run_training_pipeline(
            run_id='epoch_01',
            train_fraction=0.7,
            seed=42
        )
        
        assert 'run_id' in results
        assert 'status' in results
        assert 'dataset' in results


class TestExportPipeline:
    """Test complete export pipeline."""
    
    @patch('subprocess.run')
    def test_export_pipeline_fp16(self, mock_run, temp_dirs):
        """Test FP16 export pipeline."""
        model_path = temp_dirs['output'] / 'model.hdf5'
        model_path.write_text('dummy')
        
        exporter = TensorRTExporter(
            model_path=str(model_path),
            output_dir=str(temp_dirs['output'] / 'engines')
        )
        
        # Mock export and verification
        def mock_subprocess(cmd, **kwargs):
            if 'export' in cmd:
                # Create dummy engine
                engine_path = exporter.output_dir / 'test_fp16.engine'
                engine_path.write_text('dummy engine')
                return Mock(returncode=0, stdout='Export successful', stderr='')
            elif 'trtexec' in cmd:
                return Mock(
                    returncode=0,
                    stdout='mean = 45.2 ms\npercentile(95%): 47.1 ms',
                    stderr=''
                )
            return Mock(returncode=0, stdout='', stderr='')
        
        mock_run.side_effect = mock_subprocess
        
        results = exporter.export_pipeline(
            engine_name='test',
            precision='fp16',
            batch_size=1,
            verify=True
        )
        
        assert 'status' in results
        assert 'export' in results
        assert 'verification' in results


class TestErrorHandling:
    """Test error handling in pipelines."""
    
    def test_invalid_config_path(self, temp_dirs):
        """Test handling of invalid config path."""
        with pytest.raises(Exception):
            TrainingOrchestrator(
                config_path='/nonexistent/config.yaml',
                dataset_path=str(temp_dirs['dataset']),
                output_path=str(temp_dirs['output'])
            )
    
    def test_missing_model_file(self, temp_dirs):
        """Test handling of missing model file."""
        exporter = TensorRTExporter(
            model_path='/nonexistent/model.hdf5',
            output_dir=str(temp_dirs['output'])
        )
        
        # Should initialize but model doesn't exist
        assert not exporter.model_path.exists()
    
    @patch('subprocess.run')
    def test_training_timeout(self, mock_run, temp_dirs):
        """Test handling of training timeout."""
        orchestrator = TrainingOrchestrator(
            config_path=str(temp_dirs['config']),
            dataset_path=str(temp_dirs['dataset']),
            output_path=str(temp_dirs['output'])
        )
        
        # Mock timeout
        mock_run.side_effect = subprocess.TimeoutExpired('tao', 7200)
        
        success, metrics = orchestrator.train_model('test_run')
        
        assert success is False
        assert 'error' in metrics


def _write_test_video(path: Path, frame_count: int = 20) -> None:
    """Create a tiny synthetic MP4 video for frame extraction tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10.0,
        (32, 32),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Unable to create test video: {path}")
    for idx in range(frame_count):
        frame = np.full((32, 32, 3), idx % 255, dtype=np.uint8)
        writer.write(frame)
    writer.release()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
