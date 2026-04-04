"""
Centralized result storage for training, validation, and test runs.

Writes a JSON result file to two locations:
  1. Local data drive: /media/rusty_admin/project_data/reachy_emotion/results/<run_type>/<run_id>.json
  2. Project repo:     stats/results/dashboard_runs/<variant>/<run_type>/<run_id>.json

The project repo copy is what the Dashboard (06_Dashboard.py) reads.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

LOCAL_RESULTS_ROOT = Path("/media/rusty_admin/project_data/reachy_emotion/results")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_RESULTS_ROOT = PROJECT_ROOT / "stats" / "results" / "dashboard_runs"


def save_run_result(
    variant: str,
    run_type: str,
    run_id: str,
    payload: Dict[str, Any],
    local_root: Optional[Path] = None,
    dashboard_root: Optional[Path] = None,
) -> tuple[Path, Path]:
    """Save a run result to both local and project directories.

    Args:
        variant: Model variant ("base", "variant_1", "variant_2")
        run_type: One of "train", "validate", "test"
        run_id: Run identifier (e.g. "run_0100", "run_0101")
        payload: Result dict (metrics, gate results, metadata)
        local_root: Override for local results root
        dashboard_root: Override for project dashboard results root

    Returns:
        Tuple of (local_path, dashboard_path) where the result was written.
    """
    if local_root is None:
        local_root = LOCAL_RESULTS_ROOT
    if dashboard_root is None:
        dashboard_root = DASHBOARD_RESULTS_ROOT

    # Ensure required fields are present
    payload.setdefault("run_id", run_id)
    payload.setdefault("run_type", run_type)
    payload.setdefault("model_variant", variant)

    filename = f"{run_id}.json"
    content = json.dumps(payload, indent=2, default=str)

    # Write to local data drive
    local_dir = local_root / run_type / run_id
    local_dir.mkdir(parents=True, exist_ok=True)
    local_path = local_dir / filename
    local_path.write_text(content, encoding="utf-8")
    logger.info(f"Result saved (local): {local_path}")

    # Write to project repo for dashboard
    dashboard_dir = dashboard_root / variant / run_type
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    dashboard_path = dashboard_dir / filename
    dashboard_path.write_text(content, encoding="utf-8")
    logger.info(f"Result saved (dashboard): {dashboard_path}")

    return local_path, dashboard_path
