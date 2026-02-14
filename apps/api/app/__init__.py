"""Media Mover FastAPI application package.

Avoid importing the heavy ``.main`` module at package import time so the
gateway service (running on Ubuntu 2 with Python 3.8) can import lightweight
utilities such as ``metrics_registry`` without pulling in newer language
features or filesystem dependencies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["app", "create_app"]


if TYPE_CHECKING:  # pragma: no cover - assist static type checkers
    from .main import app, create_app


def __getattr__(name: str) -> Any:
    """Lazily expose ``app`` and ``create_app`` when requested."""

    if name in {"app", "create_app"}:
        from .main import app as _app, create_app as _create_app

        return _app if name == "app" else _create_app

    raise AttributeError(name)
