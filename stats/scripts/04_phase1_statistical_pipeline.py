#!/usr/bin/env python3
"""
Phase 1 statistical pipeline runner (3-class ready).

Inputs:
- predictions npz (required): y_true, y_pred, optional y_prob
- optional base predictions npz for model-shift tests
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from trainer.fer_finetune.evaluate import (
    compute_calibration_metrics,
    compute_confusion_matrix,
    compute_metrics,
)


def _load_predictions(path: Path) -> tuple[np.ndarray, np.ndarray, Optional[np.ndarray], List[str]]:
    payload = np.load(path, allow_pickle=True)
    y_true = payload["y_true"]
    y_pred = payload["y_pred"]
    y_prob = payload["y_prob"] if "y_prob" in payload.files else None
    class_names = [str(x) for x in payload["class_names"].tolist()] if "class_names" in payload.files else ["happy", "sad", "neutral"]
    return y_true, y_pred, y_prob, class_names


def _quality_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: Optional[np.ndarray], class_names: List[str]) -> Dict[str, object]:
    result = compute_metrics(y_true.tolist(), y_pred.tolist(), class_names=class_names)
    if y_prob is not None:
        result.update(compute_calibration_metrics(y_true.tolist(), y_prob))
    result["confusion"] = compute_confusion_matrix(y_true.tolist(), y_pred.tolist(), class_names)
    return result


def _prediction_shift(base_pred: np.ndarray, finetuned_pred: np.ndarray, class_names: List[str]) -> Dict[str, object]:
    n_classes = len(class_names)
    table = np.zeros((n_classes, n_classes), dtype=int)
    for b, f in zip(base_pred, finetuned_pred):
        table[int(b), int(f)] += 1
    base_marginal = table.sum(axis=1).tolist()
    ft_marginal = table.sum(axis=0).tolist()
    delta = [int(ft) - int(base) for base, ft in zip(base_marginal, ft_marginal)]
    return {
        "contingency_table": table.tolist(),
        "base_marginal": base_marginal,
        "finetuned_marginal": ft_marginal,
        "marginal_delta": {class_names[i]: delta[i] for i in range(n_classes)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run phase1 statistical pipeline")
    parser.add_argument("--predictions", required=True, help="Path to fine-tuned predictions npz")
    parser.add_argument("--base-predictions", help="Optional baseline predictions npz")
    parser.add_argument("--output", default="stats/results/phase1_stats_pipeline.json")
    args = parser.parse_args()

    y_true, y_pred, y_prob, class_names = _load_predictions(Path(args.predictions))
    output: Dict[str, object] = {
        "class_names": class_names,
        "quality_metrics": _quality_metrics(y_true, y_pred, y_prob, class_names),
    }

    if args.base_predictions:
        _, base_pred, _, base_classes = _load_predictions(Path(args.base_predictions))
        if base_classes != class_names:
            raise SystemExit(f"Class mismatch between base {base_classes} and finetuned {class_names}")
        output["prediction_shift"] = _prediction_shift(base_pred, y_pred, class_names)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2))
    print(json.dumps({"output": str(out_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
