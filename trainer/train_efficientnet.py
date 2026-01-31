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
    """Main entry point for EfficientNet-B0 emotion classifier training."""
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
    
    # Generate run ID if not provided
    if args.run_id is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.run_id = f"efficientnet_b0_emotion_{timestamp}"
    
    logger.info("=" * 60)
    logger.info("EfficientNet-B0 Emotion Classifier Training")
    logger.info("Model: HSEmotion enet_b0_8_best_vgaf")
    logger.info(f"Run ID: {args.run_id}")
    logger.info("=" * 60)
    
    # Import training modules
    try:
        from fer_finetune.config import TrainingConfig
        from fer_finetune.train_efficientnet import EfficientNetTrainer
        from fer_finetune.export import export_efficientnet_for_deployment
    except ImportError as e:
        logger.error(f"Failed to import training modules: {e}")
        logger.error("Ensure you're running on Ubuntu 1 with PyTorch installed")
        logger.error("Install dependencies: pip install torch timm albumentations")
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
    
    # Create trainer
    trainer = EfficientNetTrainer(config, weights_path=args.weights_path)
    
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
    
    # Exit with appropriate code
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
