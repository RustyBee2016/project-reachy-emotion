"""Router accessors for both Media Mover and Gateway services.

This module used to eagerly import routers which, in turn, pulled in
dependencies only available on newer Python runtimes (e.g. dataclasses with
``slots=``). When running the lightweight gateway on Ubuntu 2 (Python 3.8),
those imports caused ``TypeError`` at startup. To avoid that, routers are now
loaded lazily when accessed via ``__getattr__``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["gateway_router", "media_router", "metrics_router"]


if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from apps.api.app.routers.metrics import router as metrics_router
    from apps.api.routers.gateway import router as gateway_router
    from apps.api.routers.media import router as media_router


def __getattr__(name: str) -> Any:
    """Dynamically import routers on first access."""

    if name == "gateway_router":
        from apps.api.routers.gateway import router as _gateway_router

        return _gateway_router
    if name == "media_router":
        from apps.api.routers.media import router as _media_router

        return _media_router
    if name == "metrics_router":
        from apps.api.app.routers.metrics import router as _metrics_router

        return _metrics_router

    raise AttributeError(name)
