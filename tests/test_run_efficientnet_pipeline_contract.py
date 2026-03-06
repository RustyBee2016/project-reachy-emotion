from __future__ import annotations

import sys
import types
from typing import Any, Dict, List

import numpy as np
import pytest

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
    assert payload["metrics"]["variant"] == "variant_1"
    assert payload["metrics"]["run_type"] == "training"


def test_emit_contract_payloads_include_variant_context() -> None:
    """All _emit_* functions must propagate variant and run_type into payloads."""
    session = _DummySession()
    client = pipeline.GatewayContractClient(
        base_url="http://gateway.local:8000",
        session=session,  # type: ignore[arg-type]
    )

    pipeline._emit_training_started(  # type: ignore[attr-defined]
        client,
        run_id="run_v2",
        config_path="cfg.yaml",
        variant="variant_2",
        run_type="validation",
        strict=True,
    )
    started_payload = session.calls[-1]["json"]
    assert started_payload["metrics"]["variant"] == "variant_2"
    assert started_payload["metrics"]["run_type"] == "validation"

    pipeline._emit_evaluation_started(  # type: ignore[attr-defined]
        client,
        run_id="run_v2",
        checkpoint_path="/tmp/ckpt.pth",
        variant="variant_2",
        run_type="test",
        strict=True,
    )
    eval_payload = session.calls[-1]["json"]
    assert eval_payload["metrics"]["variant"] == "variant_2"
    assert eval_payload["metrics"]["run_type"] == "test"

    pipeline._emit_training_failed(  # type: ignore[attr-defined]
        client,
        run_id="run_v2",
        error_message="boom",
        variant="variant_2",
        run_type="training",
        strict=True,
    )
    failed_payload = session.calls[-1]["json"]
    assert failed_payload["metrics"]["variant"] == "variant_2"
    assert failed_payload["metrics"]["run_type"] == "training"


def test_collect_predictions_passes_run_id_to_dataloaders() -> None:
    captured: Dict[str, Any] = {}

    class _FakeTensor:
        def __init__(self, values: Any) -> None:
            self._arr = np.array(values)

        def to(self, _device: str) -> "_FakeTensor":
            return self

        def cpu(self) -> "_FakeTensor":
            return self

        def numpy(self) -> np.ndarray:
            return self._arr

    class _FakeNoGrad:
        def __enter__(self) -> None:
            return None

        def __exit__(self, _exc_type, _exc, _tb) -> bool:
            return False

    def _softmax(logits: _FakeTensor, dim: int = 1) -> _FakeTensor:
        arr = logits._arr
        exp = np.exp(arr - np.max(arr, axis=dim, keepdims=True))
        return _FakeTensor(exp / np.sum(exp, axis=dim, keepdims=True))

    def _argmax(values: _FakeTensor, dim: int = 1) -> _FakeTensor:
        return _FakeTensor(np.argmax(values._arr, axis=dim))

    class _FakeModel:
        def eval(self) -> None:
            return None

        def __call__(self, _images: _FakeTensor) -> Dict[str, _FakeTensor]:
            return {"logits": _FakeTensor([[0.1, 0.8, 0.1]])}

    def _fake_create_dataloaders(**kwargs: Any):
        captured.update(kwargs)
        val_loader = [(_FakeTensor([[1.0]]), _FakeTensor([1]))]
        return None, val_loader

    fake_torch = types.SimpleNamespace(
        cuda=types.SimpleNamespace(is_available=lambda: False),
        no_grad=lambda: _FakeNoGrad(),
        softmax=_softmax,
        argmax=_argmax,
    )
    fake_dataset_module = types.SimpleNamespace(create_dataloaders=_fake_create_dataloaders)
    fake_model_module = types.SimpleNamespace(
        load_pretrained_model=lambda *_args, **_kwargs: _FakeModel()
    )

    originals: Dict[str, Any] = {}
    for name, module in {
        "torch": fake_torch,
        "trainer.fer_finetune.dataset": fake_dataset_module,
        "trainer.fer_finetune.model_efficientnet": fake_model_module,
    }.items():
        originals[name] = sys.modules.get(name)
        sys.modules[name] = module

    try:
        output = pipeline._collect_predictions(  # type: ignore[attr-defined]
            checkpoint_path=pipeline.Path("/tmp/fake_checkpoint.pth"),
            data_root="/tmp/videos",
            class_names=["happy", "sad", "neutral"],
            input_size=224,
            batch_size=2,
            num_workers=0,
            run_id="run_0007",
            frames_per_video=10,
        )
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original

    assert captured["run_id"] == "run_0007"
    assert captured["frames_per_video"] == 10
    assert output["y_true"].tolist() == [1]


def test_normalize_run_type_accepts_aliases() -> None:
    assert pipeline._normalize_run_type("train") == "training"  # type: ignore[attr-defined]
    assert pipeline._normalize_run_type("validation") == "validation"  # type: ignore[attr-defined]
    assert pipeline._normalize_run_type("test") == "test"  # type: ignore[attr-defined]


def test_normalize_run_type_rejects_invalid_value() -> None:
    with pytest.raises(SystemExit):
        pipeline._normalize_run_type("evaluate")  # type: ignore[attr-defined]


def test_resolve_artifact_dir_partitions_variant_run_type_and_run_id(tmp_path) -> None:
    resolved = pipeline._resolve_artifact_dir(  # type: ignore[attr-defined]
        output_dir=str(tmp_path),
        variant="variant_2",
        run_type="validation",
        run_id="run_0042",
    )
    assert resolved == tmp_path / "variant_2" / "validation" / "run_0042"


def test_write_dashboard_run_payload_creates_expected_json(tmp_path) -> None:
    pred_path = tmp_path / "variant_1" / "training" / "run_0001" / "predictions.npz"
    gate_path = tmp_path / "variant_1" / "training" / "run_0001" / "gate_a.json"
    pred_path.parent.mkdir(parents=True, exist_ok=True)
    pred_path.write_text("preds")
    gate_path.write_text("{}")

    payload_path = pipeline._write_dashboard_run_payload(  # type: ignore[attr-defined]
        output_dir=str(tmp_path),
        variant="variant_1",
        run_type="training",
        run_id="run_0001",
        gate_report={
            "overall_pass": True,
            "metrics": {"f1_macro": 0.91},
            "gates": {"macro_f1": True},
        },
        predictions_path=pred_path,
        gate_path=gate_path,
        onnx_path=None,
    )

    assert payload_path.exists()
    payload = pipeline.json.loads(payload_path.read_text())
    assert payload["run_id"] == "run_0001"
    assert payload["model_variant"] == "variant_1"
    assert payload["run_type"] == "training"
    assert payload["gate_a_metrics"]["f1_macro"] == 0.91
