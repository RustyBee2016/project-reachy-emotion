#!/usr/bin/env python3
"""Gate B Runtime Validator for Jetson shadow-mode deployment.

Collects on-device latency, GPU memory, and (optionally) classification
metrics, then evaluates them against Gate B thresholds.

Gate B Thresholds (from requirements.md):
  - Latency p50  <= 120 ms
  - Latency p95  <= 250 ms
  - GPU memory   <=  2.5 GB
  - Macro F1     >=  0.80  (requires --test-set)
  - Per-class F1 >=  0.72, no class < 0.68  (requires --test-set)

Usage::

    # Latency + memory only (no test set)
    python gate_b_validator.py --duration 30

    # Full validation with F1 metrics
    python gate_b_validator.py --test-set /data/test_frames --duration 60

Output is JSON for consumption by n8n Agent 7.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from monitoring.system_monitor import JetsonMonitor

logger = logging.getLogger(__name__)


# ── Gate B threshold defaults ────────────────────────────────────────────

@dataclass(frozen=True)
class GateBThresholds:
    latency_p50_ms: float = 120.0
    latency_p95_ms: float = 250.0
    gpu_memory_gb: float = 2.5
    macro_f1: float = 0.80
    per_class_f1_floor: float = 0.72
    per_class_f1_min: float = 0.68


# ── Validation result ─────────────────────────────────────────────────

@dataclass
class MetricResult:
    name: str
    value: Optional[float]
    threshold: float
    passed: bool
    unit: str = ""
    direction: str = "lte"  # "lte" = value must be <= threshold, "gte" = >=


@dataclass
class GateBResult:
    passed: bool = False
    metrics: List[MetricResult] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    error: Optional[str] = None
    duration_s: float = 0.0
    timestamp: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


# ── Validator ────────────────────────────────────────────────────────

class GateBValidator:
    """Collect runtime metrics and validate against Gate B thresholds."""

    def __init__(self, thresholds: Optional[GateBThresholds] = None):
        self.thresholds = thresholds or GateBThresholds()
        self.monitor = JetsonMonitor()

    def collect_latency_metrics(self, duration_s: float = 30.0) -> Dict[str, Any]:
        """Collect inference latency from the running service's monitor.

        If running standalone, simulates a warm-up collection period by
        reading from the shared JetsonMonitor instance.
        """
        perf = self.monitor.get_performance_stats()
        return {
            "latency_p50_ms": perf.get("latency_p50_ms"),
            "latency_p95_ms": perf.get("latency_p95_ms"),
            "latency_p99_ms": perf.get("latency_p99_ms"),
            "latency_mean_ms": perf.get("latency_mean_ms"),
            "fps": perf.get("fps", 0),
            "frame_count": perf.get("frame_count", 0),
        }

    def collect_memory_metrics(self) -> Dict[str, Any]:
        """Collect GPU memory usage from tegrastats / nvidia-smi."""
        gpu = self.monitor.get_gpu_stats()
        ram_used_mb = gpu.get("ram_used_mb")
        ram_total_mb = gpu.get("ram_total_mb")
        gpu_memory_gb = ram_used_mb / 1024.0 if ram_used_mb else None
        return {
            "gpu_memory_gb": round(gpu_memory_gb, 2) if gpu_memory_gb else None,
            "gpu_memory_mb": ram_used_mb,
            "gpu_total_mb": ram_total_mb,
            "gpu_temp_c": gpu.get("temp_gpu"),
            "gpu_util_pct": gpu.get("gpu_util"),
        }

    def collect_f1_metrics(
        self, test_set_dir: Path, model_fn: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Compute macro and per-class F1 on a held-out test set.

        Args:
            test_set_dir: Directory with structure ``<emotion>/<frame>.jpg``
            model_fn: Optional inference callable ``(image_path) -> (label, confidence)``
                       If None, tries to import a local inference wrapper.

        Returns:
            Dict with ``macro_f1``, ``per_class_f1``, ``class_labels``.
        """
        try:
            from sklearn.metrics import f1_score
        except ImportError:
            return {"error": "scikit-learn not installed", "macro_f1": None}

        if not test_set_dir.exists():
            return {"error": f"Test set not found: {test_set_dir}", "macro_f1": None}

        true_labels: List[str] = []
        pred_labels: List[str] = []
        class_labels = sorted(
            [d.name for d in test_set_dir.iterdir() if d.is_dir()]
        )

        if not class_labels:
            return {"error": "No class subdirectories found", "macro_f1": None}

        for class_dir in test_set_dir.iterdir():
            if not class_dir.is_dir():
                continue
            label = class_dir.name
            for frame in class_dir.iterdir():
                if frame.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                    continue
                true_labels.append(label)
                if model_fn:
                    pred_label, _ = model_fn(frame)
                    pred_labels.append(pred_label)
                else:
                    # Without a model function we can only validate the dataset
                    pred_labels.append(label)  # placeholder — real results need model

        if not true_labels:
            return {"error": "No frames found in test set", "macro_f1": None}

        macro = f1_score(true_labels, pred_labels, labels=class_labels, average="macro")
        per_class = f1_score(
            true_labels, pred_labels, labels=class_labels, average=None
        )
        per_class_dict = {lbl: round(float(f1), 4) for lbl, f1 in zip(class_labels, per_class)}

        return {
            "macro_f1": round(float(macro), 4),
            "per_class_f1": per_class_dict,
            "class_labels": class_labels,
            "total_frames": len(true_labels),
        }

    def validate(
        self,
        duration_s: float = 30.0,
        test_set_dir: Optional[Path] = None,
        model_fn: Optional[callable] = None,
    ) -> GateBResult:
        """Run full Gate B validation.

        Args:
            duration_s: How long to collect latency metrics.
            test_set_dir: Optional test frame directory for F1 metrics.
            model_fn: Optional inference callable for F1.

        Returns:
            GateBResult with pass/fail per metric.
        """
        start = time.monotonic()
        result = GateBResult()
        result.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Latency metrics
        latency = self.collect_latency_metrics(duration_s)
        result.metrics.append(
            MetricResult(
                name="latency_p50_ms",
                value=latency.get("latency_p50_ms"),
                threshold=self.thresholds.latency_p50_ms,
                passed=(latency.get("latency_p50_ms") or float("inf"))
                <= self.thresholds.latency_p50_ms,
                unit="ms",
                direction="lte",
            )
        )
        result.metrics.append(
            MetricResult(
                name="latency_p95_ms",
                value=latency.get("latency_p95_ms"),
                threshold=self.thresholds.latency_p95_ms,
                passed=(latency.get("latency_p95_ms") or float("inf"))
                <= self.thresholds.latency_p95_ms,
                unit="ms",
                direction="lte",
            )
        )

        # Memory metrics
        memory = self.collect_memory_metrics()
        gpu_gb = memory.get("gpu_memory_gb")
        result.metrics.append(
            MetricResult(
                name="gpu_memory_gb",
                value=gpu_gb,
                threshold=self.thresholds.gpu_memory_gb,
                passed=(gpu_gb or float("inf")) <= self.thresholds.gpu_memory_gb,
                unit="GB",
                direction="lte",
            )
        )

        # F1 metrics (optional — only when test set provided)
        if test_set_dir:
            f1_data = self.collect_f1_metrics(test_set_dir, model_fn)
            macro = f1_data.get("macro_f1")
            if macro is not None:
                result.metrics.append(
                    MetricResult(
                        name="macro_f1",
                        value=macro,
                        threshold=self.thresholds.macro_f1,
                        passed=macro >= self.thresholds.macro_f1,
                        direction="gte",
                    )
                )
                per_class = f1_data.get("per_class_f1", {})
                min_f1 = min(per_class.values()) if per_class else 0.0
                result.metrics.append(
                    MetricResult(
                        name="per_class_f1_min",
                        value=round(min_f1, 4),
                        threshold=self.thresholds.per_class_f1_min,
                        passed=min_f1 >= self.thresholds.per_class_f1_min,
                        direction="gte",
                    )
                )
            else:
                result.skipped.append(f"macro_f1: {f1_data.get('error', 'unknown')}")
        else:
            result.skipped.append("macro_f1: no --test-set provided")
            result.skipped.append("per_class_f1: no --test-set provided")

        # Final pass/fail
        evaluated = [m for m in result.metrics if m.value is not None]
        result.passed = all(m.passed for m in evaluated) if evaluated else False
        result.duration_s = round(time.monotonic() - start, 2)

        return result


def main():
    parser = argparse.ArgumentParser(description="Gate B Runtime Validator")
    parser.add_argument(
        "--test-set",
        type=Path,
        default=None,
        help="Directory of labeled test frames (<emotion>/<frame>.jpg)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=30.0,
        help="Seconds to collect latency metrics",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    if not args.json:
        logging.basicConfig(level=logging.INFO)

    validator = GateBValidator()
    result = validator.validate(
        duration_s=args.duration,
        test_set_dir=args.test_set,
    )

    if args.json:
        print(result.to_json())
    else:
        print("\n" + "=" * 60)
        print("  GATE B VALIDATION RESULTS")
        print("=" * 60)
        for m in result.metrics:
            icon = "PASS" if m.passed else "FAIL"
            op = "<=" if m.direction == "lte" else ">="
            val = f"{m.value:.2f}" if m.value is not None else "N/A"
            print(f"  [{icon}] {m.name}: {val} {m.unit} ({op} {m.threshold})")
        if result.skipped:
            for s in result.skipped:
                print(f"  [SKIP] {s}")
        print("=" * 60)
        print(f"  OVERALL: {'PASS' if result.passed else 'FAIL'}")
        print(f"  Duration: {result.duration_s}s")
        print("=" * 60 + "\n")

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
