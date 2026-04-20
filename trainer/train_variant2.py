#!/usr/bin/env python3
"""
Variant 2 fine-tuning: starts from a Variant 1 checkpoint and selectively
unfreezes backbone layers for domain adaptation.

Variant 1 preserved the original HSEmotion backbone weights — only the 3-class
head was trained on synthetic data.  Variant 2 loads that checkpoint, keeps the
backbone frozen for an initial phase, then unlocks the specified layers so the
model can adapt its higher-level features.

Variant 2 trains on the SAME face-cropped synthetic data used by Variant 1 and
validates against the same 25 % held-out split:
    Training:   videos/train/run/<train_run_id>/{happy,sad,neutral}/
    Validation: videos/validation/run/<train_run_id>/{happy,sad,neutral}/

The backbone receives 1/10th of the head learning rate during unfreezing to
prevent catastrophic forgetting.

Config versioning:
    Every run auto-saves its full config to trainer/finetune_configs/<run_id>.yaml.
    Use --config to replay a previous run's settings, with optional CLI overrides.
    Use compare_finetune_runs.py to list and diff saved configurations.

Usage:
    # Full fine-tuning run (config auto-saved)
    python -m trainer.train_variant2 \\
        --checkpoint .../variant_1/var1_run_0106/best_model.pth \\
        --train-run-id run_0106 \\
        --run-id var2_run_0107 \\
        --epochs 30 --lr 1e-4 --label-smoothing 0.10

    # Replay a saved config with one override
    python -m trainer.train_variant2 \\
        --config trainer/finetune_configs/var2_run_0106.yaml \\
        --run-id var2_run_0108 \\
        --dropout 0.5

    # Compare runs
    python -m trainer.compare_finetune_runs
    python -m trainer.compare_finetune_runs --diff var2_run_0106 var2_run_0107
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import torch
import yaml

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


CONFIG_DIR = Path(__file__).resolve().parent / "finetune_configs"


def _resolve_val_dir(train_run_id: str) -> str:
    """Build the run-scoped validation directory path from the V1 training run."""
    return f"{VALIDATION_ROOT}/{train_run_id}"


def _save_run_config(run_id: str, args: argparse.Namespace, config: Any) -> Path:
    """Persist the full config for this run as a YAML file for reproducibility."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CONFIG_DIR / f"{run_id}.yaml"

    payload: Dict[str, Any] = {
        "run_id": run_id,
        "train_run_id": args.train_run_id,
        "checkpoint": str(args.checkpoint),
        "created": datetime.now(timezone.utc).isoformat(),
        "model": {
            "backbone": config.model.backbone,
            "pretrained_weights": config.model.pretrained_weights,
            "num_classes": config.model.num_classes,
            "input_size": config.model.input_size,
            "dropout_rate": config.model.dropout_rate,
            "freeze_backbone_epochs": config.model.freeze_backbone_epochs,
            "unfreeze_layers": list(config.model.unfreeze_layers),
        },
        "data": {
            "batch_size": config.data.batch_size,
            "num_workers": config.data.num_workers,
            "frame_sampling": config.data.frame_sampling,
            "mixup_alpha": config.data.mixup_alpha,
            "mixup_probability": config.data.mixup_probability,
        },
        "num_epochs": config.num_epochs,
        "learning_rate": config.learning_rate,
        "weight_decay": config.weight_decay,
        "lr_scheduler": config.lr_scheduler,
        "warmup_epochs": config.warmup_epochs,
        "min_lr": config.min_lr,
        "label_smoothing": config.label_smoothing,
        "gradient_clip_norm": config.gradient_clip_norm,
        "early_stopping_enabled": config.early_stopping_enabled,
        "patience": config.patience,
        "min_delta": config.min_delta,
        "monitor_metric": config.monitor_metric,
        "mixed_precision": config.mixed_precision,
        "seed": config.seed,
        "deterministic": config.deterministic,
    }

    with open(out_path, "w") as f:
        yaml.dump(payload, f, default_flow_style=False, sort_keys=False)
    logger.info("Saved run config → %s", out_path)
    return out_path


def _load_config_from_yaml(yaml_path: Path) -> Dict[str, Any]:
    """Load a previously saved config YAML and return it as a dict."""
    with open(yaml_path) as f:
        return yaml.safe_load(f) or {}


def build_config(
    epochs: int,
    lr: float,
    freeze_epochs: int,
    unfreeze_layers: list[str],
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
            affectnet_train_dir=affectnet_train_dir,
            real_samples_per_class=real_samples_per_class,
            test_manifest_path=test_manifest_path,
        ),
        num_epochs=epochs,
        learning_rate=lr,
        weight_decay=1e-4,
        lr_scheduler="cosine",
        warmup_epochs=2,
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

    # --- Config replay (takes priority over individual flags) ---------------
    parser.add_argument(
        "--config",
        default=None,
        help=(
            "Path to a saved YAML config (e.g. trainer/finetune_configs/var2_run_0106.yaml). "
            "Replays the exact hyperparameters from a previous run. "
            "Individual CLI flags still override the loaded values."
        ),
    )

    # --- Core identity ------------------------------------------------------
    parser.add_argument(
        "--checkpoint",
        default=None,
        help=(
            "Path to a Variant 1 best_model.pth "
            "(e.g. .../checkpoints/variant_1/var1_run_0102/best_model.pth)"
        ),
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Identifier for this Variant 2 run, used for checkpoint directory naming",
    )
    parser.add_argument(
        "--train-run-id",
        default=None,
        dest="train_run_id",
        help=(
            "Variant 1 training run ID whose data to fine-tune on "
            "(e.g. run_0105). Resolves training data at "
            "train/run/<train_run_id>/ and validation at "
            "validation/run/<train_run_id>/."
        ),
    )

    # --- Hyperparameters (CLI overrides config YAML when both given) --------
    parser.add_argument("--epochs", type=int, default=None,
                        help="Total training epochs (default from config or 5)")
    parser.add_argument("--lr", type=float, default=None,
                        help="Peak learning rate; backbone receives lr/10 after unfreezing")
    parser.add_argument("--freeze-epochs", type=int, default=None, dest="freeze_epochs",
                        help="Epochs to keep backbone frozen before unfreezing")
    parser.add_argument("--unfreeze-layers", default=None, dest="unfreeze_layers",
                        help="Comma-separated backbone layer names to unfreeze in Phase 2")
    parser.add_argument("--label-smoothing", type=float, default=None, dest="label_smoothing",
                        help="Label smoothing factor (0.0–0.3)")
    parser.add_argument("--dropout", type=float, default=None,
                        help="Dropout rate for classification head (0.0–0.7)")
    parser.add_argument("--weight-decay", type=float, default=None, dest="weight_decay",
                        help="L2 regularization weight decay")
    parser.add_argument("--warmup-epochs", type=int, default=None, dest="warmup_epochs",
                        help="LR warmup epochs")
    parser.add_argument("--mixup-alpha", type=float, default=None, dest="mixup_alpha",
                        help="Mixup alpha (0 disables)")
    parser.add_argument("--mixup-prob", type=float, default=None, dest="mixup_prob",
                        help="Mixup probability per batch")
    parser.add_argument("--batch-size", type=int, default=None, dest="batch_size",
                        help="Training batch size")
    parser.add_argument("--patience", type=int, default=None,
                        help="Early stopping patience")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")

    parser.add_argument(
        "--val-dir", default=None, dest="val_dir",
        help="Override validation directory with class subdirs (happy/, sad/, neutral/).",
    )
    parser.add_argument(
        "--no-save-config", action="store_true", dest="no_save_config",
        help="Skip auto-saving the config YAML for this run.",
    )

    # --- Mixed-domain training ------------------------------------------------
    parser.add_argument(
        "--mix-real", action="store_true", dest="mix_real",
        help="Combine synthetic frames with real AffectNet images during training.",
    )
    parser.add_argument(
        "--real-samples-per-class", type=int, default=5000,
        dest="real_samples_per_class",
        help="Number of real AffectNet images per class (default: 5000).",
    )
    parser.add_argument(
        "--affectnet-train-dir", default=AFFECTNET_TRAIN_DIR,
        dest="affectnet_train_dir",
        help="Path to AffectNet human-annotated training set.",
    )
    parser.add_argument(
        "--test-manifest", default="", dest="test_manifest",
        help=(
            "Path to test-labels JSONL manifest. AffectNet IDs in this file "
            "are excluded from mixed-domain training to prevent data leakage. "
            "Auto-resolved to the default test_dataset_01 manifest when "
            "--mix-real is set and this flag is omitted."
        ),
    )
    args = parser.parse_args()

    # --- Merge: config YAML → defaults → CLI overrides ----------------------
    cfg_yaml: Dict[str, Any] = {}
    if args.config:
        cfg_path = Path(args.config)
        if not cfg_path.exists():
            logger.error("Config file not found: %s", cfg_path)
            return 1
        cfg_yaml = _load_config_from_yaml(cfg_path)
        logger.info("Loaded config from %s", cfg_path)

    def _resolve(cli_val: Any, yaml_key: str, nested_key: str | None = None, default: Any = None) -> Any:
        """CLI flag > YAML value > hardcoded default."""
        if cli_val is not None:
            return cli_val
        if nested_key:
            section = cfg_yaml.get(yaml_key, {})
            if isinstance(section, dict) and nested_key in section:
                return section[nested_key]
        elif yaml_key in cfg_yaml:
            return cfg_yaml[yaml_key]
        return default

    checkpoint_str = _resolve(args.checkpoint, "checkpoint")
    if not checkpoint_str:
        logger.error("--checkpoint is required (or provide via --config YAML)")
        return 1
    checkpoint_path = Path(checkpoint_str)
    if not checkpoint_path.exists():
        logger.error("Checkpoint not found: %s", checkpoint_path)
        return 1

    train_run_id = _resolve(args.train_run_id, "train_run_id")
    if not train_run_id:
        logger.error("--train-run-id is required (or provide via --config YAML)")
        return 1

    run_id = _resolve(args.run_id, "run_id", default="var2_0001")
    epochs = _resolve(args.epochs, "num_epochs", default=5)
    lr = _resolve(args.lr, "learning_rate", default=3e-4)
    freeze_epochs = _resolve(args.freeze_epochs, "model", "freeze_backbone_epochs", default=5)
    label_smoothing = _resolve(args.label_smoothing, "label_smoothing", default=0.15)
    dropout = _resolve(args.dropout, "model", "dropout_rate", default=0.3)
    weight_decay = _resolve(args.weight_decay, "weight_decay", default=1e-4)
    warmup_epochs = _resolve(args.warmup_epochs, "warmup_epochs", default=2)
    mixup_alpha = _resolve(args.mixup_alpha, "data", "mixup_alpha", default=0.2)
    mixup_prob = _resolve(args.mixup_prob, "data", "mixup_probability", default=0.3)
    batch_size = _resolve(args.batch_size, "data", "batch_size", default=32)
    patience = _resolve(args.patience, "patience", default=10)
    seed = _resolve(args.seed, "seed", default=42)

    unfreeze_raw = args.unfreeze_layers
    if unfreeze_raw:
        unfreeze_layers = [lyr.strip() for lyr in unfreeze_raw.split(",") if lyr.strip()]
    else:
        unfreeze_layers = _resolve(None, "model", "unfreeze_layers", default=DEFAULT_UNFREEZE_LAYERS)

    save_dir = f"{BASE_CHECKPOINT_DIR}/variant_2/{run_id}"
    val_dir = args.val_dir if args.val_dir else _resolve_val_dir(train_run_id)

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
        epochs=epochs,
        lr=lr,
        freeze_epochs=freeze_epochs,
        unfreeze_layers=unfreeze_layers,
        checkpoint_dir=save_dir,
        val_dir=val_dir,
        affectnet_train_dir=affectnet_dir,
        real_samples_per_class=real_per_class,
        test_manifest_path=test_manifest,
    )
    # Apply CLI-overrideable hyperparams not covered by build_config args
    config.label_smoothing = label_smoothing
    config.model.dropout_rate = dropout
    config.weight_decay = weight_decay
    config.warmup_epochs = warmup_epochs
    config.data.mixup_alpha = mixup_alpha
    config.data.mixup_probability = mixup_prob
    config.data.batch_size = batch_size
    config.patience = patience
    config.seed = seed

    # Persist args so _save_run_config can access them
    args.checkpoint = str(checkpoint_path)
    args.train_run_id = train_run_id

    # --- Auto-save config YAML ----------------------------------------------
    if not args.no_save_config:
        _save_run_config(run_id, args, config)

    logger.info("=" * 60)
    if args.mix_real:
        logger.info("Variant 2 Fine-Tuning — MIXED-DOMAIN (synthetic + real)")
    else:
        logger.info("Variant 2 Fine-Tuning")
    logger.info(f"  Source checkpoint:  {checkpoint_path}")
    logger.info(f"  Run ID:             {run_id}")
    logger.info(f"  Train run ID:       {train_run_id}")
    logger.info(f"  Epochs: {epochs}  LR: {lr}")
    logger.info(f"  Freeze epochs: {freeze_epochs}  →  Unfreeze: {unfreeze_layers}")
    logger.info(f"  Label smoothing: {label_smoothing}  Dropout: {dropout}")
    if args.mix_real:
        logger.info(f"  + Real data: {affectnet_dir} ({real_per_class}/class)")
        if test_manifest:
            logger.info(f"  Exclude:     {Path(test_manifest).name} (leakage prevention)")
    logger.info(f"  Val data:    {val_dir}")
    logger.info(f"  Checkpoint:  {save_dir}")
    if args.config:
        logger.info(f"  Config source: {args.config}")
    logger.info("=" * 60)

    trainer = EfficientNetTrainer(config)
    _load_weights_only(trainer, str(checkpoint_path))

    results = trainer.train(run_id=train_run_id)

    save_training_artifacts(
        results=results,
        save_name=run_id,
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
