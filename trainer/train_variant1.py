#!/usr/bin/env python3
"""
Variant 1 training: HSEmotion EfficientNet-B0 with backbone frozen,
training only a new 3-class head on run_0100 synthetic data.
Validated against AffectNet validation set (3-class: happy, sad, neutral).

The backbone weights are never modified — only the classification head
(1280 → 3) learns from the synthetic data.  Backbone unfreezing is
reserved for Variant 2 fine-tuning via apps/web/pages/07_Fine_Tune.py.

Usage:
    # 5-epoch smoke test (default)
    python -m trainer.train_variant1

    # Full training
    python -m trainer.train_variant1 --epochs 50

    # Custom learning rate
    python -m trainer.train_variant1 --epochs 20 --lr 5e-5
"""

import argparse
import logging
import sys
from pathlib import Path

from trainer.fer_finetune.config import TrainingConfig, ModelConfig, DataConfig
from trainer.fer_finetune.train_efficientnet import EfficientNetTrainer
from trainer.save_run_artifacts import save_training_artifacts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------- paths ----------------------------------------------------------
TRAIN_DATA_ROOT = "/media/rusty_admin/project_data/reachy_emotion/videos"
AFFECTNET_VAL_DIR = (
    "/media/rusty_admin/project_data/reachy_emotion/affectnet/"
    "consolidated/AffectNet+/human_annotated/validation_set"
)
BASE_CHECKPOINT_DIR = "/media/rusty_admin/project_data/reachy_emotion/checkpoints"


def build_config(epochs: int, lr: float, checkpoint_dir: str) -> TrainingConfig:
    return TrainingConfig(
        model=ModelConfig(
            backbone="efficientnet_b0",
            pretrained_weights="enet_b0_8_best_vgaf",
            num_classes=3,
            input_size=224,
            dropout_rate=0.3,
            freeze_backbone_epochs=epochs,  # backbone stays frozen for all epochs
            unfreeze_layers=[],             # no unfreezing — reserved for Variant 2
        ),
        data=DataConfig(
            data_root=TRAIN_DATA_ROOT,
            val_dir=AFFECTNET_VAL_DIR,
            val_dataset_type="affectnet",
            class_names=["happy", "sad", "neutral"],
            batch_size=32,
            num_workers=4,
            frame_sampling="random",
            mixup_alpha=0.2,
            mixup_probability=0.3,
            pin_memory=False,
        ),
        num_epochs=epochs,
        learning_rate=lr,
        weight_decay=1e-4,
        lr_scheduler="cosine",
        warmup_epochs=1,
        min_lr=1e-6,
        label_smoothing=0.1,
        gradient_clip_norm=1.0,
        early_stopping_enabled=epochs > 10,
        patience=10,
        mixed_precision=True,
        checkpoint_dir=checkpoint_dir,
        save_best_only=True,
        save_interval=5,
        seed=42,
        deterministic=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Variant 1 training — frozen backbone + AffectNet val")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs (default: 5 for smoke test)")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate (default: 1e-4)")
    parser.add_argument(
        "--run-id",
        default="run_0102",
        help="Training run ID whose synthetic data is used (default: run_0102)",
    )
    args = parser.parse_args()

    save_name = f"var1_{args.run_id}"
    checkpoint_dir = f"{BASE_CHECKPOINT_DIR}/variant_1/{save_name}"

    config = build_config(epochs=args.epochs, lr=args.lr, checkpoint_dir=checkpoint_dir)

    logger.info("=" * 60)
    logger.info("Variant 1 Training — frozen backbone + AffectNet validation")
    logger.info(f"  Run ID:      {args.run_id}  →  saves as {save_name}")
    logger.info(f"  Epochs: {args.epochs}  LR: {args.lr}")
    logger.info(f"  Train data:  {TRAIN_DATA_ROOT}/train/run/{args.run_id}")
    logger.info(f"  Val data:    {AFFECTNET_VAL_DIR}")
    logger.info(f"  Checkpoint:  {checkpoint_dir}")
    logger.info("=" * 60)

    trainer = EfficientNetTrainer(config)
    results = trainer.train(run_id=args.run_id)

    save_training_artifacts(
        results=results,
        save_name=save_name,
        variant="variant_1",
        class_names=["happy", "sad", "neutral"],
        project_root=Path(__file__).resolve().parents[1],
    )

    logger.info(f"Final status: {results['status']}")
    logger.info(f"Best val F1:  {results['best_metric']:.4f}")

    gate = results.get("gate_results", {})
    if gate.get("gate_a"):
        logger.info("Gate A: PASSED")
        return 0
    else:
        logger.warning("Gate A: FAILED")
        if gate.get("gate_a_details"):
            for k, v in gate["gate_a_details"].items():
                logger.info(f"  {k}: {v}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
