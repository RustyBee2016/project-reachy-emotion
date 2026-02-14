#!/usr/bin/env python3
"""
Gate A validation utility for EfficientNet-B0 emotion classifiers.

Supports:
- Evaluation from saved predictions (`.npz`) for CI/statistical workflows
- Optional direct checkpoint evaluation against filesystem test data
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from trainer.fer_finetune.evaluate import compute_calibration_metrics, compute_metrics


@dataclass
class GateAThresholds:
    macro_f1: float = 0.84
    balanced_accuracy: float = 0.85
    per_class_f1: float = 0.75
    per_class_floor: float = 0.70
    ece: float = 0.08
    brier: float = 0.16


def _per_class_f1(metrics: Dict[str, float], class_names: List[str]) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for idx, name in enumerate(class_names):
        key = f"f1_class_{idx}"
        result[name] = float(metrics.get(key, 0.0))
    return result


def evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray],
    class_names: List[str],
    thresholds: GateAThresholds,
) -> Dict[str, object]:
    metrics = compute_metrics(y_true.tolist(), y_pred.tolist(), class_names=class_names)
    if y_prob is not None:
        metrics.update(compute_calibration_metrics(y_true.tolist(), y_prob))

    per_class = _per_class_f1(metrics, class_names)
    per_class_passes = {k: (v >= thresholds.per_class_f1) for k, v in per_class.items()}
    per_class_min = min(per_class.values()) if per_class else 0.0

    gates = {
        "macro_f1": float(metrics.get("f1_macro", 0.0)) >= thresholds.macro_f1,
        "balanced_accuracy": float(metrics.get("balanced_accuracy", 0.0)) >= thresholds.balanced_accuracy,
        "per_class_f1": all(per_class_passes.values()) and per_class_min >= thresholds.per_class_floor,
        "ece": float(metrics.get("ece", 1.0)) <= thresholds.ece,
        "brier": float(metrics.get("brier", 1.0)) <= thresholds.brier,
    }
    overall_pass = all(gates.values())

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "class_names": class_names,
        "thresholds": asdict(thresholds),
        "metrics": metrics,
        "per_class_f1": per_class,
        "gates": gates,
        "overall_pass": overall_pass,
    }


def _load_predictions(path: Path) -> tuple[np.ndarray, np.ndarray, Optional[np.ndarray], List[str]]:
    payload = np.load(path, allow_pickle=True)
    y_true = payload["y_true"]
    y_pred = payload["y_pred"]
    y_prob = payload["y_prob"] if "y_prob" in payload.files else None
    if "class_names" in payload.files:
        class_names = [str(x) for x in payload["class_names"].tolist()]
    else:
        class_names = ["happy", "sad", "neutral"]
    return y_true, y_pred, y_prob, class_names


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Gate A metrics")
    parser.add_argument("--predictions", type=str, help="Path to .npz with y_true/y_pred/y_prob")
    parser.add_argument("--output", type=str, default="stats/results/gate_a_validation.json")
    parser.add_argument("--macro-f1-threshold", type=float, default=0.84)
    parser.add_argument("--balanced-accuracy-threshold", type=float, default=0.85)
    parser.add_argument("--per-class-threshold", type=float, default=0.75)
    parser.add_argument("--per-class-floor", type=float, default=0.70)
    parser.add_argument("--ece-threshold", type=float, default=0.08)
    parser.add_argument("--brier-threshold", type=float, default=0.16)
    args = parser.parse_args()

    if not args.predictions:
        raise SystemExit("--predictions is required in this environment")

    thresholds = GateAThresholds(
        macro_f1=args.macro_f1_threshold,
        balanced_accuracy=args.balanced_accuracy_threshold,
        per_class_f1=args.per_class_threshold,
        per_class_floor=args.per_class_floor,
        ece=args.ece_threshold,
        brier=args.brier_threshold,
    )

    y_true, y_pred, y_prob, class_names = _load_predictions(Path(args.predictions))
    result = evaluate_predictions(y_true, y_pred, y_prob, class_names, thresholds)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2))

    print(json.dumps({"overall_pass": result["overall_pass"], "output": str(out_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
