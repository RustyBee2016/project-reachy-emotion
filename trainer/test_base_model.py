"""
Test the HSEmotion base model (enet_b0_8_best_vgaf) on emotion test sets.

Evaluates the 8-class base model on the 3 target classes (happy, sad, neutral).
Supports two data sources:
  1. AffectNet validation set (default) — per-image JSON annotations
  2. Run-scoped test sets via JSONL manifest (--manifest flag)

Usage:
    # AffectNet validation set (default)
    python -m trainer.test_base_model

    # Run-scoped test set via manifest
    python -m trainer.test_base_model \
        --manifest /media/rusty_admin/project_data/reachy_emotion/videos/manifests/run_0101_test_labels.jsonl \
        --data-root /media/rusty_admin/project_data/reachy_emotion/videos
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

import cv2

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s",
)
logger = logging.getLogger("test_base_model")

AFFECTNET_VAL = Path(
    "/media/rusty_admin/project_data/reachy_emotion/affectnet/consolidated"
    "/AffectNet+/human_annotated/validation_set"
)
IMAGES_DIR = AFFECTNET_VAL / "images"
ANNOTATIONS_DIR = AFFECTNET_VAL / "annotations"

# AffectNet human-label codes for our 3 target classes
TARGET_CODES = {0: "neutral", 1: "happy", 2: "sad"}

# HSEmotion 8-class output indices → project class names
HSEMOTION_IDX = {4: "happy", 5: "neutral", 6: "sad"}
HSEMOTION_TO_TARGET = {4: 1, 5: 0, 6: 2}  # HSEmotion idx → target label idx
TARGET_CLASSES = ["neutral", "happy", "sad"]  # idx 0, 1, 2


CLASS_TO_IDX = {"neutral": 0, "happy": 1, "sad": 2}


def load_affectnet_samples():
    """Load AffectNet validation samples filtered to target classes."""
    samples = []
    for ann_path in sorted(ANNOTATIONS_DIR.glob("*.json")):
        with open(ann_path) as f:
            data = json.load(f)
        code = data["human-label"]
        if code not in TARGET_CODES:
            continue
        img_id = ann_path.stem
        img_path = IMAGES_DIR / f"{img_id}.jpg"
        if not img_path.exists():
            logger.warning(f"Missing image: {img_path}")
            continue
        label_name = TARGET_CODES[code]
        samples.append({
            "img_path": img_path,
            "label_code": code,
            "label_name": label_name,
            "label_idx": CLASS_TO_IDX[label_name],
        })
    return samples


def load_manifest_samples(manifest_path: str, data_root: str):
    """Load test samples from a JSONL labels manifest.

    Each line is a JSON object with at least ``file_path`` (relative to
    *data_root*) and ``label`` (one of happy/sad/neutral).
    """
    root = Path(data_root)
    samples = []
    with open(manifest_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            label_name = entry.get("label", "").strip().lower()
            if label_name not in CLASS_TO_IDX:
                continue
            img_path = root / entry["file_path"]
            if not img_path.exists():
                logger.warning(f"Missing image: {img_path}")
                continue
            samples.append({
                "img_path": img_path,
                "label_code": None,
                "label_name": label_name,
                "label_idx": CLASS_TO_IDX[label_name],
            })
    return samples


def main():
    parser = argparse.ArgumentParser(description="Test HSEmotion base model")
    parser.add_argument("--device", default="cuda", choices=["cpu", "cuda"])
    parser.add_argument("--manifest", default=None,
                        help="Path to a JSONL test-labels manifest (e.g. run_0101_test_labels.jsonl)")
    parser.add_argument("--data-root",
                        default="/media/rusty_admin/project_data/reachy_emotion/videos",
                        help="Root directory for relative paths in manifest")
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run identifier for saving results (e.g. run_0101). If omitted, results are not saved.",
    )
    parser.add_argument(
        "--output-dir",
        default="/media/rusty_admin/project_data/reachy_emotion/results",
        help="Root for full run artifacts on local media storage.",
    )
    parser.add_argument(
        "--dashboard-dir",
        default="stats/results/runs",
        help="Project-repo directory for dashboard JSON payloads (read by 06_Dashboard.py).",
    )
    args = parser.parse_args()

    # Load samples
    if args.manifest:
        logger.info(f"Loading samples from manifest: {args.manifest}")
        samples = load_manifest_samples(args.manifest, args.data_root)
    else:
        logger.info("Loading AffectNet validation samples (codes 0, 1, 2)...")
        samples = load_affectnet_samples()
    logger.info(f"Loaded {len(samples)} samples")

    class_counts = {}
    for s in samples:
        class_counts[s["label_name"]] = class_counts.get(s["label_name"], 0) + 1
    logger.info(f"Distribution: {class_counts}")

    # Load base model
    logger.info("Loading HSEmotion base model (enet_b0_8_best_vgaf)...")
    from hsemotion.facial_emotions import HSEmotionRecognizer

    fer = HSEmotionRecognizer(model_name="enet_b0_8_best_vgaf", device=args.device)
    logger.info("Model loaded.")

    # Run inference
    y_true = []
    y_pred = []
    y_scores = []
    errors = 0

    for i, sample in enumerate(samples):
        img = cv2.imread(str(sample["img_path"]))
        if img is None:
            errors += 1
            continue

        emotion, scores = fer.predict_emotions(img, logits=True)

        # Extract scores for our 3 target classes from the 8-class output
        target_scores = np.array([scores[5], scores[4], scores[6]])  # neutral, happy, sad
        pred_idx = np.argmax(target_scores)

        y_true.append(sample["label_idx"])
        y_pred.append(pred_idx)
        y_scores.append(target_scores)

        if (i + 1) % 250 == 0:
            logger.info(f"  Processed {i + 1}/{len(samples)}")

    logger.info(f"Inference complete. {errors} read errors.")

    # Compute metrics
    from trainer.fer_finetune.evaluate import (
        compute_metrics,
        compute_calibration_metrics,
        generate_report,
    )

    y_scores_arr = np.array(y_scores)
    # Convert logits to probabilities via softmax
    exp_scores = np.exp(y_scores_arr - np.max(y_scores_arr, axis=1, keepdims=True))
    y_probs = exp_scores / exp_scores.sum(axis=1, keepdims=True)

    metrics = compute_metrics(y_true, y_pred, class_names=TARGET_CLASSES)
    cal_metrics = compute_calibration_metrics(y_true, y_probs)
    metrics.update(cal_metrics)

    # Print report
    report = generate_report(metrics)
    print()
    print(report)

    # Per-class detail
    print("\nPER-CLASS DETAIL")
    print("-" * 40)
    for i, name in enumerate(TARGET_CLASSES):
        f1 = metrics.get(f"f1_{name}", metrics.get(f"f1_class_{i}", 0))
        count = sum(1 for t in y_true if t == i)
        correct = sum(1 for t, p in zip(y_true, y_pred) if t == i and p == i)
        print(f"  {name:>8}: F1={f1:.4f}  ({correct}/{count} correct)")

    print(f"\nSamples: {len(y_true)} | Errors: {errors}")

    if args.run_id:
        _save_results(
            run_id=args.run_id,
            output_dir=args.output_dir,
            dashboard_dir=args.dashboard_dir,
            y_true=y_true,
            y_pred=y_pred,
            y_probs=y_probs,
            metrics=metrics,
        )

    return 0


def _save_results(
    *,
    run_id: str,
    output_dir: str,
    dashboard_dir: str,
    y_true: list,
    y_pred: list,
    y_probs,
    metrics: dict,
) -> None:
    """Save predictions, Gate A report, and dashboard payload for a base-model test run."""
    from trainer.gate_a_validator import GateAThresholds, evaluate_predictions

    artifact_dir = Path(output_dir) / "test" / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    pred_path = artifact_dir / "predictions.npz"
    np.savez(
        pred_path,
        y_true=np.array(y_true, dtype=np.int64),
        y_pred=np.array(y_pred, dtype=np.int64),
        y_prob=y_probs,
        class_names=np.array(TARGET_CLASSES),
    )
    logger.info("Saved predictions: %s", pred_path)

    gate_report = evaluate_predictions(
        np.array(y_true, dtype=np.int64),
        np.array(y_pred, dtype=np.int64),
        y_probs,
        TARGET_CLASSES,
        GateAThresholds(),
    )
    gate_path = artifact_dir / "gate_a.json"
    gate_path.write_text(json.dumps(gate_report, indent=2))
    logger.info("Saved Gate A report: %s", gate_path)

    dashboard_root = Path(dashboard_dir) / "base_model_test"
    dashboard_root.mkdir(parents=True, exist_ok=True)
    dashboard_payload = {
        "run_id": run_id,
        "model_variant": "base_model",
        "run_type": "base_model_test",
        "gate_a_metrics": gate_report.get("metrics", {}),
        "gate_a_gates": gate_report.get("gates", {}),
        "overall_pass": bool(gate_report.get("overall_pass")),
        "artifacts": {
            "predictions_npz": str(pred_path),
            "gate_a_report_json": str(gate_path),
        },
    }
    dashboard_path = dashboard_root / f"{run_id}.json"
    dashboard_path.write_text(json.dumps(dashboard_payload, indent=2))
    logger.info("Saved dashboard payload: %s", dashboard_path)


if __name__ == "__main__":
    sys.exit(main())
