"""Shared Prometheus registry utilities."""

from __future__ import annotations

from threading import Lock
from typing import Final

from prometheus_client import CollectorRegistry

__all__ = ["get_registry", "set_registry"]

_registry_lock: Final[Lock] = Lock()
_registry: CollectorRegistry | None = None


def get_registry() -> CollectorRegistry:
    """Return the process-wide Prometheus registry.

    Lazily instantiates a CollectorRegistry the first time it is requested so
    that multiple modules can coordinate on a single registry instance. This is
    helpful when combining built-in metrics with service-specific counters.
    """

    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = CollectorRegistry()
    return _registry


def set_registry(registry: CollectorRegistry | None) -> None:
    """Override the registry used by :func:`get_registry`.

    Primarily useful for testing scenarios where metrics should not be shared
    across test cases. Passing ``None`` resets the registry and causes the next
    call to :func:`get_registry` to create a fresh CollectorRegistry.
    """

    global _registry
    with _registry_lock:
        _registry = registry
