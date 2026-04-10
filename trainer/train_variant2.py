#!/usr/bin/env python3
"""
Variant 2 fine-tuning: starts from a Variant 1 checkpoint and selectively
unfreezes backbone layers for domain adaptation on real-world data.

Variant 1 preserved the original HSEmotion backbone weights — only the 3-class
head was trained on synthetic data.  Variant 2 loads that checkpoint, keeps the
backbone frozen for an initial phase, then unlocks the specified layers so the
model can adapt its higher-level features to real faces (AffectNet validation).

The backbone receives 1/10th of the head learning rate during unfreezing to
prevent catastrophic forgetting.

Usage:
    # Smoke test (5 epochs) — verify pipeline before a full run
    python -m trainer.train_variant2 \\
        --checkpoint /media/rusty_admin/project_data/reachy_emotion/checkpoints/variant_1/var1_run_0102/best_model.pth

    # Full fine-tuning run
    python -m trainer.train_variant2 \\
        --checkpoint .../variant_1/var1_run_0102/best_model.pth \\
        --run-id var2_0001 \\
        --epochs 30 \\
        --freeze-epochs 5 \\
        --unfreeze-layers blocks.5,blocks.6,conv_head \\
        --lr 3e-4
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import torch

from trainer.fer_finetune.config import DataConfig, ModelConfig, TrainingConfig
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
VALIDATION_ROOT = "/media/rusty_admin/project_data/reachy_emotion/videos/validation/run"
BASE_CHECKPOINT_DIR = "/media/rusty_admin/project_data/reachy_emotion/checkpoints"
DEFAULT_UNFREEZE_LAYERS = ["blocks.5", "blocks.6", "conv_head"]


def _resolve_val_dir(run_id: str) -> str:
    """Build the run-scoped validation directory path."""
    return f"{VALIDATION_ROOT}/{run_id}"


def build_config(
    epochs: int,
    lr: float,
    freeze_epochs: int,
    unfreeze_layers: list[str],
    checkpoint_dir: str,
    val_dir: str,
) -> TrainingConfig:
    return TrainingConfig(
        model=ModelConfig(
            backbone="efficientnet_b0",
            pretrained_weights="enet_b0_8_best_vgaf",
            num_classes=3,
            input_size=224,
            dropout_rate=0.3,
            freeze_backbone_epochs=freeze_epochs,
            unfreeze_layers=unfreeze_layers,
        ),
        data=DataConfig(
            data_root=TRAIN_DATA_ROOT,
            val_dir=val_dir,
            val_dataset_type="emotion",
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
        warmup_epochs=2,
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


def _load_weights_only(trainer: EfficientNetTrainer, checkpoint_path: str) -> None:
    """Load model weights from a Variant 1 checkpoint, preserving fresh training state.

    Uses strict=False so that minor key mismatches (e.g. an extra layer added
    in the new head config) are handled gracefully with a warning rather than a
    hard error.
    """
    ckpt = torch.load(checkpoint_path, map_location=trainer.device, weights_only=False)
    if "model_state_dict" in ckpt:
        state_dict = ckpt["model_state_dict"]
    elif "state_dict" in ckpt:
        state_dict = ckpt["state_dict"]
    else:
        state_dict = ckpt
    state_dict = {k.replace("module.", ""): v for k, v in state_dict.items()}
    missing, unexpected = trainer.model.load_state_dict(state_dict, strict=False)
    if missing:
        logger.warning("Missing keys when loading Variant 1 weights: %s", missing[:5])
    if unexpected:
        logger.warning("Unexpected keys when loading Variant 1 weights: %s", unexpected[:5])
    logger.info("Loaded Variant 1 weights from %s", checkpoint_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Variant 2 — fine-tune a Variant 1 checkpoint with selective backbone unfreezing"
    )
    parser.add_argument(
        "--checkpoint",
        required=True,
        help=(
            "Path to a Variant 1 best_model.pth "
            "(e.g. .../checkpoints/variant_1/var1_run_0102/best_model.pth)"
        ),
    )
    parser.add_argument(
        "--run-id",
        default="var2_0001",
        help="Identifier for this Variant 2 run, used for checkpoint directory naming (default: var2_0001)",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=5,
        help="Total training epochs (default: 5 for smoke test; use 30+ for a full run)",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=3e-4,
        help="Peak learning rate for the head; backbone receives lr/10 after unfreezing (default: 3e-4)",
    )
    parser.add_argument(
        "--freeze-epochs",
        type=int,
        default=5,
        dest="freeze_epochs",
        help="Epochs to keep the backbone fully frozen before unfreezing (default: 5)",
    )
    parser.add_argument(
        "--unfreeze-layers",
        default=",".join(DEFAULT_UNFREEZE_LAYERS),
        dest="unfreeze_layers",
        help=(
            "Comma-separated backbone layer names to unfreeze in Phase 2. "
            "Default: blocks.5,blocks.6,conv_head. "
            "Add blocks.3,blocks.4 for deeper adaptation (risk: catastrophic forgetting)."
        ),
    )
    parser.add_argument(
        "--val-run-id",
        default=None,
        dest="val_run_id",
        help=(
            "Run ID for the validation dataset (e.g. run_0103). "
            "Defaults to --run-id if not specified."
        ),
    )
    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.exists():
        logger.error("Checkpoint not found: %s", checkpoint_path)
        return 1

    unfreeze_layers = [lyr.strip() for lyr in args.unfreeze_layers.split(",") if lyr.strip()]
    save_dir = f"{BASE_CHECKPOINT_DIR}/variant_2/{args.run_id}"
    val_run_id = args.val_run_id or args.run_id
    val_dir = _resolve_val_dir(val_run_id)

    config = build_config(
        epochs=args.epochs,
        lr=args.lr,
        freeze_epochs=args.freeze_epochs,
        unfreeze_layers=unfreeze_layers,
        checkpoint_dir=save_dir,
        val_dir=val_dir,
    )

    logger.info("=" * 60)
    logger.info("Variant 2 Fine-Tuning")
    logger.info(f"  Source checkpoint:  {checkpoint_path}")
    logger.info(f"  Run ID:             {args.run_id}")
    logger.info(f"  Epochs: {args.epochs}  LR: {args.lr}")
    logger.info(f"  Freeze epochs: {args.freeze_epochs}  →  Unfreeze: {unfreeze_layers}")
    logger.info(f"  Val data:    {val_dir}")
    logger.info(f"  Checkpoint:  {save_dir}")
    logger.info("=" * 60)

    trainer = EfficientNetTrainer(config)
    _load_weights_only(trainer, str(checkpoint_path))

    results = trainer.train(run_id=args.run_id)

    save_training_artifacts(
        results=results,
        save_name=args.run_id,
        variant="variant_2",
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
