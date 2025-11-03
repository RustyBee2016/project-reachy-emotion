"""Prometheus metrics primitives for promotion workflows."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

from .metrics_registry import get_registry

REGISTRY = get_registry()

PROMOTION_OPERATION_COUNTER = Counter(
    "promotion_operations_total",
    "Number of promotion operations, grouped by action and outcome.",
    labelnames=("action", "outcome"),
    registry=REGISTRY,
)

PROMOTION_OPERATION_DURATION = Histogram(
    "promotion_operation_duration_seconds",
    "Duration of promotion operations in seconds, grouped by action.",
    labelnames=("action",),
    registry=REGISTRY,
)

PROMOTION_FILESYSTEM_FAILURES = Counter(
    "promotion_filesystem_failures_total",
    "Total filesystem failures encountered during promotion operations.",
    labelnames=("action",),
    registry=REGISTRY,
)


def get_metric_sample(metric_name: str, labels: dict[str, str] | None = None) -> float | None:
    """Lookup a sample value from the shared registry for tests."""

    return REGISTRY.get_sample_value(metric_name, labels or {})


def reset_metrics() -> None:
    """Clear all recorded promotion metrics (useful for tests)."""

    PROMOTION_OPERATION_COUNTER.clear()
    PROMOTION_OPERATION_DURATION.clear()
    PROMOTION_FILESYSTEM_FAILURES.clear()
