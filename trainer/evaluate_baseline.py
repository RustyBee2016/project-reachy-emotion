#!/usr/bin/env python3
"""
Evaluate the raw HSEmotion 8-class model on the 3-class test dataset.

This provides the **base model** baseline: how well does the pre-trained
HSEmotion enet_b0_8_best_vgaf perform on our 3-class task (happy, sad,
neutral) WITHOUT any fine-tuning on synthetic data.

The script:
  1. Loads the original 8-class HSEmotion model (NOT our 3-class head)
  2. Runs inference on the fixed test dataset
  3. Extracts logits for the 3 relevant classes (happy=4, neutral=5, sad=6)
  4. Remaps to our class ordering [happy, sad, neutral]
  5. Computes full Gate A metrics + confusion matrix
  6. Writes dashboard-compatible JSON to stats/results/runs/test/

Usage (from project root on Ubuntu 1):
    export REACHY_TEST_DATA_DIR=/media/rusty_admin/project_data/reachy_emotion/videos/test/affectnet_test_dataset
    python -m trainer.evaluate_baseline --run-id base_test_001

Output:
    stats/results/runs/test/base_test_001.json  (dashboard payload)
    /media/.../results/test/base_test_001/gate_a.json  (full report)
    /media/.../results/test/base_test_001/predictions.npz
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import torch
import torch.nn.functional as F

from trainer.fer_finetune.dataset import EmotionDataset, get_val_transforms
from trainer.fer_finetune.evaluate import compute_calibration_metrics, compute_metrics
from trainer.gate_a_validator import GateAThresholds, evaluate_predictions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# HSEmotion 8-class indices that map to our 3-class task.
# HSEmotion order: anger(0), contempt(1), disgust(2), fear(3),
#                  happy(4), neutral(5), sad(6), surprise(7)
# Our order:       happy(0), sad(1), neutral(2)
_HSEMOTION_INDICES = [4, 6, 5]  # [happy, sad, neutral] in HSEmotion indexing

_EXTERNAL_RESULTS_ROOT = "/media/rusty_admin/project_data/reachy_emotion/results"


def _load_hsemotion_8class(device: str = "cuda") -> torch.nn.Module:
    """Load the original 8-class HSEmotion model (no head replacement)."""
    from hsemotion.facial_emotions import HSEmotionRecognizer

    logger.info("Loading raw HSEmotion enet_b0_8_best_vgaf (8-class)")
    recognizer = HSEmotionRecognizer(model_name="enet_b0_8_best_vgaf")
    model = recognizer.model
    model.to(device)
    model.eval()
    logger.info("HSEmotion 8-class model loaded successfully")
    return model


def _evaluate_on_test(
    model: torch.nn.Module,
    test_dir: str,
    class_names: List[str],
    input_size: int = 224,
    batch_size: int = 64,
    device: str = "cuda",
) -> Dict[str, np.ndarray]:
    """Run inference and remap 8-class outputs to 3-class."""
    from torch.utils.data import DataLoader

    dataset = EmotionDataset(
        data_dir=test_dir,
        split="",
        transform=get_val_transforms(input_size),
        class_names=class_names,
        frame_sampling="middle",
    )
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    y_true_list: List[int] = []
    y_pred_list: List[int] = []
    y_prob_list: List[np.ndarray] = []

    logger.info(f"Evaluating {len(dataset)} samples from {test_dir}")

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            outputs = model(images)

            # outputs may be a dict or raw tensor depending on hsemotion version
            if isinstance(outputs, dict):
                logits_8 = outputs.get("logits", outputs.get("output"))
            else:
                logits_8 = outputs

            # Extract the 3 relevant logits and remap
            logits_3 = logits_8[:, _HSEMOTION_INDICES]  # [B, 3]
            probs_3 = F.softmax(logits_3, dim=1)
            preds_3 = torch.argmax(probs_3, dim=1)

            y_true_list.extend(labels.cpu().numpy().tolist())
            y_pred_list.extend(preds_3.cpu().numpy().tolist())
            y_prob_list.extend(probs_3.cpu().numpy())

    return {
        "y_true": np.array(y_true_list, dtype=np.int64),
        "y_pred": np.array(y_pred_list, dtype=np.int64),
        "y_prob": np.array(y_prob_list, dtype=np.float32),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate raw HSEmotion base model on 3-class test set"
    )
    parser.add_argument(
        "--run-id",
        default="base_test_001",
        help="Run identifier for output files",
    )
    parser.add_argument(
        "--test-dir",
        default=os.getenv(
            "REACHY_TEST_DATA_DIR",
            "/media/rusty_admin/project_data/reachy_emotion/videos/test/affectnet_test_dataset",
        ),
        help="Path to test dataset with class subdirectories",
    )
    parser.add_argument(
        "--output-dir",
        default=_EXTERNAL_RESULTS_ROOT,
        help="Root for external artifacts",
    )
    parser.add_argument(
        "--dashboard-dir",
        default="stats/results/runs",
        help="Project-repo directory for dashboard JSON payloads",
    )
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--input-size", type=int, default=224)
    args = parser.parse_args()

    class_names = ["happy", "sad", "neutral"]
    device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info("=" * 60)
    logger.info("Base Model Evaluation (HSEmotion 8-class → 3-class)")
    logger.info(f"  Test dir:  {args.test_dir}")
    logger.info(f"  Run ID:    {args.run_id}")
    logger.info(f"  Device:    {device}")
    logger.info("=" * 60)

    # 1. Load raw 8-class model
    model = _load_hsemotion_8class(device=device)

    # 2. Run inference with 8→3 class remapping
    preds = _evaluate_on_test(
        model=model,
        test_dir=args.test_dir,
        class_names=class_names,
        input_size=args.input_size,
        batch_size=args.batch_size,
        device=device,
    )

    # 3. Save predictions.npz
    artifact_dir = Path(args.output_dir) / "test" / args.run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    pred_path = artifact_dir / "predictions.npz"
    np.savez(
        pred_path,
        y_true=preds["y_true"],
        y_pred=preds["y_pred"],
        y_prob=preds["y_prob"],
        class_names=np.array(class_names),
    )
    logger.info(f"Saved predictions → {pred_path}")

    # 4. Gate A evaluation
    gate_report = evaluate_predictions(
        preds["y_true"],
        preds["y_pred"],
        preds["y_prob"],
        class_names,
        GateAThresholds(),
    )
    gate_path = artifact_dir / "gate_a.json"
    gate_path.write_text(json.dumps(gate_report, indent=2, default=str))
    logger.info(f"Saved gate_a.json → {gate_path}")

    # 5. Dashboard payload
    dashboard_dir = Path(args.dashboard_dir) / "test"
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    dashboard_path = dashboard_dir / f"{args.run_id}.json"
    dashboard_payload = {
        "run_id": args.run_id,
        "model_variant": "base",
        "run_type": "test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "description": "HSEmotion enet_b0_8_best_vgaf (8→3 class remap, no fine-tuning)",
        "gate_a_metrics": gate_report.get("metrics", {}),
        "gate_a_gates": gate_report.get("gates", {}),
        "overall_pass": bool(gate_report.get("overall_pass")),
        "artifacts": {
            "predictions_npz": str(pred_path),
            "gate_a_report_json": str(gate_path),
        },
    }
    dashboard_path.write_text(json.dumps(dashboard_payload, indent=2, default=str))
    logger.info(f"Saved dashboard payload → {dashboard_path}")

    # 6. Print summary
    metrics = gate_report.get("metrics", {})
    gates = gate_report.get("gates", {})
    overall = gate_report.get("overall_pass", False)

    logger.info("=" * 60)
    logger.info("BASE MODEL RESULTS")
    logger.info("=" * 60)
    logger.info(f"  Accuracy:          {metrics.get('accuracy', 0):.4f}")
    logger.info(f"  F1 Macro:          {metrics.get('f1_macro', 0):.4f}")
    logger.info(f"  Balanced Accuracy: {metrics.get('balanced_accuracy', 0):.4f}")
    logger.info(f"  Precision Macro:   {metrics.get('precision_macro', 0):.4f}")
    logger.info(f"  Recall Macro:      {metrics.get('recall_macro', 0):.4f}")
    logger.info(f"  ECE:               {metrics.get('ece', 0):.4f}")
    logger.info(f"  Brier:             {metrics.get('brier', 0):.4f}")
    logger.info(f"  MCE:               {metrics.get('mce', 0):.4f}")
    for cn in class_names:
        logger.info(f"  F1 {cn:>8s}:       {metrics.get(f'f1_{cn}', 0):.4f}")
    logger.info(f"  Confusion Matrix:  {metrics.get('confusion_matrix', [])}")
    logger.info(f"  Gate A: {'PASSED' if overall else 'FAILED'}")
    for gate_name, passed in gates.items():
        logger.info(f"    {gate_name}: {'✓' if passed else '✗'}")

    print(
        json.dumps(
            {
                "run_id": args.run_id,
                "dashboard_payload": str(dashboard_path),
                "gate_report": str(gate_path),
                "overall_pass": overall,
                "f1_macro": metrics.get("f1_macro"),
                "balanced_accuracy": metrics.get("balanced_accuracy"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
