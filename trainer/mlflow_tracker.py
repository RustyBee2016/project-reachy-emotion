"""
MLflow experiment tracking integration for EfficientNet-B0 training.

This module provides a wrapper class (MLflowTracker) for logging training
experiments, metrics, hyperparameters, and model artifacts to MLflow.
MLflow enables reproducibility tracking, experiment comparison, and model
versioning across training runs.

Key features:
  - Automatic experiment creation and run management
  - Epoch-level metric logging (loss, accuracy, F1, etc.)
  - Hyperparameter and config logging
  - Dataset hash tracking for reproducibility
  - Model artifact logging (checkpoints, ONNX exports)
  - Gate A validation result tracking

MLflow tracking URI:
  - Default: file:///media/rusty_admin/project_data/reachy_emotion/mlruns
  - Override via MLFLOW_TRACKING_URI environment variable

Used by:
  - EfficientNetTrainer (fer_finetune/train_efficientnet.py)
  - run_efficientnet_pipeline.py for end-to-end tracking
  - Streamlit UI (06_Dashboard.py) for experiment visualization
"""

# ---------------------------------------------------------------------------
# Standard library imports for environment variables, filesystem operations,
# type hints, and logging.
# ---------------------------------------------------------------------------
import os
import mlflow
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# ===========================================================================
# MLflowTracker Class
# ===========================================================================
# This class wraps MLflow's Python API to provide a simplified interface for
# logging training runs.  It handles experiment creation, run lifecycle
# management, and structured logging of metrics, parameters, and artifacts.
#
# All runs are grouped under a single experiment (default: 'emotion_classification').
# Each training run gets a unique run_id that ties together:
#   - MLflow run record
#   - Dataset manifests (run_XXXX_train.jsonl)
#   - Dashboard payloads (dashboard_runs/<variant>/<run_type>/<run_id>.json)
#   - n8n workflow correlation IDs
# ===========================================================================

class MLflowTracker:
    """Track experiments and models with MLflow."""
    
    # -----------------------------------------------------------------------
    # Initialization
    # -----------------------------------------------------------------------
    # Sets up MLflow tracking URI and creates/sets the experiment.
    # The tracking URI defaults to a local filesystem path but can be
    # overridden to point to a remote MLflow server.
    # -----------------------------------------------------------------------
    def __init__(self, experiment_name: str = 'emotion_classification'):
        """
        Initialize MLflow tracker.
        
        Args:
            experiment_name: Name of MLflow experiment
        """
        self.experiment_name = experiment_name
        self.run = None
        
        # Set tracking URI from environment or use default
        tracking_uri = os.getenv('MLFLOW_TRACKING_URI', 'file:///media/rusty_admin/project_data/reachy_emotion/mlruns')
        mlflow.set_tracking_uri(tracking_uri)
        
        # Create or set experiment
        mlflow.set_experiment(experiment_name)
        logger.info(f"MLflow tracking initialized for experiment: {experiment_name}")

    # -----------------------------------------------------------------------
    # Auto-Run Initialization
    # -----------------------------------------------------------------------
    # If no active MLflow run exists, start one automatically.  This is a
    # safety mechanism to prevent errors when log_* methods are called
    # outside of an explicit start_training() context.
    # -----------------------------------------------------------------------
    def _ensure_run(self, run_name: str = 'auto_run'):
        """Ensure there is an active MLflow run."""
        active = mlflow.active_run()
        if active:
            self.run = active
            return

        logger.info("No active MLflow run detected. Starting an auto-run.")
        self.run = mlflow.start_run(run_name=run_name)
    
    # -----------------------------------------------------------------------
    # Training Run Initialization
    # -----------------------------------------------------------------------
    # Starts a new MLflow run and logs all hyperparameters from the config.
    # This should be called at the beginning of each training session.
    # The run_id becomes the MLflow run name for easy correlation.
    # -----------------------------------------------------------------------
    def start_training(
        self,
        run_id: str,
        config: Dict[str, Any],
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Start a new MLflow training run.
        
        Args:
            run_id: Unique identifier for this run (e.g., run_0042)
            config: Training configuration parameters (hyperparameters, paths)
            tags: Optional tags for the run (e.g., {'variant': 'variant_1'})
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
    
    # -----------------------------------------------------------------------
    # Epoch-Level Metric Logging
    # -----------------------------------------------------------------------
    # Logs metrics for a single training epoch.  Metrics are timestamped
    # and associated with the epoch number (step) for visualization in
    # MLflow UI.  Typical metrics: train_loss, val_loss, val_accuracy,
    # val_f1_macro, learning_rate, etc.
    # -----------------------------------------------------------------------
    def log_epoch_metrics(
        self,
        epoch: int,
        metrics: Dict[str, float]
    ):
        """
        Log metrics for a training epoch.
        
        Args:
            epoch: Epoch number (used as MLflow step)
            metrics: Dictionary of metric names and values (e.g., {'val_f1': 0.87})
        """
        if not self.run:
            logger.warning("No active MLflow run. Starting one...")
            self.start_training('auto_run', {})
        
        # Log metrics with step
        mlflow.log_metrics(metrics, step=epoch)
        
        logger.info(f"Logged metrics for epoch {epoch}: {metrics}")
    
    # -----------------------------------------------------------------------
    # Model Artifact Logging
    # -----------------------------------------------------------------------
    # Uploads model checkpoints or ONNX exports to MLflow as artifacts.
    # Artifacts are versioned and tied to the run, enabling model retrieval
    # and comparison across experiments.
    # -----------------------------------------------------------------------
    def log_model(
        self,
        model_path: str,
        model_name: Optional[str] = None
    ):
        """
        Log model artifact to MLflow.
        
        Args:
            model_path: Path to model file or directory (e.g., best_model.pth)
            model_name: Optional artifact path within MLflow (default: 'models')
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
    
    # -----------------------------------------------------------------------
    # Dataset Metadata Logging
    # -----------------------------------------------------------------------
    # Logs dataset hash and sample counts for reproducibility tracking.
    # The dataset hash (from DatasetPreparer.calculate_dataset_hash()) is
    # critical for detecting dataset drift between runs.  If two runs have
    # different hashes, their datasets differ (new videos, re-extraction, etc.).
    # -----------------------------------------------------------------------
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
            dataset_hash: SHA256 hash of dataset (from DatasetPreparer)
            train_count: Number of training samples (frames)
            test_count: Number of test samples (frames)
            additional_info: Additional dataset metadata (e.g., frames_per_video)
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
    
    # -----------------------------------------------------------------------
    # Validation Gate Result Logging
    # -----------------------------------------------------------------------
    # Logs Gate A (or other gate) validation results to MLflow.  This
    # includes the pass/fail status and all gate metrics (F1, ECE, Brier).
    # Used for tracking model quality over time and identifying regressions.
    # -----------------------------------------------------------------------
    def log_validation_results(
        self,
        gate_name: str,
        passed: bool,
        metrics: Dict[str, Any]
    ):
        """
        Log validation gate results.
        
        Args:
            gate_name: Name of validation gate (e.g., 'gate_a')
            passed: Whether gate passed (True/False)
            metrics: Gate metrics (e.g., {'f1_macro': 0.87, 'ece': 0.06})
        """
        if not self.run:
            return
        
        # Log as metrics
        mlflow.log_metric(f'{gate_name}_passed', 1.0 if passed else 0.0)
        
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                mlflow.log_metric(f'{gate_name}_{key}', value)
        
        logger.info(f"Validation gate {gate_name}: {'PASSED' if passed else 'FAILED'}")
    
    # -----------------------------------------------------------------------
    # Training Run Finalization
    # -----------------------------------------------------------------------
    # Ends the current MLflow run and tags it with a final status.
    # Status values: 'FINISHED' (success), 'FAILED' (error), 'KILLED' (user abort).
    # Always call this at the end of training to properly close the run.
    # -----------------------------------------------------------------------
    def end_training(
        self,
        status: str = 'FINISHED'
    ):
        """
        End the current MLflow run.
        
        Args:
            status: Final status of the run ('FINISHED', 'FAILED', 'KILLED')
        """
        if self.run:
            mlflow.set_tag('status', status)
            mlflow.end_run()
            self.run = None
            logger.info(f"Ended MLflow run with status: {status}")
