"""Training control router — launches training, validation, and test runs.

Spawns `trainer/run_efficientnet_pipeline.py` as a background subprocess so
the Media Mover API returns immediately while the long-running ML job
executes.  Status is persisted to the ``training_run`` table via the
existing gateway contract client built into the pipeline runner.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import AppConfig, get_config
from ..db import models
from ..deps import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["training-control"])

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
_DEFAULT_CONFIG_YAML = "trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml"
_DEFAULT_OUTPUT_DIR = "/media/rusty_admin/project_data/reachy_emotion/results"
_DEFAULT_DASHBOARD_DIR = "stats/results/runs"
_TRAIN_FRACTION = 0.9

_RUN_TYPE_TO_DIR: dict[str, str] = {
    "training": "train",
    "validation": "validate",
    "test": "test",
}
_VAL_FRACTION = 0.1
_VARIANT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _default_checkpoint_dir(config: AppConfig) -> Path:
    """Checkpoint directory derived from config.videos_root's parent."""
    return config.videos_root.parent / "checkpoints" / "efficientnet_b0_3cls"


def _run_dir(config: AppConfig) -> Path:
    return config.train_path / "run"


def _project_root() -> Path:
    """Resolve the project root (four levels up from this file)."""
    return Path(__file__).resolve().parents[4]


def _next_run_id(config: AppConfig) -> str:
    """Generate the next sequential run_XXXX ID.

    Delegates to ``DatasetPreparer.resolve_run_id()`` so that training
    control and dataset preparation always agree on the next identifier.
    """
    from trainer.prepare_dataset import DatasetPreparer  # lazy to avoid heavy cv2 import at module load

    preparer = DatasetPreparer(str(config.videos_root))
    return preparer.resolve_run_id(None)


def _normalize_variant(variant: Optional[str]) -> str:
    """Normalize and validate a model variant slug."""
    value = (variant or "variant_1").strip().lower()
    if not _VARIANT_PATTERN.fullmatch(value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "invalid_variant",
                "message": "variant must match ^[a-z0-9][a-z0-9_-]{0,63}$ (e.g., variant_1, variant_2)",
            },
        )
    return value


def _mode_to_run_type(mode: str) -> str:
    """Map launch mode to canonical run-type label used in stats paths."""
    if mode == "train":
        return "training"
    if mode == "validate":
        return "validation"
    return "test"


def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge *overrides* into *base*, returning a new dict."""
    merged = dict(base)
    for key, value in overrides.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _write_run_config(
    base_config_path: Path,
    run_id: str,
    overrides: Dict[str, Any],
    project_root: Path,
) -> Path:
    """Write a run-specific YAML config by merging overrides into the base.

    Returns the path to the newly written config file.
    """
    with open(base_config_path, "r") as fh:
        base_data = yaml.safe_load(fh) or {}

    merged = _deep_merge(base_data, overrides)

    run_configs_dir = project_root / "trainer" / "fer_finetune" / "specs" / "runs"
    run_configs_dir.mkdir(parents=True, exist_ok=True)
    run_config_path = run_configs_dir / f"{run_id}_finetune.yaml"

    with open(run_config_path, "w") as fh:
        yaml.dump(merged, fh, default_flow_style=False, sort_keys=False)

    logger.info("Wrote run-specific config: %s", run_config_path)
    return run_config_path


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class TrainingLaunchRequest(BaseModel):
    run_id: Optional[str] = Field(
        None,
        description="Run identifier. Auto-generated if omitted.",
    )
    variant: Optional[str] = Field(
        None,
        description="Model variant slug (e.g., variant_1, variant_2). Defaults to variant_1.",
    )
    config_path: Optional[str] = Field(
        None,
        description="Path to training YAML config (relative to project root).",
    )
    mode: str = Field(
        "train",
        description="Execution mode: 'train', 'validate', or 'test'.",
    )
    checkpoint: Optional[str] = Field(
        None,
        description="Checkpoint path (required for validate/test; defaults to best_model.pth for train).",
    )
    test_data_dir: Optional[str] = Field(
        None,
        description="Override test/validation data directory.",
    )
    config_overrides: Optional[Dict[str, Any]] = Field(
        None,
        description="Hyperparameter overrides merged into the base YAML config for fine-tuning.",
    )


class TrainingLaunchResponse(BaseModel):
    status: str
    run_id: str
    mode: str
    variant: str
    message: str
    pid: Optional[int] = None


class FineTuneRequest(BaseModel):
    """Request model for Variant 2 fine-tuning endpoint."""
    checkpoint_path: str = Field(
        ...,
        description="Path to Variant 1 checkpoint to load weights from.",
    )
    run_id: Optional[str] = Field(
        None,
        description="Run identifier. Auto-generated if omitted.",
    )
    epochs: int = Field(
        30,
        ge=1,
        le=200,
        description="Total number of training epochs.",
    )
    freeze_epochs: int = Field(
        5,
        ge=0,
        description="Number of epochs to keep backbone frozen before unfreezing.",
    )
    unfreeze_layers: list[str] = Field(
        ["blocks.5", "blocks.6", "conv_head"],
        description="Backbone layers to unfreeze after freeze_epochs.",
    )
    learning_rate: float = Field(
        3e-4,
        gt=0,
        description="Peak learning rate for head (backbone gets lr/10).",
    )


class FineTuneResponse(BaseModel):
    """Response model for fine-tuning endpoint."""
    status: str
    run_id: str
    variant: str = "variant_2"
    message: str
    pid: Optional[int] = None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/training/launch",
    response_model=TrainingLaunchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def launch_training(
    body: TrainingLaunchRequest,
    session: AsyncSession = Depends(get_db),
    config: AppConfig = Depends(get_config),
) -> TrainingLaunchResponse:
    """Launch a training, validation, or test run as a background process.

    Modes
    -----
    - **train** — full training pipeline (train → evaluate → Gate A)
    - **validate** — evaluation-only using an existing checkpoint against the
      run's validation split (``valid_ds_<run_id>`` or ``test/``)
    - **test** — evaluation-only against the run-scoped AffectNet test dataset at
      ``/videos/test/<run_id>``
    """
    mode = body.mode.strip().lower()
    if mode not in {"train", "validate", "test"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "invalid_mode", "message": f"mode must be train, validate, or test; got '{mode}'"},
        )

    run_id = (body.run_id or "").strip() or _next_run_id(config)
    variant = _normalize_variant(body.variant)
    run_type = _mode_to_run_type(mode)
    config_path = body.config_path or _DEFAULT_CONFIG_YAML
    project_root = _project_root()

    # Resolve checkpoint
    checkpoint = body.checkpoint
    if mode in {"validate", "test"} and not checkpoint:
        # Default to best_model.pth in standard checkpoint dir
        default_ckpt = _default_checkpoint_dir(config) / "best_model.pth"
        if default_ckpt.exists():
            checkpoint = str(default_ckpt)
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "checkpoint_required",
                    "message": (
                        f"No checkpoint provided and default not found at {default_ckpt}. "
                        "Run a training job first or provide an explicit --checkpoint."
                    ),
                },
            )

    # If config_overrides are provided, write a run-specific YAML
    effective_config_path = project_root / config_path
    if body.config_overrides:
        effective_config_path = _write_run_config(
            base_config_path=project_root / config_path,
            run_id=run_id,
            overrides=body.config_overrides,
            project_root=project_root,
        )

    # Build subprocess command — always use the project venv Python
    _venv_python = project_root / "venv" / "bin" / "python"
    python_exe = str(_venv_python) if _venv_python.exists() else sys.executable
    cmd = [
        python_exe, "-m", "trainer.run_efficientnet_pipeline",
        "--config", str(effective_config_path),
        "--run-id", run_id,
        "--variant", variant,
        "--run-type", run_type,
        "--output-dir", _DEFAULT_OUTPUT_DIR,
        "--dashboard-dir", str(project_root / _DEFAULT_DASHBOARD_DIR),
    ]

    # Gateway base for contract status updates
    gateway_base = os.getenv("REACHY_GATEWAY_BASE", f"http://localhost:{config.api_port}")
    cmd.extend(["--gateway-base", gateway_base])

    if mode in {"validate", "test"} and checkpoint:
        cmd.extend(["--skip-train", "--checkpoint", checkpoint])

    # For test mode, override the data root to point at the AffectNet test dataset
    # We do this by setting an env var that run_efficientnet_pipeline can pick up,
    # or we patch the config YAML on the fly.  Simpler: use an env override.
    env = {**os.environ}
    if mode == "test":
        test_dir = body.test_data_dir or str(config.test_path / run_id)
        env["REACHY_TEST_DATA_DIR"] = test_dir

    if mode == "validate" and body.test_data_dir:
        env["REACHY_TEST_DATA_DIR"] = body.test_data_dir

    # Persist initial status row
    initial_status = "training" if mode == "train" else "evaluating"
    now = datetime.now(timezone.utc)
    row = await session.get(models.TrainingRun, run_id)
    if row is None:
        run_data_path = str(_run_dir(config) / run_id) if mode == "train" else None
        row = models.TrainingRun(
            run_id=run_id,
            strategy=f"web_ui_{mode}",
            train_fraction=_TRAIN_FRACTION,
            test_fraction=_VAL_FRACTION,
            status=initial_status,
            started_at=now,
            metrics={
                "mode": mode,
                "run_type": run_type,
                "variant": variant,
                "config_path": config_path,
                "train_val_split": f"{_TRAIN_FRACTION}/{_VAL_FRACTION}",
                "run_data_path": run_data_path,
                "artifacts_root": f"{_DEFAULT_OUTPUT_DIR}/{_RUN_TYPE_TO_DIR.get(run_type, run_type)}/{run_id}",
            },
        )
        session.add(row)
    else:
        row.status = initial_status
        row.started_at = now
        merged = dict(row.metrics or {})
        merged["mode"] = mode
        merged["run_type"] = run_type
        merged["variant"] = variant
        merged["artifacts_root"] = f"{_DEFAULT_OUTPUT_DIR}/{_RUN_TYPE_TO_DIR.get(run_type, run_type)}/{run_id}"
        row.metrics = merged
    await session.commit()

    # Spawn subprocess
    try:
        log_dir = project_root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{variant}_{run_id}_{mode}.log"

        with open(log_file, "w") as lf:
            proc = subprocess.Popen(
                cmd,
                cwd=str(project_root),
                env=env,
                stdout=lf,
                stderr=subprocess.STDOUT,
                start_new_session=True,  # detach from parent
            )

        logger.info(
            "Launched %s run %s (pid=%d, log=%s)",
            mode, run_id, proc.pid, log_file,
        )

        return TrainingLaunchResponse(
            status="accepted",
            run_id=run_id,
            mode=mode,
            variant=variant,
            message=f"{mode.capitalize()} run launched (pid={proc.pid}). Check /api/training/status/{run_id} for progress.",
            pid=proc.pid,
        )

    except Exception as exc:
        logger.error("Failed to launch %s run %s: %s", mode, run_id, exc, exc_info=True)
        row.status = "failed"
        row.error_message = str(exc)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "launch_failed", "message": str(exc)},
        )


@router.post(
    "/api/v1/training/finetune",
    response_model=FineTuneResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def launch_finetune(
    body: FineTuneRequest,
    session: AsyncSession = Depends(get_db),
    config: AppConfig = Depends(get_config),
) -> FineTuneResponse:
    """Launch Variant 2 fine-tuning job with selective backbone unfreezing.

    This endpoint is specifically designed for Variant 2 training, which:
    1. Loads Variant 1 weights (model state only, no training state)
    2. Trains with backbone frozen for `freeze_epochs`
    3. Unfreezes specified backbone layers and continues training

    The job runs as a background subprocess via `trainer/train_variant2.py`.
    """
    checkpoint_path = Path(body.checkpoint_path)
    if not checkpoint_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "checkpoint_not_found", "message": f"Checkpoint not found: {checkpoint_path}"},
        )

    run_id = (body.run_id or "").strip() or _next_run_id(config)
    project_root = _project_root()
    python_exe = project_root / "venv" / "bin" / "python"
    if not python_exe.exists():
        python_exe = Path(sys.executable)

    # Build command for train_variant2.py
    cmd = [
        str(python_exe),
        "-m",
        "trainer.train_variant2",
        "--checkpoint",
        str(checkpoint_path),
        "--run-id",
        run_id,
        "--epochs",
        str(body.epochs),
        "--freeze-epochs",
        str(body.freeze_epochs),
        "--unfreeze-layers",
        ",".join(body.unfreeze_layers),
        "--lr",
        str(body.learning_rate),
    ]

    # Create training_run DB record
    now = datetime.now(timezone.utc)
    row = models.TrainingRun(
        run_id=run_id,
        strategy="finetune_v2",
        train_fraction=_TRAIN_FRACTION,
        test_fraction=_VAL_FRACTION,
        status="training",
        started_at=now,
        metrics={
            "variant": "variant_2",
            "checkpoint": str(checkpoint_path),
            "epochs": body.epochs,
            "freeze_epochs": body.freeze_epochs,
            "unfreeze_layers": body.unfreeze_layers,
            "learning_rate": body.learning_rate,
        },
        config={"checkpoint": str(checkpoint_path), "epochs": body.epochs, "freeze_epochs": body.freeze_epochs},
    )
    session.add(row)
    await session.commit()

    try:
        logger.info("Launching Variant 2 fine-tuning: %s", " ".join(cmd))
        proc = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        logger.info("Fine-tuning job started: run_id=%s, pid=%d", run_id, proc.pid)

        return FineTuneResponse(
            status="started",
            run_id=run_id,
            variant="variant_2",
            message=f"Fine-tuning job launched (pid={proc.pid}). Checkpoints will be saved to /checkpoints/variant_2/{run_id}/",
            pid=proc.pid,
        )

    except Exception as exc:
        logger.error("Failed to launch fine-tuning run %s: %s", run_id, exc, exc_info=True)
        row.status = "failed"
        row.error_message = str(exc)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "finetune_launch_failed", "message": str(exc)},
        )
