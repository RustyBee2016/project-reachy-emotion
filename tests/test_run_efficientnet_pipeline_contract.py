from __future__ import annotations

from typing import Any, Dict, List

from trainer import run_efficientnet_pipeline as pipeline


class _DummyResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


class _DummySession:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def post(self, url: str, json: Dict[str, Any], timeout: float) -> _DummyResponse:
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        return _DummyResponse(200)


def test_gateway_contract_client_posts_training_status() -> None:
    session = _DummySession()
    client = pipeline.GatewayContractClient(
        base_url="http://gateway.local:8000",
        session=session,  # type: ignore[arg-type]
        timeout_seconds=3.5,
    )

    client.post_training_status("run_abc", {"status": "training", "metrics": {"epoch": 1}})

    assert len(session.calls) == 1
    call = session.calls[0]
    assert call["url"] == "http://gateway.local:8000/api/training/status/run_abc"
    assert call["json"]["status"] == "training"
    assert call["json"]["metrics"]["epoch"] == 1
    assert call["timeout"] == 3.5


def test_build_contract_payload_contains_required_envelope_fields() -> None:
    payload = pipeline._build_contract_payload(  # type: ignore[attr-defined]
        event_type="training.started",
        run_id="run_123",
        status="training",
        source="agent5.training_orchestrator",
        metrics={"config_path": "cfg.yaml"},
    )

    assert payload["schema_version"] == "v1"
    assert payload["event_type"] == "training.started"
    assert payload["source"] == "agent5.training_orchestrator"
    assert payload["correlation_id"] == "run_123"
    assert payload["status"] == "training"
    assert payload["issued_at"]


def test_emit_training_completed_posts_gate_a_metrics() -> None:
    session = _DummySession()
    client = pipeline.GatewayContractClient(
        base_url="http://gateway.local:8000",
        session=session,  # type: ignore[arg-type]
    )

    train_result = {
        "status": "completed_gate_passed",
        "epochs_completed": 5,
        "best_metric": 0.91,
    }
    gate_report = {
        "overall_pass": True,
        "metrics": {"f1_macro": 0.91, "balanced_accuracy": 0.9},
        "gates": {"macro_f1": True, "balanced_accuracy": True},
    }

    pipeline._emit_training_completed(  # type: ignore[attr-defined]
        client,
        run_id="run_55",
        train_result=train_result,
        gate_report=gate_report,
        pred_path="/tmp/preds.npz",
        gate_path="/tmp/gate.json",
        strict=True,
    )

    assert len(session.calls) == 1
    payload = session.calls[0]["json"]
    assert payload["event_type"] == "training.completed"
    assert payload["status"] == "completed"
    assert payload["metrics"]["gate_a_passed"] is True
    assert payload["metrics"]["gate_a_metrics"]["f1_macro"] == 0.91
    assert payload["metrics"]["artifacts"]["predictions_npz"] == "/tmp/preds.npz"
