#!/usr/bin/env python3
"""
EfficientNet-B0 Emotion Classifier Training Script (HSEmotion)

Fine-tunes EfficientNet-B0 pre-trained on VGGFace2 + AffectNet (HSEmotion)
for emotion classification. Supports binary (happy/sad) and multi-class
(8 emotions) configurations.

Model: HSEmotion enet_b0_8_best_vgaf
Storage path: /media/rusty_admin/project_data/ml_models/efficientnet_b0

Usage:
    # Binary classification (Phase 1)
    python train_efficientnet.py --config fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml

    # 8-class classification (Phase 2+)
    python train_efficientnet.py --config fer_finetune/specs/efficientnet_b0_emotion_8cls.yaml

    # Resume from checkpoint
    python train_efficientnet.py --config <config.yaml> --resume checkpoints/latest.pth

    # Export only (ONNX)
    python train_efficientnet.py --export-only --resume checkpoints/best_model.pth
"""

# ---------------------------------------------------------------------------
# Standard library imports for CLI argument parsing, filesystem operations,
# JSON serialization (for structured result output), and logging.
# ---------------------------------------------------------------------------
import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
import logging

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path so that sibling packages
# (fer_finetune, trainer, apps) can be imported regardless of the
# working directory from which this script is launched.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Configure structured logging for training progress, errors, and gate
# validation results.  All log lines include timestamps for correlation
# with MLflow run records and n8n workflow audit trails.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for EfficientNet-B0 emotion classifier training."""

    # -------------------------------------------------------------------
    # CLI Argument Definitions
    # -------------------------------------------------------------------
    # This block defines every command-line flag the script accepts.
    # The script is invoked directly by the Streamlit web UI (03_Train.py)
    # via training_control.py, or manually from the command line.
    # Key arguments:
    #   --config   : Path to YAML spec (e.g. efficientnet_b0_emotion_3cls.yaml)
    #   --run-id   : Ties this run to MLflow, manifests, and dashboard payloads
    #   --resume   : Checkpoint path for warm-starting interrupted training
    #   --export-only : Skip training and jump straight to ONNX export
    #   --weights-path: Override default HSEmotion pretrained weight location
    # -------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description='Train EfficientNet-B0 emotion classifier (HSEmotion pretrained)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml',
        help='Path to training config YAML'
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default=None,
        help='Override data directory from config'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Override output directory from config'
    )
    parser.add_argument(
        '--run-id',
        type=str,
        default=None,
        help='Training run ID (auto-generated if not provided)'
    )
    parser.add_argument(
        '--resume',
        type=str,
        default=None,
        help='Path to checkpoint to resume from'
    )
    parser.add_argument(
        '--export-only',
        action='store_true',
        help='Skip training, only export existing checkpoint'
    )
    parser.add_argument(
        '--export-path',
        type=str,
        default=None,
        help='Path for ONNX export (used with --export-only)'
    )
    parser.add_argument(
        '--weights-path',
        type=str,
        default=None,
        help='Explicit path to pretrained weights file'
    )
    
    args = parser.parse_args()
    
    # -------------------------------------------------------------------
    # Run ID Generation
    # -------------------------------------------------------------------
    # If no explicit run ID is provided, generate a timestamped one.
    # This ID is used throughout the pipeline: MLflow experiment tracking,
    # JSONL manifest naming, dashboard payload files, and n8n correlation.
    # -------------------------------------------------------------------
    if args.run_id is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.run_id = f"efficientnet_b0_emotion_{timestamp}"
    
    logger.info("=" * 60)
    logger.info("EfficientNet-B0 Emotion Classifier Training")
    logger.info("Model: HSEmotion enet_b0_8_best_vgaf")
    logger.info(f"Run ID: {args.run_id}")
    logger.info("=" * 60)
    
    # -------------------------------------------------------------------
    # Lazy Import of Heavy ML Dependencies
    # -------------------------------------------------------------------
    # PyTorch, timm, and albumentations are only available on Ubuntu 1
    # (the training node).  A deferred import inside a try/except block
    # gives a clear error message if this script is accidentally run on
    # Ubuntu 2 (gateway) or Jetson (inference-only), where these
    # packages are not installed.
    # -------------------------------------------------------------------
    try:
        from fer_finetune.config import TrainingConfig
        from fer_finetune.train_efficientnet import EfficientNetTrainer
        from fer_finetune.export import export_efficientnet_for_deployment
    except ImportError as e:
        logger.error(f"Failed to import training modules: {e}")
        logger.error("Ensure you're running on Ubuntu 1 with PyTorch installed")
        logger.error("Install dependencies: pip install torch timm albumentations")
        sys.exit(1)
    
    # -------------------------------------------------------------------
    # Configuration Loading & CLI Overrides
    # -------------------------------------------------------------------
    # Load the YAML training spec (model architecture, hyperparameters,
    # data paths, augmentation settings).  Relative paths are resolved
    # against the trainer/ directory.  CLI flags --data-dir and
    # --output-dir override YAML values, enabling the web UI (07_Fine_Tune)
    # to inject per-run paths without editing the spec file.
    # -------------------------------------------------------------------
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).parent / config_path
    
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    
    logger.info(f"Loading config: {config_path}")
    config = TrainingConfig.from_yaml(str(config_path))
    
    # Apply CLI overrides to the loaded config
    if args.data_dir:
        config.data.data_root = args.data_dir
    if args.output_dir:
        config.checkpoint_dir = args.output_dir
    
    # -------------------------------------------------------------------
    # Export-Only Mode
    # -------------------------------------------------------------------
    # When --export-only is set, skip training entirely and convert an
    # existing checkpoint to ONNX format for downstream TensorRT
    # conversion on the Jetson (Agent 7 — Deployment Agent).  This is
    # used when a model has already been trained and only the deployment
    # artifact is needed.
    # -------------------------------------------------------------------
    if args.export_only:
        if args.resume is None:
            logger.error("--resume required with --export-only")
            sys.exit(1)
        
        export_path = args.export_path or f"/workspace/exports/{args.run_id}"
        logger.info(f"Exporting model to: {export_path}")
        
        results = export_efficientnet_for_deployment(
            checkpoint_path=args.resume,
            output_dir=export_path,
            model_name=f"emotion_efficientnet_{args.run_id}",
            precision="fp16",
            input_size=config.model.input_size,
            num_classes=config.model.num_classes,
        )
        
        print("\n" + "=" * 60)
        print("EXPORT RESULTS")
        print("=" * 60)
        print(json.dumps(results, indent=2))
        print("=" * 60)
        return
    
    # -------------------------------------------------------------------
    # Trainer Instantiation & Checkpoint Resume
    # -------------------------------------------------------------------
    # EfficientNetTrainer wraps the two-phase training loop:
    #   Phase 1 (epochs 1-5): Backbone frozen, only classification head trains
    #   Phase 2 (epochs 6+):  Selectively unfreeze blocks.5, blocks.6, conv_head
    # If --resume is provided, the trainer restores optimizer state and
    # learning rate schedule from the checkpoint, continuing from the
    # saved epoch.
    # -------------------------------------------------------------------
    trainer = EfficientNetTrainer(config, weights_path=args.weights_path)
    
    resume_epoch = 0
    if args.resume:
        if not Path(args.resume).exists():
            logger.error(f"Checkpoint not found: {args.resume}")
            sys.exit(1)
        resume_epoch = trainer.load_checkpoint(args.resume)
    
    # Execute the training loop (returns a results dict with status, metrics)
    results = trainer.train(run_id=args.run_id, resume_epoch=resume_epoch)
    
    # -------------------------------------------------------------------
    # Results Output & Conditional ONNX Export
    # -------------------------------------------------------------------
    # Print training results as JSON for machine-parseable output.
    # If Gate A validation passed during training (status =
    # 'completed_gate_passed'), automatically export the best checkpoint
    # to ONNX.  The ONNX file is later converted to TensorRT by the
    # Deployment Agent (Agent 7) on the Jetson Xavier NX.
    # -------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("TRAINING RESULTS")
    print("=" * 60)
    print(json.dumps(results, indent=2, default=str))
    print("=" * 60)
    
    if results.get('status') == 'completed_gate_passed':
        logger.info("Gate A passed - exporting model for deployment")
        
        checkpoint_path = Path(config.checkpoint_dir) / 'best_model.pth'
        export_path = f"/workspace/exports/{args.run_id}"
        
        try:
            export_results = export_efficientnet_for_deployment(
                checkpoint_path=str(checkpoint_path),
                output_dir=export_path,
                model_name=f"emotion_efficientnet_{args.run_id}",
                precision="fp16",
                input_size=config.model.input_size,
                num_classes=config.model.num_classes,
            )
            
            results['export'] = export_results
            
            print("\n" + "=" * 60)
            print("EXPORT RESULTS")
            print("=" * 60)
            print(json.dumps(export_results, indent=2))
            print("=" * 60)
        except Exception as e:
            logger.error(f"Export failed: {e}")
            results['export_error'] = str(e)
    
    # -------------------------------------------------------------------
    # Exit Code Convention
    # -------------------------------------------------------------------
    # Exit 0 on successful completion (even if gates failed — the model
    # was trained correctly, it just didn't meet thresholds).  Exit 1
    # only on actual training errors.  n8n workflow nodes and
    # training_control.py use the exit code to determine success/failure.
    # -------------------------------------------------------------------
    if results['status'] in ['completed', 'completed_gate_passed']:
        sys.exit(0)
    elif results['status'] == 'completed_gate_failed':
        logger.warning("Training completed but quality gates failed")
        logger.warning("Consider: more data, longer training, or hyperparameter tuning")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
