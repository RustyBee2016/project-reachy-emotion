"""Manifest orchestration primitives for training workflows."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol


class ManifestError(RuntimeError):
    """Raised when manifest orchestration cannot be completed."""


class ManifestBackend(Protocol):
    """Protocol describing concrete manifest orchestration backends."""

    def schedule_rebuild(self, *, reason: str, run_id: str | None) -> None:
        """Trigger a rebuild of the training manifest."""

    def reset(self, *, reason: str, run_id: str | None) -> None:
        """Reset manifest state; used during full rehydration."""


@dataclass(slots=True)
class LoggingManifestBackend:
    """Default backend that logs manifest operations for observability."""

    logger: logging.Logger

    def schedule_rebuild(self, *, reason: str, run_id: str | None) -> None:  # noqa: D401
        self.logger.info(
            "manifest_schedule_rebuild",
            extra={"reason": reason, "run_id": run_id},
        )

    def reset(self, *, reason: str, run_id: str | None) -> None:  # noqa: D401
        self.logger.info(
            "manifest_reset",
            extra={"reason": reason, "run_id": run_id},
        )


def get_default_backend(logger: logging.Logger | None = None) -> ManifestBackend:
    """Return the fallback manifest backend used by the promotion service."""

    logger = logger or logging.getLogger(__name__)
    return LoggingManifestBackend(logger)
