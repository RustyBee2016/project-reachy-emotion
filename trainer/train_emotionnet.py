#!/usr/bin/env python3
"""
EmotionNet Training Orchestrator
Coordinates TAO training with MLflow tracking and validation gates.
"""

import os
import sys
import argparse
import subprocess
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trainer.prepare_dataset import DatasetPreparer
from trainer.mlflow_tracker import MLflowTracker
from trainer.tao.config_loader import TAOConfigLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TrainingOrchestrator:
    """Orchestrate EmotionNet training with TAO and MLflow."""
    
    def __init__(
        self,
        config_path: str,
        dataset_path: str,
        output_path: str,
        mlflow_experiment: str = "emotionnet"
    ):
        """
        Initialize training orchestrator.
        
        Args:
            config_path: Path to TAO training config YAML
            dataset_path: Path to dataset root directory
            output_path: Path for training outputs
            mlflow_experiment: MLflow experiment name
        """
        self.config_path = Path(config_path)
        self.dataset_path = Path(dataset_path)
        self.output_path = Path(output_path)
        
        # Load configuration
        self.config_loader = TAOConfigLoader()
        self.config = self.config_loader.load_config(str(self.config_path))
        
        # Initialize components
        self.dataset_preparer = DatasetPreparer(str(self.dataset_path))
        self.mlflow_tracker = MLflowTracker(experiment_name=mlflow_experiment)
        
        # Create output directory
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Training orchestrator initialized")
        logger.info(f"Config: {self.config_path}")
        logger.info(f"Dataset: {self.dataset_path}")
        logger.info(f"Output: {self.output_path}")
    
    def prepare_dataset(
        self,
        run_id: str,
        train_fraction: float = 0.7,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Prepare training dataset with balanced sampling.
        
        Args:
            run_id: Unique identifier for this training run
            train_fraction: Fraction of data for training
            seed: Random seed for reproducibility
        
        Returns:
            Dataset metadata dictionary
        """
        logger.info(f"Preparing dataset for run: {run_id}")
        
        dataset_info = self.dataset_preparer.prepare_training_dataset(
            run_id=run_id,
            train_fraction=train_fraction,
            seed=seed
        )
        
        logger.info(f"Dataset prepared: {dataset_info['train_count']} train, "
                   f"{dataset_info['test_count']} test samples")
        
        return dataset_info
    
    def train_model(
        self,
        run_id: str,
        resume_from: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Train EmotionNet model using TAO.
        
        Args:
            run_id: Training run identifier
            resume_from: Optional checkpoint to resume from
        
        Returns:
            Tuple of (success, metrics)
        """
        logger.info(f"Starting TAO training for run: {run_id}")
        
        # Prepare TAO command
        experiment_dir = self.output_path / run_id
        experiment_dir.mkdir(parents=True, exist_ok=True)
        
        # Build TAO command
        tao_cmd = [
            "docker", "exec", "reachy-tao-train",
            "tao", "emotionnet", "train",
            "-e", f"/workspace/specs/{self.config_path.name}",
            "-r", f"/workspace/experiments/{run_id}",
            "-k", os.getenv("TAO_API_KEY", "tlt_encode")
        ]
        
        if resume_from:
            tao_cmd.extend(["--resume_model_weights", resume_from])
        
        logger.info(f"TAO command: {' '.join(tao_cmd)}")
        
        # Execute training
        try:
            result = subprocess.run(
                tao_cmd,
                capture_output=True,
                text=True,
                timeout=7200  # 2 hour timeout
            )
            
            if result.returncode != 0:
                logger.error(f"TAO training failed: {result.stderr}")
                return False, {"error": result.stderr}
            
            # Parse training output for metrics
            metrics = self._parse_training_output(result.stdout)
            
            logger.info(f"Training completed successfully")
            return True, metrics
            
        except subprocess.TimeoutExpired:
            logger.error("Training timeout exceeded")
            return False, {"error": "Training timeout"}
        except Exception as e:
            logger.error(f"Training error: {e}")
            return False, {"error": str(e)}
    
    def _parse_training_output(self, output: str) -> Dict[str, Any]:
        """
        Parse TAO training output for metrics.
        
        Args:
            output: TAO stdout output
        
        Returns:
            Dictionary of parsed metrics
        """
        metrics = {
            'epochs_completed': 0,
            'final_loss': None,
            'final_accuracy': None,
            'final_f1': None
        }
        
        lines = output.split('\n')
        for line in lines:
            # Parse epoch metrics
            # Example: "Epoch 50/50 - loss: 0.234 - accuracy: 0.856 - f1: 0.842"
            if 'Epoch' in line and 'loss:' in line:
                try:
                    parts = line.split('-')
                    epoch_part = parts[0].split()[1]
                    epoch_num = int(epoch_part.split('/')[0])
                    metrics['epochs_completed'] = max(metrics['epochs_completed'], epoch_num)
                    
                    # Extract metrics
                    for part in parts[1:]:
                        if ':' in part:
                            key, value = part.split(':')
                            key = key.strip()
                            value = float(value.strip())
                            
                            if key == 'loss':
                                metrics['final_loss'] = value
                            elif key == 'accuracy':
                                metrics['final_accuracy'] = value
                            elif key == 'f1':
                                metrics['final_f1'] = value
                except (ValueError, IndexError):
                    continue
        
        return metrics
    
    def validate_gates(
        self,
        run_id: str,
        metrics: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Validate training results against quality gates.
        
        Args:
            run_id: Training run identifier
            metrics: Training metrics
        
        Returns:
            Dictionary of gate results
        """
        logger.info("Validating quality gates")
        
        gates = self.config.get('gates', {})
        results = {}
        
        # Gate A: Offline validation
        if 'gate_a' in gates:
            gate_a = gates['gate_a']
            f1_macro = metrics.get('final_f1', 0.0)
            
            gate_a_passed = (
                f1_macro >= gate_a.get('min_f1_macro', 0.84)
            )
            
            results['gate_a'] = gate_a_passed
            
            logger.info(f"Gate A: {'PASSED' if gate_a_passed else 'FAILED'} "
                       f"(F1: {f1_macro:.3f} vs {gate_a.get('min_f1_macro', 0.84):.3f})")
            
            # Log to MLflow
            self.mlflow_tracker.log_validation_results(
                gate_name='gate_a',
                passed=gate_a_passed,
                metrics={'f1_macro': f1_macro}
            )
        
        return results
    
    def run_training_pipeline(
        self,
        run_id: Optional[str] = None,
        train_fraction: float = 0.7,
        seed: Optional[int] = None,
        skip_dataset_prep: bool = False
    ) -> Dict[str, Any]:
        """
        Run complete training pipeline.
        
        Args:
            run_id: Training run identifier (auto-generated if None)
            train_fraction: Fraction for training split
            seed: Random seed
            skip_dataset_prep: Skip dataset preparation if already done
        
        Returns:
            Pipeline results dictionary
        """
        # Generate run ID if not provided
        if run_id is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            model_name = self.config.get('model', {}).get('model_name', 'emotionnet')
            run_id = f"{model_name}_{timestamp}"
        
        logger.info(f"=" * 60)
        logger.info(f"Starting training pipeline: {run_id}")
        logger.info(f"=" * 60)
        
        results = {
            'run_id': run_id,
            'status': 'started',
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Step 1: Prepare dataset
            if not skip_dataset_prep:
                dataset_info = self.prepare_dataset(run_id, train_fraction, seed)
                results['dataset'] = dataset_info
            else:
                logger.info("Skipping dataset preparation")
                dataset_info = {'dataset_hash': 'unknown'}
            
            # Step 2: Start MLflow run
            training_config = {
                'model_arch': self.config.get('model', {}).get('arch'),
                'num_classes': self.config.get('model', {}).get('num_classes'),
                'batch_size': self.config.get('training', {}).get('batch_size'),
                'learning_rate': self.config.get('training', {}).get('learning_rate'),
                'num_epochs': self.config.get('training', {}).get('num_epochs'),
                'optimizer': self.config.get('training', {}).get('optimizer')
            }
            
            self.mlflow_tracker.start_training(
                run_id=run_id,
                config=training_config,
                tags={'config_file': self.config_path.name}
            )
            
            # Log dataset info
            if not skip_dataset_prep:
                self.mlflow_tracker.log_dataset_info(
                    dataset_hash=dataset_info['dataset_hash'],
                    train_count=dataset_info['train_count'],
                    test_count=dataset_info['test_count'],
                    additional_info={'seed': dataset_info['seed']}
                )
            
            # Step 3: Train model
            success, metrics = self.train_model(run_id)
            results['training'] = {
                'success': success,
                'metrics': metrics
            }
            
            if not success:
                results['status'] = 'failed'
                self.mlflow_tracker.end_training(status='FAILED')
                return results
            
            # Step 4: Validate gates
            gate_results = self.validate_gates(run_id, metrics)
            results['gates'] = gate_results
            
            # Step 5: Determine final status
            if gate_results.get('gate_a', False):
                results['status'] = 'completed'
                self.mlflow_tracker.end_training(status='FINISHED')
                logger.info(f"Training pipeline completed successfully: {run_id}")
            else:
                results['status'] = 'completed_gates_failed'
                self.mlflow_tracker.end_training(status='FINISHED_GATES_FAILED')
                logger.warning(f"Training completed but gates failed: {run_id}")
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            results['status'] = 'error'
            results['error'] = str(e)
            self.mlflow_tracker.end_training(status='FAILED')
        
        logger.info(f"=" * 60)
        logger.info(f"Pipeline finished: {results['status']}")
        logger.info(f"=" * 60)
        
        return results


def main():
    """Main entry point for training orchestrator."""
    parser = argparse.ArgumentParser(description='Train EmotionNet model with TAO')
    parser.add_argument('--config', required=True, help='Path to TAO config YAML')
    parser.add_argument('--dataset', required=True, help='Path to dataset root')
    parser.add_argument('--output', required=True, help='Path for training outputs')
    parser.add_argument('--run-id', help='Training run ID (auto-generated if not provided)')
    parser.add_argument('--train-fraction', type=float, default=0.7, help='Training fraction')
    parser.add_argument('--seed', type=int, help='Random seed')
    parser.add_argument('--skip-dataset-prep', action='store_true', help='Skip dataset preparation')
    parser.add_argument('--mlflow-experiment', default='emotionnet', help='MLflow experiment name')
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = TrainingOrchestrator(
        config_path=args.config,
        dataset_path=args.dataset,
        output_path=args.output,
        mlflow_experiment=args.mlflow_experiment
    )
    
    # Run pipeline
    results = orchestrator.run_training_pipeline(
        run_id=args.run_id,
        train_fraction=args.train_fraction,
        seed=args.seed,
        skip_dataset_prep=args.skip_dataset_prep
    )
    
    # Print results
    print("\n" + "=" * 60)
    print("TRAINING RESULTS")
    print("=" * 60)
    print(json.dumps(results, indent=2))
    print("=" * 60)
    
    # Exit with appropriate code
    if results['status'] in ['completed', 'completed_gates_failed']:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
