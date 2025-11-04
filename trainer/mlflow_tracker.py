"""
MLflow experiment tracking integration for TAO training.
"""

import os
import mlflow
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MLflowTracker:
    """Track experiments and models with MLflow."""
    
    def __init__(self, experiment_name: str = 'emotion_classification'):
        """
        Initialize MLflow tracker.
        
        Args:
            experiment_name: Name of MLflow experiment
        """
        self.experiment_name = experiment_name
        self.run = None
        
        # Set tracking URI from environment or use default
        tracking_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
        mlflow.set_tracking_uri(tracking_uri)
        
        # Create or set experiment
        mlflow.set_experiment(experiment_name)
        logger.info(f"MLflow tracking initialized for experiment: {experiment_name}")

    def _ensure_run(self, run_name: str = 'auto_run'):
        """Ensure there is an active MLflow run."""
        active = mlflow.active_run()
        if active:
            self.run = active
            return

        logger.info("No active MLflow run detected. Starting an auto-run.")
        self.run = mlflow.start_run(run_name=run_name)
    
    def start_training(
        self,
        run_id: str,
        config: Dict[str, Any],
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Start a new MLflow training run.
        
        Args:
            run_id: Unique identifier for this run
            config: Training configuration parameters
            tags: Optional tags for the run
        """
        # End any existing run
        if self.run:
            mlflow.end_run()
        
        # Start new run
        self.run = mlflow.start_run(run_name=run_id)
        
        # Log parameters
        mlflow.log_params(config)
        
        # Log tags
        if tags:
            mlflow.set_tags(tags)
        
        logger.info(f"Started MLflow run: {run_id}")
    
    def log_epoch_metrics(
        self,
        epoch: int,
        metrics: Dict[str, float]
    ):
        """
        Log metrics for a training epoch.
        
        Args:
            epoch: Epoch number
            metrics: Dictionary of metric names and values
        """
        if not self.run:
            logger.warning("No active MLflow run. Starting one...")
            self.start_training('auto_run', {})
        
        # Log metrics with step
        mlflow.log_metrics(metrics, step=epoch)
        
        logger.info(f"Logged metrics for epoch {epoch}: {metrics}")
    
    def log_model(
        self,
        model_path: str,
        model_name: Optional[str] = None
    ):
        """
        Log model artifact to MLflow.
        
        Args:
            model_path: Path to model file
            model_name: Optional name for the model
        """
        if not self.run:
            self._ensure_run(run_name='auto_model_logging')
        
        model_file = Path(model_path)
        
        if not model_file.exists():
            logger.error(f"Model file not found: {model_file}")
            return
        
        # Log model as artifact
        if model_file.is_file():
            mlflow.log_artifact(str(model_file), artifact_path=model_name or "models")
        else:
            mlflow.log_artifacts(str(model_file), artifact_path=model_name or "models")
        
        logger.info(f"Logged model: {model_path}")
    
    def log_dataset_info(
        self,
        dataset_hash: str,
        train_count: int,
        test_count: int,
        additional_info: Optional[Dict[str, Any]] = None
    ):
        """
        Log dataset information for reproducibility.
        
        Args:
            dataset_hash: SHA256 hash of dataset
            train_count: Number of training samples
            test_count: Number of test samples
            additional_info: Additional dataset metadata
        """
        if not self.run:
            self._ensure_run(run_name='auto_dataset_logging')
        
        # Log as parameters
        mlflow.log_param('dataset_hash', dataset_hash)
        mlflow.log_param('train_count', train_count)
        mlflow.log_param('test_count', test_count)
        
        if additional_info:
            for key, value in additional_info.items():
                mlflow.log_param(f'dataset_{key}', value)
        
        logger.info(f"Logged dataset info: hash={dataset_hash[:8]}..., train={train_count}, test={test_count}")
    
    def log_validation_results(
        self,
        gate_name: str,
        passed: bool,
        metrics: Dict[str, Any]
    ):
        """
        Log validation gate results.
        
        Args:
            gate_name: Name of validation gate
            passed: Whether gate passed
            metrics: Gate metrics
        """
        if not self.run:
            return
        
        # Log as metrics
        mlflow.log_metric(f'{gate_name}_passed', 1.0 if passed else 0.0)
        
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                mlflow.log_metric(f'{gate_name}_{key}', value)
        
        logger.info(f"Validation gate {gate_name}: {'PASSED' if passed else 'FAILED'}")
    
    def end_training(
        self,
        status: str = 'FINISHED'
    ):
        """
        End the current MLflow run.
        
        Args:
            status: Final status of the run
        """
        if self.run:
            mlflow.set_tag('status', status)
            mlflow.end_run()
            self.run = None
            logger.info(f"Ended MLflow run with status: {status}")
