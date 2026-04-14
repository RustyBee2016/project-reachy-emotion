#!/usr/bin/env python3
"""
Automated hyperparameter sweep for Variant 2 fine-tuning.

Iterates through targeted parameter combinations to find the configuration
that maximizes generalization (F1 on validation data) while passing Gate A
calibration thresholds (ECE ≤ 0.08, Brier ≤ 0.16).

Strategy:
  1. Stage 1 (screening): Short runs (8 epochs) over a coarse grid of the
     most impactful regularization parameters.
  2. Stage 2 (refinement): Full runs (30 epochs) with the top-K configs from
     Stage 1, including early stopping.

Results are stored as a leaderboard in:
    stats/results/sweep/leaderboard.json
    stats/results/sweep/best_model.json   (auto-updated when a new best is found)

The sweep calls train_variant2.py with CLI flags — no direct import of
training internals, so each trial is fully isolated and config-tracked.

Usage:
    # Full sweep (Stage 1 screening + Stage 2 refinement)
    python -m trainer.sweep_variant2 \
        --checkpoint .../variant_1/var1_run_0107/best_model.pth \
        --train-run-id run_0107

    # Stage 1 only (fast screening, ~15-20 min per trial)
    python -m trainer.sweep_variant2 \
        --checkpoint .../variant_1/var1_run_0107/best_model.pth \
        --train-run-id run_0107 \
        --stage1-only

    # Dry run (print configs without training)
    python -m trainer.sweep_variant2 --dry-run

    # Custom search space via YAML
    python -m trainer.sweep_variant2 \
        --checkpoint .../best_model.pth \
        --train-run-id run_0107 \
        --search-space trainer/sweep_search_space.yaml

    # Resume a previously interrupted sweep
    python -m trainer.sweep_variant2 \
        --checkpoint .../best_model.pth \
        --train-run-id run_0107 \
        --resume
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SWEEP_DIR = PROJECT_ROOT / "stats" / "results" / "sweep"
LEADERBOARD_PATH = SWEEP_DIR / "leaderboard.json"
BEST_MODEL_PATH = SWEEP_DIR / "best_model.json"
TRAIN_RESULTS_DIR = PROJECT_ROOT / "stats" / "results" / "runs" / "train"

# Default checkpoint (latest V1)
DEFAULT_CHECKPOINT = (
    "/media/rusty_admin/project_data/reachy_emotion/checkpoints/"
    "variant_1/var1_run_0107/best_model.pth"
)

# ─────────────────────────────────────────────────────────────────────────────
# Search Space Definition
# ─────────────────────────────────────────────────────────────────────────────

# Stage 1: Coarse screening — focus on the parameters most likely to fix
# the overfitting + calibration issue (train F1=0.999 vs test F1=0.44)
STAGE1_SEARCH_SPACE: Dict[str, List[Any]] = {
    "dropout": [0.3, 0.5, 0.6],
    "label_smoothing": [0.10, 0.15, 0.20, 0.25],
    "lr": [1e-4, 3e-4],
    "freeze_epochs": [5, 8],
    "mixup_alpha": [0.2, 0.4],
}

# Stage 1 uses short runs to screen
STAGE1_EPOCHS = 8

# Stage 2: Take top-K from Stage 1, run with full epochs + early stopping
STAGE2_EPOCHS = 30
STAGE2_TOP_K = 5

# Fixed parameters that don't vary in the sweep
FIXED_PARAMS: Dict[str, Any] = {
    "unfreeze_layers": "blocks.5,blocks.6,conv_head",
    "weight_decay": 1e-4,
    "warmup_epochs": 2,
    "batch_size": 32,
    "patience": 10,
    "seed": 42,
}

# Gate A thresholds for ranking
GATE_A_THRESHOLDS = {
    "f1_macro": 0.84,
    "balanced_accuracy": 0.85,
    "per_class_f1": 0.75,
    "ece": 0.12,
    "brier": 0.16,
}


# ─────────────────────────────────────────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────────────────────────────────────────

def compute_composite_score(metrics: Dict[str, Any]) -> float:
    """Compute a composite score that balances classification performance and calibration.

    The score prioritizes:
    1. F1 Macro (primary classification metric)
    2. ECE (calibration — the current failure mode)
    3. Balanced accuracy
    4. Brier score

    All components are normalized to [0, 1] where higher is better.
    """
    f1 = metrics.get("f1_macro", 0.0)
    bal_acc = metrics.get("balanced_accuracy", 0.0)
    ece = metrics.get("ece", 1.0)
    brier = metrics.get("brier", 1.0)

    # Invert ECE and Brier (lower is better → higher score)
    ece_score = max(0.0, 1.0 - ece / 0.30)  # 0.30 as practical worst case
    brier_score = max(0.0, 1.0 - brier / 0.50)

    # Weighted composite — calibration gets extra weight since it's the failure mode
    score = (
        0.35 * f1
        + 0.30 * ece_score
        + 0.20 * bal_acc
        + 0.15 * brier_score
    )
    return round(score, 6)


def gate_a_passed(metrics: Dict[str, Any]) -> bool:
    """Check if all Gate A thresholds are met."""
    f1 = metrics.get("f1_macro", 0.0)
    bal_acc = metrics.get("balanced_accuracy", 0.0)
    ece = metrics.get("ece", 1.0)
    brier = metrics.get("brier", 1.0)

    per_class_ok = True
    for key in ["f1_happy", "f1_sad", "f1_neutral", "f1_class_0", "f1_class_1", "f1_class_2"]:
        val = metrics.get(key)
        if val is not None and val < GATE_A_THRESHOLDS["per_class_f1"]:
            per_class_ok = False
            break

    return (
        f1 >= GATE_A_THRESHOLDS["f1_macro"]
        and bal_acc >= GATE_A_THRESHOLDS["balanced_accuracy"]
        and ece <= GATE_A_THRESHOLDS["ece"]
        and brier <= GATE_A_THRESHOLDS["brier"]
        and per_class_ok
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sweep Engine
# ─────────────────────────────────────────────────────────────────────────────

def generate_trial_configs(search_space: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    """Generate all combinations from a search space dict."""
    keys = sorted(search_space.keys())
    values = [search_space[k] for k in keys]
    configs = []
    for combo in itertools.product(*values):
        configs.append(dict(zip(keys, combo)))
    return configs


def build_run_id(stage: int, trial_idx: int) -> str:
    """Generate a sweep run ID like var2_sweep_s1_t001."""
    return f"var2_sweep_s{stage}_t{trial_idx:03d}"


def run_trial(
    *,
    run_id: str,
    checkpoint: str,
    train_run_id: str,
    trial_config: Dict[str, Any],
    epochs: int,
    dry_run: bool = False,
) -> Optional[Dict[str, Any]]:
    """Execute a single training trial via subprocess.

    Returns the dashboard result JSON if successful, None otherwise.
    """
    cmd = [
        sys.executable, "-m", "trainer.train_variant2",
        "--checkpoint", checkpoint,
        "--train-run-id", train_run_id,
        "--run-id", run_id,
        "--epochs", str(epochs),
    ]

    # Map trial config keys to CLI flags
    flag_map = {
        "lr": "--lr",
        "dropout": "--dropout",
        "label_smoothing": "--label-smoothing",
        "freeze_epochs": "--freeze-epochs",
        "weight_decay": "--weight-decay",
        "warmup_epochs": "--warmup-epochs",
        "mixup_alpha": "--mixup-alpha",
        "mixup_prob": "--mixup-prob",
        "batch_size": "--batch-size",
        "patience": "--patience",
        "seed": "--seed",
        "unfreeze_layers": "--unfreeze-layers",
    }

    # Apply trial-specific params
    for key, value in trial_config.items():
        flag = flag_map.get(key)
        if flag:
            cmd.extend([flag, str(value)])

    # Apply fixed params (only if not overridden by trial config)
    for key, value in FIXED_PARAMS.items():
        if key not in trial_config:
            flag = flag_map.get(key)
            if flag:
                cmd.extend([flag, str(value)])

    if dry_run:
        logger.info("[DRY RUN] Would execute: %s", " ".join(cmd))
        return {"run_id": run_id, "dry_run": True, "config": trial_config}

    logger.info("=" * 60)
    logger.info("Starting trial: %s", run_id)
    logger.info("Config: %s", json.dumps(trial_config, indent=2))
    logger.info("Command: %s", " ".join(cmd))
    logger.info("=" * 60)

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout per trial
            cwd=str(PROJECT_ROOT),
        )
        elapsed = time.time() - start_time

        if result.returncode != 0:
            logger.warning(
                "Trial %s failed (exit %d, %.1fs)\nstderr: %s",
                run_id, result.returncode, elapsed, result.stderr[-500:] if result.stderr else "",
            )
            # Still try to collect partial results
        else:
            logger.info("Trial %s completed in %.1fs", run_id, elapsed)

    except subprocess.TimeoutExpired:
        logger.error("Trial %s timed out after 3600s", run_id)
        return None
    except Exception as exc:
        logger.error("Trial %s failed with exception: %s", run_id, exc)
        return None

    # Collect results from the dashboard payload
    result_path = TRAIN_RESULTS_DIR / f"{run_id}.json"
    if result_path.exists():
        with open(result_path) as f:
            return json.load(f)
    else:
        logger.warning("No result file found at %s", result_path)
        return None


def load_leaderboard() -> List[Dict[str, Any]]:
    """Load existing leaderboard or return empty list."""
    if LEADERBOARD_PATH.exists():
        with open(LEADERBOARD_PATH) as f:
            return json.load(f)
    return []


def save_leaderboard(entries: List[Dict[str, Any]]) -> None:
    """Save leaderboard sorted by composite score (descending)."""
    entries.sort(key=lambda e: e.get("composite_score", 0.0), reverse=True)
    SWEEP_DIR.mkdir(parents=True, exist_ok=True)
    with open(LEADERBOARD_PATH, "w") as f:
        json.dump(entries, f, indent=2, default=str)
    logger.info("Leaderboard saved → %s (%d entries)", LEADERBOARD_PATH, len(entries))


def update_best_model(entries: List[Dict[str, Any]]) -> None:
    """Update best_model.json with the top-scoring entry."""
    if not entries:
        return

    # Sort by composite score
    ranked = sorted(entries, key=lambda e: e.get("composite_score", 0.0), reverse=True)
    best = ranked[0]

    payload = {
        "run_id": best["run_id"],
        "stage": best.get("stage"),
        "composite_score": best["composite_score"],
        "gate_a_passed": best.get("gate_a_passed", False),
        "config": best.get("config", {}),
        "metrics": best.get("metrics", {}),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_trials": len(entries),
        "passing_trials": sum(1 for e in entries if e.get("gate_a_passed")),
    }

    SWEEP_DIR.mkdir(parents=True, exist_ok=True)
    with open(BEST_MODEL_PATH, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    logger.info(
        "Best model updated → %s (score=%.4f, gate_a=%s)",
        best["run_id"], best["composite_score"], best.get("gate_a_passed"),
    )


def _completed_run_ids(entries: List[Dict[str, Any]]) -> set:
    """Get set of already-completed run IDs from leaderboard."""
    return {e["run_id"] for e in entries if not e.get("dry_run")}


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Automated hyperparameter sweep for Variant 2 fine-tuning"
    )
    parser.add_argument(
        "--checkpoint", default=DEFAULT_CHECKPOINT,
        help="Path to Variant 1 checkpoint to fine-tune from",
    )
    parser.add_argument(
        "--train-run-id", default="run_0107", dest="train_run_id",
        help="Variant 1 training run ID (for data directory resolution)",
    )
    parser.add_argument(
        "--stage1-only", action="store_true", dest="stage1_only",
        help="Run Stage 1 screening only (skip Stage 2 refinement)",
    )
    parser.add_argument(
        "--stage2-only", action="store_true", dest="stage2_only",
        help="Skip Stage 1, run Stage 2 on existing leaderboard top-K",
    )
    parser.add_argument(
        "--dry-run", action="store_true", dest="dry_run",
        help="Print trial configs without running training",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume an interrupted sweep (skip already-completed trials)",
    )
    parser.add_argument(
        "--search-space", default=None, dest="search_space",
        help="Path to YAML file defining custom search space",
    )
    parser.add_argument(
        "--top-k", type=int, default=STAGE2_TOP_K, dest="top_k",
        help=f"Number of top Stage 1 configs to promote to Stage 2 (default: {STAGE2_TOP_K})",
    )
    parser.add_argument(
        "--stage1-epochs", type=int, default=STAGE1_EPOCHS, dest="stage1_epochs",
        help=f"Epochs per Stage 1 trial (default: {STAGE1_EPOCHS})",
    )
    parser.add_argument(
        "--stage2-epochs", type=int, default=STAGE2_EPOCHS, dest="stage2_epochs",
        help=f"Epochs per Stage 2 trial (default: {STAGE2_EPOCHS})",
    )
    args = parser.parse_args()

    # Load custom search space if provided
    search_space = STAGE1_SEARCH_SPACE
    if args.search_space:
        ss_path = Path(args.search_space)
        if not ss_path.exists():
            logger.error("Search space file not found: %s", ss_path)
            return 1
        with open(ss_path) as f:
            search_space = yaml.safe_load(f)
        logger.info("Loaded custom search space from %s", ss_path)

    # Load existing leaderboard (for resume support)
    leaderboard = load_leaderboard()
    completed_ids = _completed_run_ids(leaderboard) if args.resume else set()

    if args.resume and completed_ids:
        logger.info("Resuming sweep — %d trials already completed", len(completed_ids))

    # ── Stage 1: Screening ────────────────────────────────────────────────────
    if not args.stage2_only:
        trial_configs = generate_trial_configs(search_space)
        total_trials = len(trial_configs)
        logger.info(
            "Stage 1: %d trial configs × %d epochs = ~%d total epochs",
            total_trials, args.stage1_epochs, total_trials * args.stage1_epochs,
        )

        for idx, config in enumerate(trial_configs, start=1):
            run_id = build_run_id(stage=1, trial_idx=idx)

            if run_id in completed_ids:
                logger.info("Skipping completed trial: %s", run_id)
                continue

            logger.info("─── Stage 1 Trial %d/%d: %s ───", idx, total_trials, run_id)

            result = run_trial(
                run_id=run_id,
                checkpoint=args.checkpoint,
                train_run_id=args.train_run_id,
                trial_config=config,
                epochs=args.stage1_epochs,
                dry_run=args.dry_run,
            )

            if result and not args.dry_run:
                metrics = result.get("gate_a_metrics", {})
                entry = {
                    "run_id": run_id,
                    "stage": 1,
                    "config": config,
                    "metrics": metrics,
                    "composite_score": compute_composite_score(metrics),
                    "gate_a_passed": gate_a_passed(metrics),
                    "status": result.get("status", "unknown"),
                    "best_metric": result.get("best_metric", 0.0),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                leaderboard.append(entry)
                save_leaderboard(leaderboard)
                update_best_model(leaderboard)

                logger.info(
                    "  → F1=%.4f  ECE=%.4f  Score=%.4f  Gate A: %s",
                    metrics.get("f1_macro", 0),
                    metrics.get("ece", 1),
                    entry["composite_score"],
                    "PASS" if entry["gate_a_passed"] else "FAIL",
                )
            elif args.dry_run:
                logger.info("  → [DRY RUN] Config: %s", config)

        if args.stage1_only or args.dry_run:
            _print_summary(leaderboard)
            return 0

    # ── Stage 2: Refinement ───────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("Stage 2: Refinement (top-%d configs, %d epochs)", args.top_k, args.stage2_epochs)
    logger.info("=" * 60)

    # Select top-K from Stage 1 results
    stage1_entries = [e for e in leaderboard if e.get("stage") == 1]
    stage1_entries.sort(key=lambda e: e.get("composite_score", 0.0), reverse=True)
    top_configs = stage1_entries[: args.top_k]

    if not top_configs:
        logger.warning("No Stage 1 results to refine. Run Stage 1 first.")
        return 1

    for rank, entry in enumerate(top_configs, start=1):
        config = entry["config"]
        run_id = build_run_id(stage=2, trial_idx=rank)

        if run_id in completed_ids:
            logger.info("Skipping completed trial: %s", run_id)
            continue

        logger.info(
            "─── Stage 2 Trial %d/%d: %s (from %s, score=%.4f) ───",
            rank, len(top_configs), run_id, entry["run_id"], entry["composite_score"],
        )

        result = run_trial(
            run_id=run_id,
            checkpoint=args.checkpoint,
            train_run_id=args.train_run_id,
            trial_config=config,
            epochs=args.stage2_epochs,
            dry_run=args.dry_run,
        )

        if result and not args.dry_run:
            metrics = result.get("gate_a_metrics", {})
            s2_entry = {
                "run_id": run_id,
                "stage": 2,
                "config": config,
                "metrics": metrics,
                "composite_score": compute_composite_score(metrics),
                "gate_a_passed": gate_a_passed(metrics),
                "status": result.get("status", "unknown"),
                "best_metric": result.get("best_metric", 0.0),
                "promoted_from": entry["run_id"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            leaderboard.append(s2_entry)
            save_leaderboard(leaderboard)
            update_best_model(leaderboard)

            logger.info(
                "  → F1=%.4f  ECE=%.4f  Score=%.4f  Gate A: %s",
                metrics.get("f1_macro", 0),
                metrics.get("ece", 1),
                s2_entry["composite_score"],
                "PASS" if s2_entry["gate_a_passed"] else "FAIL",
            )

    _print_summary(leaderboard)
    return 0


def _print_summary(leaderboard: List[Dict[str, Any]]) -> None:
    """Print a compact summary of sweep results."""
    if not leaderboard:
        logger.info("No results to summarize.")
        return

    logger.info("\n" + "=" * 60)
    logger.info("SWEEP SUMMARY")
    logger.info("=" * 60)

    passing = [e for e in leaderboard if e.get("gate_a_passed")]
    logger.info("Total trials: %d", len(leaderboard))
    logger.info("Gate A passed: %d", len(passing))

    ranked = sorted(leaderboard, key=lambda e: e.get("composite_score", 0.0), reverse=True)
    logger.info("\nTop 5:")
    logger.info(
        "  %-20s  %6s  %6s  %6s  %6s  %7s  %s",
        "Run ID", "F1", "ECE", "Brier", "BalAcc", "Score", "Gate A",
    )
    logger.info("  " + "─" * 75)
    for entry in ranked[:5]:
        m = entry.get("metrics", {})
        logger.info(
            "  %-20s  %6.4f  %6.4f  %6.4f  %6.4f  %7.4f  %s",
            entry["run_id"],
            m.get("f1_macro", 0),
            m.get("ece", 1),
            m.get("brier", 1),
            m.get("balanced_accuracy", 0),
            entry.get("composite_score", 0),
            "PASS" if entry.get("gate_a_passed") else "FAIL",
        )

    if passing:
        best = passing[0]
        logger.info("\nBest passing config:")
        logger.info("  %s", json.dumps(best.get("config", {}), indent=4))


if __name__ == "__main__":
    sys.exit(main())
