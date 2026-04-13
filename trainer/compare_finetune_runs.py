#!/usr/bin/env python3
"""Compare Variant 2 fine-tuning runs side-by-side.

Lists all saved configs in trainer/finetune_configs/ and pairs them with
their training results from stats/results/runs/train/.

Usage:
    # List all runs (compact table)
    python -m trainer.compare_finetune_runs

    # Verbose: show full config diffs between two runs
    python -m trainer.compare_finetune_runs --diff var2_run_0106 var2_run_0107

    # Filter by Gate A status
    python -m trainer.compare_finetune_runs --gate-passed
    python -m trainer.compare_finetune_runs --gate-failed
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "trainer" / "finetune_configs"
RESULTS_DIR = PROJECT_ROOT / "stats" / "results" / "runs" / "train"

# Metrics to display in the compact table
TABLE_METRICS = [
    ("f1_macro", "F1 Macro", ".4f"),
    ("balanced_accuracy", "Bal Acc", ".4f"),
    ("ece", "ECE", ".4f"),
    ("brier", "Brier", ".4f"),
    ("accuracy", "Accuracy", ".4f"),
    ("mce", "MCE", ".4f"),
]

# Key hyperparameters to show in the compact table
TABLE_HPARAMS = [
    "learning_rate",
    "label_smoothing",
    "model.dropout_rate",
    "model.freeze_backbone_epochs",
    "num_epochs",
    "warmup_epochs",
    "data.mixup_alpha",
]


def _load_yaml(path: Path) -> Dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def _get_nested(d: Dict[str, Any], dotted_key: str) -> Any:
    """Retrieve a value from a nested dict using dot notation."""
    keys = dotted_key.split(".")
    current = d
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k)
        else:
            return None
    return current


def _collect_runs() -> List[Dict[str, Any]]:
    """Collect all config+result pairs."""
    runs = []
    if not CONFIG_DIR.exists():
        return runs

    for cfg_path in sorted(CONFIG_DIR.glob("*.yaml")):
        run_id = cfg_path.stem
        config = _load_yaml(cfg_path)
        result_path = RESULTS_DIR / f"{run_id}.json"
        result = _load_json(result_path) if result_path.exists() else None
        runs.append({
            "run_id": run_id,
            "config_path": cfg_path,
            "config": config,
            "result_path": result_path if result_path.exists() else None,
            "result": result,
        })
    return runs


def _format_val(val: Any, fmt: str = "") -> str:
    if val is None:
        return "—"
    if fmt and isinstance(val, (int, float)):
        return f"{val:{fmt}}"
    return str(val)


def _print_table(runs: List[Dict[str, Any]]) -> None:
    """Print a compact comparison table."""
    if not runs:
        print("No fine-tuning configs found in trainer/finetune_configs/")
        return

    # Header
    id_width = max(len(r["run_id"]) for r in runs)
    id_width = max(id_width, 10)

    # Build rows
    header_parts = [f"{'Run ID':<{id_width}}", "Gate A"]
    for _, label, _ in TABLE_METRICS:
        header_parts.append(f"{label:>8}")
    header_parts.append("  | ")
    for hp in TABLE_HPARAMS:
        short = hp.split(".")[-1][:12]
        header_parts.append(f"{short:>12}")

    header = "  ".join(header_parts)
    print(header)
    print("─" * len(header))

    for run in runs:
        result = run.get("result")
        config = run.get("config", {})
        metrics = result.get("gate_a_metrics", {}) if result else {}
        gates = result.get("gate_a_gates", {}) if result else {}

        gate_passed = all(gates.values()) if gates else None
        gate_str = "PASS" if gate_passed else ("FAIL" if gate_passed is not None else " — ")

        parts = [f"{run['run_id']:<{id_width}}", f"{gate_str:>6}"]
        for key, _, fmt in TABLE_METRICS:
            parts.append(f"{_format_val(metrics.get(key), fmt):>8}")
        parts.append("  | ")
        for hp in TABLE_HPARAMS:
            val = _get_nested(config, hp)
            if isinstance(val, float) and val < 0.01:
                parts.append(f"{val:>12.1e}")
            elif isinstance(val, float):
                parts.append(f"{val:>12.3f}")
            else:
                parts.append(f"{str(val) if val is not None else '—':>12}")

        print("  ".join(parts))


def _print_diff(runs: List[Dict[str, Any]], id_a: str, id_b: str) -> None:
    """Show config differences between two runs."""
    run_a = next((r for r in runs if r["run_id"] == id_a), None)
    run_b = next((r for r in runs if r["run_id"] == id_b), None)
    if not run_a:
        print(f"Config not found: {id_a}")
        return
    if not run_b:
        print(f"Config not found: {id_b}")
        return

    cfg_a = run_a["config"]
    cfg_b = run_b["config"]

    print(f"\n{'Parameter':<35} {id_a:>20} {id_b:>20}  Change")
    print("─" * 100)

    def _compare(a: Dict, b: Dict, prefix: str = "") -> None:
        all_keys = sorted(set(list(a.keys()) + list(b.keys())))
        for k in all_keys:
            full_key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
            va = a.get(k)
            vb = b.get(k)
            if isinstance(va, dict) and isinstance(vb, dict):
                _compare(va, vb, full_key)
            elif va != vb:
                sa = _format_val(va)
                sb = _format_val(vb)
                marker = " ◀ changed"
                print(f"  {full_key:<33} {sa:>20} {sb:>20}{marker}")

    _compare(cfg_a, cfg_b)

    # Show results comparison
    res_a = run_a.get("result", {}).get("gate_a_metrics", {})
    res_b = run_b.get("result", {}).get("gate_a_metrics", {})
    if res_a or res_b:
        print(f"\n{'Metric':<35} {id_a:>20} {id_b:>20}  Delta")
        print("─" * 100)
        for key, label, fmt in TABLE_METRICS:
            va = res_a.get(key)
            vb = res_b.get(key)
            sa = _format_val(va, fmt)
            sb = _format_val(vb, fmt)
            delta = ""
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                d = vb - va
                arrow = "↑" if d > 0 else "↓" if d < 0 else "="
                delta = f"  {arrow} {abs(d):{fmt}}"
            print(f"  {label:<33} {sa:>20} {sb:>20}{delta}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare Variant 2 fine-tuning runs"
    )
    parser.add_argument(
        "--diff",
        nargs=2,
        metavar=("RUN_A", "RUN_B"),
        help="Show config differences between two run IDs",
    )
    parser.add_argument(
        "--gate-passed",
        action="store_true",
        dest="gate_passed",
        help="Only show runs that passed Gate A",
    )
    parser.add_argument(
        "--gate-failed",
        action="store_true",
        dest="gate_failed",
        help="Only show runs that failed Gate A",
    )
    args = parser.parse_args()

    runs = _collect_runs()

    if args.gate_passed:
        runs = [
            r for r in runs
            if r.get("result") and all(r["result"].get("gate_a_gates", {}).values())
        ]
    elif args.gate_failed:
        runs = [
            r for r in runs
            if r.get("result") and not all(r["result"].get("gate_a_gates", {}).values())
        ]

    if args.diff:
        all_runs = _collect_runs()  # unfiltered for diff
        _print_diff(all_runs, args.diff[0], args.diff[1])
    else:
        _print_table(runs)

    return 0


if __name__ == "__main__":
    sys.exit(main())
