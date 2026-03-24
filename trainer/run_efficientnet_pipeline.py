#!/usr/bin/env python3
"""
End-to-end EfficientNet-B0 pipeline runner:
train -> evaluate -> Gate A validate -> statistical outputs.

This script orchestrates the complete ML workflow for Agent 5 (Training
Orchestrator) and Agent 6 (Evaluation Agent).  It can either:
  1. Train a model from scratch, then evaluate it, OR
  2. Skip training and evaluate an existing checkpoint (--skip-train mode)

Key responsibilities:
  - Emit Agent 5/6 contract events to the FastAPI gateway for n8n tracking
  - Run Gate A validation on predictions
  - Export ONNX when gates pass
  - Write dashboard payload files for the web UI (06_Dashboard.py)
  - Support variant/run-type partitioning for A/B testing
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

# ---------------------------------------------------------------------------
# Variant naming pattern validator (e.g., variant_1, variant_2, base_model)
# Used for organizing outputs under stats/results/<variant>/<run_type>/<run_id>
# ---------------------------------------------------------------------------
_VARIANT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


# ===========================================================================
# Gateway Contract Client
# ===========================================================================
# This client posts structured event payloads to the FastAPI gateway
# (Ubuntu 2) at /api/training/status/<run_id>.  The gateway persists these
# events to Postgres and forwards them to n8n workflows (Agent 5 & Agent 6)
# for orchestration tracking, alerting, and dashboard updates.
#
# Event types emitted:
#   - training.started
#   - training.completed
#   - training.failed
#   - evaluation.started
#   - evaluation.completed
# ===========================================================================

class GatewayContractClient:
    """Minimal client for Agent 5/6 status contracts via gateway."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 10.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def post_training_status(self, run_id: str, payload: Dict[str, Any]) -> None:
        """POST event payload to gateway /api/training/status/<run_id> endpoint."""
        url = f"{self.base_url}/api/training/status/{run_id}"
        response = self.session.post(url, json=payload, timeout=self.timeout_seconds)
        response.raise_for_status()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_contract_payload(
    *,
    event_type: str,
    run_id: str,
    status: str,
    source: str,
    metrics: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": "v1",
        "event_type": event_type,
        "source": source,
        "correlation_id": run_id,
        "issued_at": _utcnow_iso(),
        "status": status,
        "metrics": metrics or {},
        "error_message": error_message,
    }


def _emit_training_started(
    client: Optional[GatewayContractClient],
    *,
    run_id: str,
    config_path: str,
    variant: str = "variant_1",
    run_type: str = "training",
    strict: bool,
) -> None:
    if client is None:
        return
    payload = _build_contract_payload(
        event_type="training.started",
        run_id=run_id,
        status="training",
        source="agent5.training_orchestrator",
        metrics={"config_path": config_path, "variant": variant, "run_type": run_type},
    )
    _post_contract_payload(client, run_id=run_id, payload=payload, strict=strict)


def _emit_evaluation_started(
    client: Optional[GatewayContractClient],
    *,
    run_id: str,
    checkpoint_path: str,
    variant: str = "variant_1",
    run_type: str = "training",
    strict: bool,
) -> None:
    if client is None:
        return
    payload = _build_contract_payload(
        event_type="evaluation.started",
        run_id=run_id,
        status="evaluating",
        source="agent6.evaluation_agent",
        metrics={"checkpoint_path": checkpoint_path, "variant": variant, "run_type": run_type},
    )
    _post_contract_payload(client, run_id=run_id, payload=payload, strict=strict)


def _emit_training_completed(
    client: Optional[GatewayContractClient],
    *,
    run_id: str,
    train_result: Dict[str, Any],
    gate_report: Dict[str, Any],
    pred_path: str,
    gate_path: str,
    event_type: str = "training.completed",
    source: str = "agent5.training_orchestrator",
    variant: str = "variant_1",
    run_type: str = "training",
    strict: bool,
) -> None:
    if client is None:
        return
    metrics = {
        "training_status": train_result.get("status"),
        "epochs_completed": train_result.get("epochs_completed"),
        "best_metric": train_result.get("best_metric"),
        "gate_a_passed": bool(gate_report.get("overall_pass")),
        "gate_a_metrics": gate_report.get("metrics", {}),
        "gate_a_gates": gate_report.get("gates", {}),
        "variant": variant,
        "run_type": run_type,
        "artifacts": {
            "predictions_npz": pred_path,
            "gate_a_report_json": gate_path,
        },
    }
    payload = _build_contract_payload(
        event_type=event_type,
        run_id=run_id,
        status="completed",
        source=source,
        metrics=metrics,
    )
    _post_contract_payload(client, run_id=run_id, payload=payload, strict=strict)


def _emit_training_failed(
    client: Optional[GatewayContractClient],
    *,
    run_id: str,
    error_message: str,
    variant: str = "variant_1",
    run_type: str = "training",
    strict: bool,
) -> None:
    if client is None:
        return
    payload = _build_contract_payload(
        event_type="training.failed",
        run_id=run_id,
        status="failed",
        source="agent5.training_orchestrator",
        metrics={"variant": variant, "run_type": run_type},
        error_message=error_message,
    )
    _post_contract_payload(client, run_id=run_id, payload=payload, strict=strict)


def _post_contract_payload(
    client: GatewayContractClient,
    *,
    run_id: str,
    payload: Dict[str, Any],
    strict: bool,
) -> None:
    try:
        client.post_training_status(run_id, payload)
    except Exception as exc:  # noqa: BLE001
        if strict:
            raise
        print(
            json.dumps(
                {
                    "warning": "contract_emit_failed",
                    "run_id": run_id,
                    "event_type": payload.get("event_type"),
                    "error": str(exc),
                }
            )
        )


# ===========================================================================
# Prediction Collection (Evaluation Phase)
# ===========================================================================
# Load a trained checkpoint and run inference on the validation dataset to
# collect ground-truth labels (y_true), predicted labels (y_pred), and
# softmax probabilities (y_prob).  These arrays are saved as .npz files and
# used by gate_a_validator.py to compute Gate A metrics (F1, ECE, Brier).
#
# This function is called after training completes OR in --skip-train mode
# when evaluating an existing checkpoint against test data.
# ===========================================================================

def _collect_predictions(
    checkpoint_path: Path,
    data_root: str,
    class_names: List[str],
    input_size: int,
    batch_size: int,
    num_workers: int,
    run_id: Optional[str] = None,
    frames_per_video: int = 1,
) -> Dict[str, Any]:
    import numpy as np
    import torch

    from trainer.fer_finetune.dataset import create_dataloaders
    from trainer.fer_finetune.model_efficientnet import load_pretrained_model

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = load_pretrained_model(str(checkpoint_path), num_classes=len(class_names), device=device)
    _, val_loader = create_dataloaders(
        data_dir=data_root,
        batch_size=batch_size,
        num_workers=num_workers,
        input_size=input_size,
        class_names=class_names,
        frame_sampling_train="random",
        frame_sampling_val="middle",
        run_id=run_id,
        frames_per_video=frames_per_video,
    )

    y_true: List[int] = []
    y_pred: List[int] = []
    y_prob: List[np.ndarray] = []

    model.eval()
    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device)
            outputs = model(images)
            logits = outputs["logits"] if isinstance(outputs, dict) else outputs
            probs = torch.softmax(logits, dim=1)
            preds = torch.argmax(probs, dim=1)
            y_true.extend(labels.cpu().numpy().tolist())
            y_pred.extend(preds.cpu().numpy().tolist())
            y_prob.extend(probs.cpu().numpy())

    return {
        "y_true": np.array(y_true, dtype=np.int64),
        "y_pred": np.array(y_pred, dtype=np.int64),
        "y_prob": np.array(y_prob, dtype=np.float32),
    }


def _normalize_variant(variant: str) -> str:
    normalized = variant.strip().lower()
    if not _VARIANT_PATTERN.fullmatch(normalized):
        raise SystemExit("Invalid --variant value. Expected ^[a-z0-9][a-z0-9_-]{0,63}$")
    return normalized


def _normalize_run_type(run_type: str) -> str:
    normalized = run_type.strip().lower()
    aliases = {
        "train": "training",
        "training": "training",
        "validate": "validation",
        "validation": "validation",
        "test": "test",
    }
    if normalized not in aliases:
        raise SystemExit("Invalid --run-type value. Expected one of: training, validation, test")
    return aliases[normalized]


# ===========================================================================
# Artifact Directory Resolution
# ===========================================================================
# Organize outputs by variant/run_type/run_id hierarchy:
#   stats/results/variant_1/training/run_0042/
#   stats/results/variant_2/validation/run_0043/
# This enables A/B testing and clean separation of training vs validation runs.
# ===========================================================================

def _resolve_artifact_dir(output_dir: str, variant: str, run_type: str, run_id: str) -> Path:
    return Path(output_dir) / variant / run_type / run_id


# ===========================================================================
# Dashboard Payload Generation
# ===========================================================================
# Write a JSON payload file consumed by the Streamlit dashboard (06_Dashboard.py)
# to display Gate A metrics, confusion matrices, and artifact paths.
# Payloads are organized under:
#   stats/results/dashboard_runs/<variant>/<run_type>/<run_id>.json
# ===========================================================================

def _write_dashboard_run_payload(
    *,
    output_dir: str,
    variant: str,
    run_type: str,
    run_id: str,
    gate_report: Dict[str, Any],
    predictions_path: Path,
    gate_path: Path,
    onnx_path: Optional[str],
) -> Path:
    dashboard_root = Path(output_dir) / "dashboard_runs" / variant / run_type
    dashboard_root.mkdir(parents=True, exist_ok=True)
    dashboard_payload_path = dashboard_root / f"{run_id}.json"
    dashboard_payload = {
        "run_id": run_id,
        "model_variant": variant,
        "run_type": run_type,
        "gate_a_metrics": gate_report.get("metrics", {}),
        "gate_a_gates": gate_report.get("gates", {}),
        "overall_pass": bool(gate_report.get("overall_pass")),
        "artifacts": {
            "predictions_npz": str(predictions_path),
            "gate_a_report_json": str(gate_path),
            "onnx_path": onnx_path,
        },
    }
    dashboard_payload_path.write_text(json.dumps(dashboard_payload, indent=2))
    return dashboard_payload_path


# ===========================================================================
# Main Pipeline Orchestration
# ===========================================================================
# This function coordinates the full train -> evaluate -> validate -> export
# workflow.  It handles both training mode (default) and evaluation-only mode
# (--skip-train), emitting contract events to the gateway at each phase.
# ===========================================================================

def main() -> int:
    # -------------------------------------------------------------------
    # CLI Argument Parsing
    # -------------------------------------------------------------------
    # Key flags:
    #   --config         : Training config YAML (hyperparameters, data paths)
    #   --run-id         : Unique identifier for this pipeline run
    #   --skip-train     : Evaluate existing checkpoint without training
    #   --checkpoint     : Path to checkpoint (required with --skip-train)
    #   --variant        : Model variant slug (variant_1, variant_2, etc.)
    #   --run-type       : training | validation | test
    #   --gateway-base   : FastAPI gateway URL for contract events
    # -------------------------------------------------------------------
    parser = argparse.ArgumentParser(description="Run complete EfficientNet pipeline")
    parser.add_argument("--config", default="trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml")
    parser.add_argument("--run-id", default="efficientnet_pipeline_run")
    parser.add_argument("--skip-train", action="store_true", help="Skip training and use existing checkpoint")
    parser.add_argument("--checkpoint", help="Checkpoint path when --skip-train is used")
    parser.add_argument("--output-dir", default="stats/results")
    parser.add_argument(
        "--variant",
        default="variant_1",
        help="Model variant slug used for output path partitioning (e.g., variant_1, variant_2)",
    )
    parser.add_argument(
        "--run-type",
        default="training",
        help="Run type used for output path partitioning: training, validation, or test",
    )
    parser.add_argument(
        "--gateway-base",
        default=os.getenv("REACHY_GATEWAY_BASE", "http://10.0.4.140:8000"),
        help="Gateway base URL for Agent 5/6 contract status updates",
    )
    parser.add_argument(
        "--no-contract-updates",
        action="store_true",
        help="Disable Agent 5/6 gateway status contract updates",
    )
    parser.add_argument(
        "--strict-contract-updates",
        action="store_true",
        help="Fail pipeline when contract update calls fail",
    )
    args = parser.parse_args()
    args.variant = _normalize_variant(args.variant)
    args.run_type = _normalize_run_type(args.run_type)

    import numpy as np

    from trainer.fer_finetune.config import TrainingConfig
    from trainer.fer_finetune.train_efficientnet import EfficientNetTrainer
    from trainer.gate_a_validator import GateAThresholds, evaluate_predictions

    config = TrainingConfig.from_yaml(args.config)

    # Allow env-var override of the evaluation data root (used by test mode)
    test_data_dir = os.getenv("REACHY_TEST_DATA_DIR")
    if test_data_dir and args.skip_train:
        config.data.data_root = test_data_dir

    # -------------------------------------------------------------------
    # Gateway Contract Client Initialization
    # -------------------------------------------------------------------
    # If --no-contract-updates is NOT set, create a client to emit
    # training/evaluation events to the FastAPI gateway.  This enables
    # n8n workflows (Agent 5 & 6) to track pipeline progress in real-time.
    # -------------------------------------------------------------------
    contract_client: Optional[GatewayContractClient] = None
    if not args.no_contract_updates:
        contract_client = GatewayContractClient(base_url=args.gateway_base)

    # -------------------------------------------------------------------
    # Training Phase (or Skip)
    # -------------------------------------------------------------------
    # If --skip-train is set, bypass training and jump straight to
    # evaluation.  Otherwise, instantiate EfficientNetTrainer and run
    # the full training loop.  Emit training.started and training.completed
    # events to the gateway.
    # -------------------------------------------------------------------
    train_result: Dict[str, Any] = {
        "run_id": args.run_id,
        "status": "skipped",
        "epochs_completed": None,
        "best_metric": None,
    }
    if args.skip_train:
        if not args.checkpoint:
            raise SystemExit("--checkpoint is required with --skip-train")
        checkpoint_path = Path(args.checkpoint)
        _emit_evaluation_started(
            contract_client,
            run_id=args.run_id,
            checkpoint_path=str(checkpoint_path),
            variant=args.variant,
            run_type=args.run_type,
            strict=args.strict_contract_updates,
        )
    else:
        _emit_training_started(
            contract_client,
            run_id=args.run_id,
            config_path=args.config,
            variant=args.variant,
            run_type=args.run_type,
            strict=args.strict_contract_updates,
        )
        try:
            trainer = EfficientNetTrainer(config)
            train_result = trainer.train(run_id=args.run_id, resume_epoch=0)
            if train_result["status"] not in {"completed", "completed_gate_passed", "completed_gate_failed"}:
                _emit_training_failed(
                    contract_client,
                    run_id=args.run_id,
                    error_message=f"Training failed: {train_result}",
                    variant=args.variant,
                    run_type=args.run_type,
                    strict=args.strict_contract_updates,
                )
                raise SystemExit(f"Training failed: {train_result}")
            checkpoint_path = Path(config.checkpoint_dir) / "best_model.pth"
            _emit_evaluation_started(
                contract_client,
                run_id=args.run_id,
                checkpoint_path=str(checkpoint_path),
                variant=args.variant,
                run_type=args.run_type,
                strict=args.strict_contract_updates,
            )
        except Exception as exc:
            _emit_training_failed(
                contract_client,
                run_id=args.run_id,
                error_message=str(exc),
                variant=args.variant,
                run_type=args.run_type,
                strict=args.strict_contract_updates,
            )
            raise

    # -------------------------------------------------------------------
    # Evaluation Phase
    # -------------------------------------------------------------------
    # Wrapped in try/except to emit training.failed events on crashes.
    # Steps:
    #   1. Collect predictions (y_true, y_pred, y_prob) from validation set
    #   2. Save predictions.npz for reproducibility
    #   3. Run Gate A validation (F1, balanced accuracy, ECE, Brier)
    #   4. Export to ONNX if gates pass
    #   5. Write dashboard payload JSON
    #   6. Emit evaluation.completed event to gateway
    # -------------------------------------------------------------------
    try:
        preds = _collect_predictions(
            checkpoint_path=checkpoint_path,
            data_root=config.data.data_root,
            class_names=config.data.class_names,
            input_size=config.model.input_size,
            batch_size=config.data.batch_size,
            num_workers=0,  # avoid multiprocessing deadlocks on small datasets
            run_id=args.run_id,
            frames_per_video=max(1, int(config.data.frames_per_video)),
        )

        output_dir = _resolve_artifact_dir(
            output_dir=args.output_dir,
            variant=args.variant,
            run_type=args.run_type,
            run_id=args.run_id,
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        pred_path = output_dir / "predictions.npz"
        np.savez(
            pred_path,
            y_true=preds["y_true"],
            y_pred=preds["y_pred"],
            y_prob=preds["y_prob"],
            class_names=np.array(config.data.class_names),
        )

        gate_report = evaluate_predictions(
            preds["y_true"],
            preds["y_pred"],
            preds["y_prob"],
            config.data.class_names,
            GateAThresholds(),
        )
        gate_path = output_dir / "gate_a.json"
        gate_path.write_text(json.dumps(gate_report, indent=2))

        # ---------------------------------------------------------------
        # Conditional ONNX Export
        # ---------------------------------------------------------------
        # If Gate A validation passed (F1 ≥ 0.84, ECE ≤ 0.08, etc.),
        # export the checkpoint to ONNX format.  The ONNX file is later
        # converted to TensorRT by Agent 7 (Deployment Agent) on Jetson.
        # ---------------------------------------------------------------
        onnx_path: Optional[str] = None
        if gate_report["overall_pass"]:
            from trainer.fer_finetune.export import export_efficientnet_for_deployment

            export_dir = output_dir / "export"
            export_result = export_efficientnet_for_deployment(
                checkpoint_path=str(checkpoint_path),
                output_dir=str(export_dir),
                num_classes=len(config.data.class_names),
                input_size=config.model.input_size,
            )
            onnx_path = export_result.get("onnx_path")
            print(json.dumps({"onnx_export": export_result}, indent=2))

        dashboard_payload_path = _write_dashboard_run_payload(
            output_dir=args.output_dir,
            variant=args.variant,
            run_type=args.run_type,
            run_id=args.run_id,
            gate_report=gate_report,
            predictions_path=pred_path,
            gate_path=gate_path,
            onnx_path=onnx_path,
        )

        _emit_training_completed(
            contract_client,
            run_id=args.run_id,
            train_result=train_result,
            gate_report=gate_report,
            pred_path=str(pred_path),
            gate_path=str(gate_path),
            event_type="evaluation.completed" if args.skip_train else "training.completed",
            source="agent6.evaluation_agent" if args.skip_train else "agent5.training_orchestrator",
            variant=args.variant,
            run_type=args.run_type,
            strict=args.strict_contract_updates,
        )

        print(
            json.dumps(
                {
                    "predictions": str(pred_path),
                    "gate_report": str(gate_path),
                    "dashboard_payload": str(dashboard_payload_path),
                    "overall_pass": gate_report["overall_pass"],
                    "onnx_path": onnx_path,
                },
                indent=2,
            )
        )
        return 0

    except Exception as exc:
        _emit_training_failed(
            contract_client,
            run_id=args.run_id,
            error_message=f"Evaluation failed: {exc}",
            variant=args.variant,
            run_type=args.run_type,
            strict=args.strict_contract_updates,
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
