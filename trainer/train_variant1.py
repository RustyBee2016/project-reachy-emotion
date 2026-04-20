#!/usr/bin/env python3
"""Variant 1 training: HSEmotion EfficientNet-B0 with backbone frozen,
training only a new 3-class head on run_XXXX synthetic data.
Validated against a held-out 25 % split of the same face-cropped synthetic frames.

The backbone weights are never modified — only the classification head
(1280 → 3) learns from the synthetic data.  Backbone unfreezing is
reserved for Variant 2 fine-tuning via apps/web/pages/07_Fine_Tune.py.

Dataset creation (handled automatically by DatasetPreparer):
    1. Extracts frames from videos/train/{happy,sad,neutral}/*.mp4
    2. Face detection + cropping (OpenCV DNN SSD) applied to every frame
    3. Splits extracted face crops 75 % train / 25 % validation
    4. Training frames  → videos/train/run/<run_id>/{happy,sad,neutral}/
    5. Validation frames → videos/validation/run/<run_id>/{happy,sad,neutral}/

Mixed-domain training (--mix-real):
    Adds real AffectNet images to the training set to close the
    synthetic-to-real domain gap.  The head sees both synthetic frames
    and real face images, calibrating decision boundaries for real-world
    feature distributions.  Use --real-samples-per-class to control how
    many real images per class are mixed in.

Prerequisites:
    Source videos must exist in videos/train/{happy,sad,neutral}/.

Usage:
    # 5-epoch smoke test (default)
    python -m trainer.train_variant1

    # Full training
    python -m trainer.train_variant1 --epochs 50

    # Mixed-domain training (recommended for closing synthetic-to-real gap)
    python -m trainer.train_variant1 --epochs 30 --mix-real --real-samples-per-class 5000

    # Custom learning rate
    python -m trainer.train_variant1 --epochs 20 --lr 5e-5
"""

import argparse
import logging
import sys
from pathlib import Path

from trainer.fer_finetune.config import TrainingConfig, ModelConfig, DataConfig
from trainer.fer_finetune.train_efficientnet import EfficientNetTrainer
from trainer.prepare_dataset import DatasetPreparer
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


def _resolve_val_dir(run_id: str) -> str:
    """Build the run-scoped validation directory path."""
    return f"{VALIDATION_ROOT}/{run_id}"


# Default AffectNet training set path (human-annotated, ~414K images)
AFFECTNET_TRAIN_DIR = (
    "/media/rusty_admin/project_data/reachy_emotion/affectnet/"
    "consolidated/AffectNet+/human_annotated/train_set"
)
# Default test-labels manifest (for excluding test images from training)
DEFAULT_TEST_MANIFEST = (
    "/media/rusty_admin/project_data/reachy_emotion/videos/"
    "manifests/test_dataset_01_test_labels.jsonl"
)


def build_config(
    epochs: int,
    lr: float,
    checkpoint_dir: str,
    val_dir: str,
    affectnet_train_dir: str = "",
    real_samples_per_class: int = 5000,
    test_manifest_path: str = "",
) -> TrainingConfig:
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
            val_dir=val_dir,
            val_dataset_type="emotion",
            class_names=["happy", "sad", "neutral"],
            batch_size=32,
            num_workers=4,
            frame_sampling="random",
            mixup_alpha=0.2,
            mixup_probability=0.3,
            pin_memory=False,
            affectnet_train_dir=affectnet_train_dir,
            real_samples_per_class=real_samples_per_class,
            test_manifest_path=test_manifest_path,
        ),
        num_epochs=epochs,
        learning_rate=lr,
        weight_decay=1e-4,
        lr_scheduler="cosine",
        warmup_epochs=1,
        min_lr=1e-6,
        label_smoothing=0.15,
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
    parser = argparse.ArgumentParser(description="Variant 1 training — frozen backbone + synthetic 75/25 val")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs (default: 5 for smoke test)")
    parser.add_argument("--lr", type=float, default=1e-4, help="Learning rate (default: 1e-4)")
    parser.add_argument(
        "--run-id",
        default="run_0102",
        help="Training run ID whose synthetic data is used (default: run_0102)",
    )
    parser.add_argument(
        "--skip-prepare",
        action="store_true",
        help="Skip dataset preparation (use existing extracted frames + manifest)",
    )
    parser.add_argument(
        "--val-dir",
        default=None,
        dest="val_dir",
        help=(
            "Override validation directory with class subdirs (happy/, sad/, neutral/). "
            "Defaults to the run-scoped 25%% synthetic split at validation/run/<run_id>/."
        ),
    )
    parser.add_argument(
        "--no-face-crop",
        action="store_true",
        dest="no_face_crop",
        help="Disable face detection and cropping during frame extraction (NOT recommended).",
    )
    parser.add_argument(
        "--face-confidence",
        type=float,
        default=0.6,
        dest="face_confidence",
        help="Minimum face detection confidence (default: 0.6)",
    )
    parser.add_argument(
        "--face-target-size",
        type=int,
        default=224,
        dest="face_target_size",
        help="Face crop output size in pixels (default: 224)",
    )
    parser.add_argument(
        "--mix-real",
        action="store_true",
        dest="mix_real",
        help=(
            "Enable mixed-domain training: combine synthetic frames with real "
            "AffectNet images to calibrate the head's decision boundaries for "
            "real-world data. This is the primary strategy for closing the "
            "synthetic-to-real domain gap."
        ),
    )
    parser.add_argument(
        "--real-samples-per-class",
        type=int,
        default=5000,
        dest="real_samples_per_class",
        help=(
            "Max real AffectNet images per class for mixed-domain training "
            "(default: 5000). Only used when --mix-real is set."
        ),
    )
    parser.add_argument(
        "--affectnet-train-dir",
        default=AFFECTNET_TRAIN_DIR,
        dest="affectnet_train_dir",
        help=(
            "Path to AffectNet human-annotated training set with images/ and "
            "annotations/ subdirectories. Only used when --mix-real is set."
        ),
    )
    parser.add_argument(
        "--test-manifest",
        default="",
        dest="test_manifest",
        help=(
            "Path to test-labels JSONL manifest. AffectNet IDs in this file "
            "are excluded from mixed-domain training to prevent data leakage. "
            "Auto-resolved to the default test_dataset_01 manifest when "
            "--mix-real is set and this flag is omitted."
        ),
    )
    args = parser.parse_args()

    save_name = f"var1_{args.run_id}"
    checkpoint_dir = f"{BASE_CHECKPOINT_DIR}/variant_1/{save_name}"
    val_dir = args.val_dir if args.val_dir else _resolve_val_dir(args.run_id)

    # ------------------------------------------------------------------
    # Dataset preparation: extract per-run frames from source videos
    # ------------------------------------------------------------------
    # Creates train/run/<run_id>/{happy,sad,neutral}/ with extracted
    # JPEG frames (10 per video) and a JSONL manifest under manifests/.
    # Without this step, training falls back to raw source videos which
    # is non-reproducible and cannot be inspected.
    # ------------------------------------------------------------------
    run_train_dir = Path(TRAIN_DATA_ROOT) / "train" / "run" / args.run_id
    if not args.skip_prepare:
        logger.info("Preparing per-run training dataset …")
        preparer = DatasetPreparer(base_path=TRAIN_DATA_ROOT)
        prep_result = preparer.prepare_training_dataset(
            run_id=args.run_id,
            face_crop=not args.no_face_crop,
            target_size=args.face_target_size,
            face_confidence=args.face_confidence,
        )
        logger.info(
            f"  Extracted {prep_result['train_count']} train + "
            f"{prep_result['val_count']} val frames from "
            f"{prep_result['videos_processed']} videos  "
            f"(hash: {prep_result['dataset_hash'][:12]}…)"
        )
    else:
        if not run_train_dir.exists():
            logger.error(
                f"--skip-prepare used but {run_train_dir} does not exist. "
                f"Run without --skip-prepare first."
            )
            return 1
        logger.info(f"Skipping dataset preparation — using existing {run_train_dir}")

    # Resolve mixed-domain training settings
    affectnet_dir = args.affectnet_train_dir if args.mix_real else ""
    real_per_class = args.real_samples_per_class if args.mix_real else 0

    # Auto-resolve test manifest for leakage prevention when --mix-real is used
    test_manifest = args.test_manifest
    if args.mix_real and not test_manifest:
        if Path(DEFAULT_TEST_MANIFEST).exists():
            test_manifest = DEFAULT_TEST_MANIFEST
            logger.info(f"Auto-resolved test manifest for leakage prevention: {test_manifest}")
        else:
            logger.warning(
                "No --test-manifest provided and default not found. "
                "Training may include test images — results would be invalid!"
            )

    config = build_config(
        epochs=args.epochs,
        lr=args.lr,
        checkpoint_dir=checkpoint_dir,
        val_dir=val_dir,
        affectnet_train_dir=affectnet_dir,
        real_samples_per_class=real_per_class,
        test_manifest_path=test_manifest,
    )

    logger.info("=" * 60)
    if args.mix_real:
        logger.info("Variant 1 Training — frozen backbone + MIXED-DOMAIN (synthetic + real)")
    else:
        logger.info("Variant 1 Training — frozen backbone + run-scoped validation")
    logger.info(f"  Run ID:      {args.run_id}  →  saves as {save_name}")
    logger.info(f"  Epochs: {args.epochs}  LR: {args.lr}")
    logger.info(f"  Train data:  {run_train_dir}")
    if args.mix_real:
        logger.info(f"  + Real data: {affectnet_dir} ({real_per_class}/class)")
        if test_manifest:
            logger.info(f"  Exclude:     {Path(test_manifest).name} (leakage prevention)")
    logger.info(f"  Val data:    {val_dir}")
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
