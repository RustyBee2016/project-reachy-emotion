#!/usr/bin/env python3
"""
ResNet-50 Emotion Classifier Training Script

Fine-tunes ResNet-50 pre-trained on AffectNet + RAF-DB for emotion classification.
Supports binary (happy/sad) and multi-class (8 emotions) configurations.

Model placeholder: resnet50-affectnet-raf-db
Storage path: /media/rusty_admin/project_data/ml_models/resnet50

Usage:
    python train_resnet50.py --config specs/resnet50_emotion_2cls.yaml
    python train_resnet50.py --config specs/resnet50_emotion_8cls.yaml --run-id my_run
"""

import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for ResNet-50 emotion classifier training."""
    parser = argparse.ArgumentParser(
        description='Train ResNet-50 emotion classifier (AffectNet + RAF-DB pretrained)'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='fer_finetune/specs/resnet50_emotion_2cls.yaml',
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
    
    args = parser.parse_args()
    
    # Generate run ID if not provided
    if args.run_id is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.run_id = f"resnet50_emotion_{timestamp}"
    
    logger.info("=" * 60)
    logger.info("ResNet-50 Emotion Classifier Training")
    logger.info("Model: resnet50-affectnet-raf-db (placeholder)")
    logger.info(f"Run ID: {args.run_id}")
    logger.info("=" * 60)
    
    # Import training modules
    try:
        from fer_finetune.config import TrainingConfig
        from fer_finetune.train import Trainer, train_model
        from fer_finetune.export import export_for_deployment
    except ImportError as e:
        logger.error(f"Failed to import training modules: {e}")
        logger.error("Ensure you're running on Ubuntu 1 with PyTorch installed")
        sys.exit(1)
    
    # Load configuration
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).parent / config_path
    
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    
    logger.info(f"Loading config: {config_path}")
    config = TrainingConfig.from_yaml(str(config_path))
    
    # Apply overrides
    if args.data_dir:
        config.data.data_root = args.data_dir
    if args.output_dir:
        config.checkpoint_dir = args.output_dir
    
    # Export only mode
    if args.export_only:
        if args.resume is None:
            logger.error("--resume required with --export-only")
            sys.exit(1)
        
        export_path = args.export_path or f"/workspace/exports/{args.run_id}"
        logger.info(f"Exporting model to: {export_path}")
        
        results = export_for_deployment(
            checkpoint_path=args.resume,
            output_dir=export_path,
            model_name=f"emotion_classifier_{args.run_id}",
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
    
    # Create trainer and run
    trainer = Trainer(config)
    
    # Resume from checkpoint if specified
    resume_epoch = 0
    if args.resume:
        if not Path(args.resume).exists():
            logger.error(f"Checkpoint not found: {args.resume}")
            sys.exit(1)
        resume_epoch = trainer.load_checkpoint(args.resume)
    
    # Run training
    results = trainer.train(run_id=args.run_id, resume_epoch=resume_epoch)
    
    # Print results
    print("\n" + "=" * 60)
    print("TRAINING RESULTS")
    print("=" * 60)
    print(json.dumps(results, indent=2, default=str))
    print("=" * 60)
    
    # Export if training succeeded and gates passed
    if results.get('status') == 'completed_gate_passed':
        logger.info("Gate A passed - exporting model for deployment")
        
        checkpoint_path = Path(config.checkpoint_dir) / 'best_model.pth'
        export_path = f"/workspace/exports/{args.run_id}"
        
        export_results = export_for_deployment(
            checkpoint_path=str(checkpoint_path),
            output_dir=export_path,
            model_name=f"emotion_classifier_{args.run_id}",
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
    
    # Exit with appropriate code
    if results['status'] in ['completed', 'completed_gate_passed']:
        sys.exit(0)
    elif results['status'] == 'completed_gate_failed':
        logger.warning("Training completed but quality gates failed")
        sys.exit(0)  # Still success, just needs more data/tuning
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
