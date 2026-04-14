#!/usr/bin/env python3
"""Compare a Variant 2 run against the sweep's best model.

Reads the optimized parameters from stats/results/sweep/best_model.json
and compares them against a specified run's results. Useful for checking
whether a new manual or automated run beats the current champion.

Usage:
    # Compare a specific run against the sweep best
    python -m trainer.compare_to_best var2_run_0108

    # Compare the latest Variant 2 run
    python -m trainer.compare_to_best --latest

    # Show the current best model details
    python -m trainer.compare_to_best --show-best
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SWEEP_DIR = PROJECT_ROOT / "stats" / "results" / "sweep"
BEST_MODEL_PATH = SWEEP_DIR / "best_model.json"
LEADERBOARD_PATH = SWEEP_DIR / "leaderboard.json"
TRAIN_RESULTS_DIR = PROJECT_ROOT / "stats" / "results" / "runs" / "train"
TEST_RESULTS_DIR = PROJECT_ROOT / "stats" / "results" / "runs" / "test"

METRICS_TO_COMPARE = [
    ("f1_macro", "F1 Macro", ".4f", "higher"),
    ("balanced_accuracy", "Bal Acc", ".4f", "higher"),
    ("ece", "ECE", ".4f", "lower"),
    ("brier", "Brier", ".4f", "lower"),
    ("mce", "MCE", ".4f", "lower"),
    ("f1_happy", "F1 Happy", ".4f", "higher"),
    ("f1_sad", "F1 Sad", ".4f", "higher"),
    ("f1_neutral", "F1 Neutral", ".4f", "higher"),
]

GATE_A_THRESHOLDS = {
    "f1_macro": (">=", 0.84),
    "balanced_accuracy": (">=", 0.85),
    "ece": ("<=", 0.12),
    "brier": ("<=", 0.16),
}


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _find_latest_var2() -> Optional[str]:
    """Find the most recent var2_* training result."""
    if not TRAIN_RESULTS_DIR.exists():
        return None
    var2_files = sorted(
        TRAIN_RESULTS_DIR.glob("var2_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return var2_files[0].stem if var2_files else None


def _format_delta(val_new: float, val_best: float, direction: str) -> str:
    """Format a delta with arrow indicating improvement."""
    delta = val_new - val_best
    if abs(delta) < 1e-6:
        return "  = "
    if direction == "higher":
        arrow = "\u2191" if delta > 0 else "\u2193"
        improved = delta > 0
    else:
        arrow = "\u2193" if delta < 0 else "\u2191"
        improved = delta < 0
    sign = "+" if delta > 0 else ""
    marker = " *" if improved else ""
    return f"{arrow} {sign}{delta:.4f}{marker}"


def show_best() -> None:
    """Display current best model details."""
    best = _load_json(BEST_MODEL_PATH)
    if not best:
        print("No best model found. Run the sweep first:")
        print("  python -m trainer.sweep_variant2 --dry-run")
        return

    print("=" * 60)
    print("CURRENT BEST MODEL (from sweep)")
    print("=" * 60)
    print(f"  Run ID:          {best.get('run_id')}")
    print(f"  Stage:           {best.get('stage', 'N/A')}")
    print(f"  Composite Score: {best.get('composite_score', 0):.4f}")
    print(f"  Gate A Passed:   {best.get('gate_a_passed', False)}")
    print(f"  Updated:         {best.get('updated_at', 'unknown')}")
    print(f"  Total Trials:    {best.get('total_trials', 0)}")
    print(f"  Passing Trials:  {best.get('passing_trials', 0)}")
    print()
    print("  Config:")
    for k, v in best.get("config", {}).items():
        print(f"    {k}: {v}")
    print()
    print("  Metrics:")
    for k, v in best.get("metrics", {}).items():
        print(f"    {k}: {v}")


def compare_run(run_id: str) -> int:
    """Compare a run against the best model."""
    best = _load_json(BEST_MODEL_PATH)
    if not best:
        print("No best model found. Run the sweep first.")
        return 1

    # Try training results first, then test results
    run_data = _load_json(TRAIN_RESULTS_DIR / f"{run_id}.json")
    result_type = "train"
    if not run_data:
        run_data = _load_json(TEST_RESULTS_DIR / f"{run_id}.json")
        result_type = "test"
    if not run_data:
        print(f"No results found for run '{run_id}'")
        print(f"  Checked: {TRAIN_RESULTS_DIR / f'{run_id}.json'}")
        print(f"  Checked: {TEST_RESULTS_DIR / f'{run_id}.json'}")
        return 1

    run_metrics = run_data.get("gate_a_metrics", {})
    best_metrics = best.get("metrics", {})

    print("=" * 70)
    print(f"COMPARISON: {run_id} ({result_type}) vs Best ({best.get('run_id')})")
    print("=" * 70)
    print()
    print(f"  {'Metric':<14}  {'New Run':>10}  {'Best':>10}  {'Delta':>16}  {'Gate A':>10}")
    print("  " + "\u2500" * 66)

    improvements = 0
    regressions = 0

    for key, label, fmt, direction in METRICS_TO_COMPARE:
        val_new = run_metrics.get(key)
        val_best = best_metrics.get(key)

        str_new = f"{val_new:{fmt}}" if val_new is not None else "\u2014"
        str_best = f"{val_best:{fmt}}" if val_best is not None else "\u2014"

        delta_str = ""
        if val_new is not None and val_best is not None:
            delta_str = _format_delta(val_new, val_best, direction)
            delta = val_new - val_best
            if direction == "higher" and delta > 1e-6:
                improvements += 1
            elif direction == "lower" and delta < -1e-6:
                improvements += 1
            elif abs(delta) > 1e-6:
                regressions += 1

        # Gate A threshold check
        gate_str = ""
        if key in GATE_A_THRESHOLDS and val_new is not None:
            op, threshold = GATE_A_THRESHOLDS[key]
            if op == ">=" and val_new >= threshold:
                gate_str = "PASS"
            elif op == "<=" and val_new <= threshold:
                gate_str = "PASS"
            elif key in GATE_A_THRESHOLDS:
                gate_str = "FAIL"

        print(f"  {label:<14}  {str_new:>10}  {str_best:>10}  {delta_str:>16}  {gate_str:>10}")

    print()
    print(f"  Improvements: {improvements}  |  Regressions: {regressions}")

    # Overall verdict
    gates = run_data.get("gate_a_gates", {})
    all_passed = all(gates.values()) if gates else False
    print(f"  Gate A Overall: {'PASS' if all_passed else 'FAIL'}")

    if all_passed and not best.get("gate_a_passed"):
        print("\n  ** NEW BEST MODEL ** — this run passes Gate A while the previous best did not!")
    elif all_passed and improvements > regressions:
        print("\n  ** NEW BEST MODEL ** — better overall with Gate A passing!")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare a Variant 2 run against the sweep best model"
    )
    parser.add_argument("run_id", nargs="?", help="Run ID to compare")
    parser.add_argument("--latest", action="store_true", help="Compare the latest Variant 2 run")
    parser.add_argument("--show-best", action="store_true", dest="show_best",
                        help="Show current best model details")
    args = parser.parse_args()

    if args.show_best:
        show_best()
        return 0

    run_id = args.run_id
    if args.latest:
        run_id = _find_latest_var2()
        if not run_id:
            print("No Variant 2 runs found.")
            return 1
        print(f"Latest Variant 2 run: {run_id}\n")

    if not run_id:
        parser.print_help()
        return 1

    return compare_run(run_id)


if __name__ == "__main__":
    sys.exit(main())
