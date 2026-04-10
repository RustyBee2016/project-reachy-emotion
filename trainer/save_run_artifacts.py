"""
Shared utility: write run artifacts after a terminal training run completes.

Writes two outputs:
1. External media (full artifacts):
   /media/.../results/train/<save_name>/gate_a.json

2. Project repo (dashboard payload):
   {project_root}/stats/results/runs/train/<save_name>.json

The dashboard (06_Dashboard.py) reads from #2.
The mapping from local results → project payload is performed here after each run.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Gate A thresholds (mirror gate_a_validator.GateAThresholds)
_GATE_THRESHOLDS = {
    "macro_f1": 0.84,
    "balanced_accuracy": 0.85,
    "per_class_f1": 0.75,
    "ece": 0.08,
    "brier": 0.16,
}

_EXTERNAL_RESULTS_ROOT = "/media/rusty_admin/project_data/reachy_emotion/results"


def _gate_gates(gate_results: dict[str, Any], class_names: list[str]) -> dict[str, bool]:
    """Derive per-threshold pass/fail flags from gate_results."""
    details = gate_results.get("gate_a_details", {})
    f1_macro = details.get("f1_macro", 0.0)
    bal_acc = details.get("balanced_accuracy", 0.0)
    per_class = details.get("f1_per_class", [])
    ece = details.get("ece", 1.0)
    brier = details.get("brier", 1.0)

    per_class_pass = all(f >= _GATE_THRESHOLDS["per_class_f1"] for f in per_class) if per_class else False
    return {
        "macro_f1": f1_macro >= _GATE_THRESHOLDS["macro_f1"],
        "balanced_accuracy": bal_acc >= _GATE_THRESHOLDS["balanced_accuracy"],
        "per_class_f1": per_class_pass,
        "ece": ece <= _GATE_THRESHOLDS["ece"],
        "brier": brier <= _GATE_THRESHOLDS["brier"],
    }


def _gate_metrics(gate_results: dict[str, Any], class_names: list[str]) -> dict[str, Any]:
    """Build the gate_a_metrics dict compatible with the dashboard payload format."""
    # Extract from nested gate_a_details structure returned by trainer.train()
    details = gate_results.get("gate_a_details", {})
    per_class = details.get("f1_per_class", [])
    
    metrics: dict[str, Any] = {
        "f1_macro": details.get("f1_macro"),
        "balanced_accuracy": details.get("balanced_accuracy"),
        "ece": details.get("ece"),
        "brier": details.get("brier"),
        # Fields not available from train() — set to 0.0 for dashboard compatibility
        "accuracy": 0.0,
        "precision_macro": 0.0,
        "recall_macro": 0.0,
        "confusion_matrix": [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
        "mce": 0.0,
    }
    for i, cls in enumerate(class_names):
        val = per_class[i] if i < len(per_class) else 0.0
        metrics[f"f1_class_{i}"] = val
        metrics[f"f1_{cls}"] = val
    return metrics


def save_training_artifacts(
    *,
    results: dict[str, Any],
    save_name: str,
    variant: str,
    class_names: list[str],
    project_root: Path,
    external_results_root: str = _EXTERNAL_RESULTS_ROOT,
) -> None:
    """Write gate_a.json (external) and dashboard payload JSON (project repo).

    Args:
        results:              Dict returned by EfficientNetTrainer.train()
        save_name:            Checkpoint directory name, used as the run ID in
                              results paths (e.g. "var1_run_0102", "var2_0001")
        variant:              Model variant label (e.g. "variant_1", "variant_2")
        class_names:          Ordered list of class names, e.g. ["happy", "sad", "neutral"]
        project_root:         Absolute Path to the project repo root
        external_results_root: Root for external media results storage
    """
    gate_results = results.get("gate_results", {})
    status = results.get("status", "unknown")
    best_metric = results.get("best_metric", 0.0)
    timestamp = datetime.now(timezone.utc).isoformat()

    # ── 1. External: gate_a.json ──────────────────────────────────────────────
    ext_dir = Path(external_results_root) / "train" / save_name
    ext_dir.mkdir(parents=True, exist_ok=True)
    gate_a_path = ext_dir / "gate_a.json"

    gate_a_payload = {
        "run_id": save_name,
        "variant": variant,
        "status": status,
        "best_metric": float(best_metric),
        "timestamp": timestamp,
        "gate_a_passed": bool(gate_results.get("gate_a", False)),
        "metrics": {
            "f1_macro": gate_results.get("f1_macro"),
            "balanced_accuracy": gate_results.get("balanced_accuracy"),
            "f1_per_class": gate_results.get("f1_per_class"),
            "ece": gate_results.get("ece"),
            "brier": gate_results.get("brier"),
        },
        "gate_a_details": gate_results.get("gate_a_details", {}),
    }
    gate_a_path.write_text(json.dumps(gate_a_payload, indent=2, default=str), encoding="utf-8")
    logger.info("Saved gate_a.json → %s", gate_a_path)

    # ── 2. Project repo: dashboard payload JSON ───────────────────────────────
    dashboard_dir = project_root / "stats" / "results" / "runs" / "train"
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    dashboard_path = dashboard_dir / f"{save_name}.json"

    dashboard_payload = {
        "run_id": save_name,
        "run_type": "train",
        "model_variant": variant,
        "status": status,
        "best_metric": float(best_metric),
        "timestamp": timestamp,
        "artifacts_root": str(ext_dir),
        "gate_a_metrics": _gate_metrics(gate_results, class_names),
        "gate_a_gates": _gate_gates(gate_results, class_names),
    }
    dashboard_path.write_text(json.dumps(dashboard_payload, indent=2, default=str), encoding="utf-8")
    logger.info("Saved dashboard payload → %s", dashboard_path)
