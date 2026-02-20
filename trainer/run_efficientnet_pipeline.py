#!/usr/bin/env python3
"""
End-to-end EfficientNet-B0 pipeline runner:
train -> evaluate -> Gate A validate -> statistical outputs.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests


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
    strict: bool,
) -> None:
    if client is None:
        return
    payload = _build_contract_payload(
        event_type="training.started",
        run_id=run_id,
        status="training",
        source="agent5.training_orchestrator",
        metrics={"config_path": config_path},
    )
    _post_contract_payload(client, run_id=run_id, payload=payload, strict=strict)


def _emit_evaluation_started(
    client: Optional[GatewayContractClient],
    *,
    run_id: str,
    checkpoint_path: str,
    strict: bool,
) -> None:
    if client is None:
        return
    payload = _build_contract_payload(
        event_type="evaluation.started",
        run_id=run_id,
        status="evaluating",
        source="agent6.evaluation_agent",
        metrics={"checkpoint_path": checkpoint_path},
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
    strict: bool,
) -> None:
    if client is None:
        return
    payload = _build_contract_payload(
        event_type="training.failed",
        run_id=run_id,
        status="failed",
        source="agent5.training_orchestrator",
        metrics={},
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
        frames_per_video=frames_per_video,
        run_id=run_id,
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run complete EfficientNet pipeline")
    parser.add_argument("--config", default="trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml")
    parser.add_argument("--run-id", default="efficientnet_pipeline_run")
    parser.add_argument("--skip-train", action="store_true", help="Skip training and use existing checkpoint")
    parser.add_argument("--checkpoint", help="Checkpoint path when --skip-train is used")
    parser.add_argument("--output-dir", default="stats/results")
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

    import numpy as np

    from trainer.fer_finetune.config import TrainingConfig
    from trainer.fer_finetune.train_efficientnet import EfficientNetTrainer
    from trainer.gate_a_validator import GateAThresholds, evaluate_predictions

    config = TrainingConfig.from_yaml(args.config)
    contract_client: Optional[GatewayContractClient] = None
    if not args.no_contract_updates:
        contract_client = GatewayContractClient(base_url=args.gateway_base)

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
            strict=args.strict_contract_updates,
        )
    else:
        _emit_training_started(
            contract_client,
            run_id=args.run_id,
            config_path=args.config,
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
                    strict=args.strict_contract_updates,
                )
                raise SystemExit(f"Training failed: {train_result}")
            checkpoint_path = Path(config.checkpoint_dir) / "best_model.pth"
            _emit_evaluation_started(
                contract_client,
                run_id=args.run_id,
                checkpoint_path=str(checkpoint_path),
                strict=args.strict_contract_updates,
            )
        except Exception as exc:
            _emit_training_failed(
                contract_client,
                run_id=args.run_id,
                error_message=str(exc),
                strict=args.strict_contract_updates,
            )
            raise

    preds = _collect_predictions(
        checkpoint_path=checkpoint_path,
        data_root=config.data.data_root,
        class_names=config.data.class_names,
        input_size=config.model.input_size,
        batch_size=config.data.batch_size,
        num_workers=config.data.num_workers,
        run_id=args.run_id,
        frames_per_video=config.data.frames_per_video,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pred_path = output_dir / f"{args.run_id}_predictions.npz"
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
    gate_path = output_dir / f"{args.run_id}_gate_a.json"
    gate_path.write_text(json.dumps(gate_report, indent=2))

    _emit_training_completed(
        contract_client,
        run_id=args.run_id,
        train_result=train_result,
        gate_report=gate_report,
        pred_path=str(pred_path),
        gate_path=str(gate_path),
        event_type="evaluation.completed" if args.skip_train else "training.completed",
        source="agent6.evaluation_agent" if args.skip_train else "agent5.training_orchestrator",
        strict=args.strict_contract_updates,
    )

    print(
        json.dumps(
            {
                "predictions": str(pred_path),
                "gate_report": str(gate_path),
                "overall_pass": gate_report["overall_pass"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
