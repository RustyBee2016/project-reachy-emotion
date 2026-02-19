"""Filesystem utilities for atomic media promotions."""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence


class FileMoverError(RuntimeError):
    """Raised when a filesystem transition fails."""


@dataclass(frozen=True)
class FileTransition:
    """Represents a filesystem transition for a video."""

    video_id: str  # UUID stored as string
    source: Path  # relative to root, pre-operation
    destination: Path  # relative to root, post-operation
    operation: Literal["move", "copy"]


class FileMover:
    """Performs atomic file moves and copies within the videos root."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        """Return the root directory for media files."""

        return self._root

    def stage_to_train(self, *, video_id: str, file_path: str, label: str) -> FileTransition:
        """Move a clip from temp/ into train/<label>/ atomically."""

        relative, destination_relative, source, destination = self._prepare_stage(file_path, label)
        self._ensure_source_exists(source, video_id)
        self._atomic_move(video_id, source, destination)
        return FileTransition(
            video_id=video_id,
            source=relative,
            destination=destination_relative,
            operation="move",
        )

    def plan_stage_to_train(self, *, video_id: str, file_path: str, label: str) -> FileTransition:
        """Preview temp -> train/<label> move without mutating state."""

        relative, destination_relative, source, _ = self._prepare_stage(file_path, label)
        self._ensure_source_exists(source, video_id)
        return FileTransition(
            video_id=video_id,
            source=relative,
            destination=destination_relative,
            operation="move",
        )

    def copy_to_split(
        self,
        *,
        video_id: str,
        file_path: str,
        target_split: str,
        run_id: str,
    ) -> FileTransition:
        """Copy run-scoped media into consolidated train/run and test/run directories."""

        (
            relative,
            destination_relative,
            source,
            destination,
        ) = self._prepare_copy(file_path, target_split, run_id)
        self._ensure_source_exists(source, video_id)
        self._atomic_copy(video_id, source, destination)
        return FileTransition(
            video_id=video_id,
            source=relative,
            destination=destination_relative,
            operation="copy",
        )

    def plan_copy_to_split(
        self,
        *,
        video_id: str,
        file_path: str,
        target_split: str,
        run_id: str,
    ) -> FileTransition:
        """Preview copy_to_split() without mutating state."""

        (
            relative,
            destination_relative,
            source,
            _,
        ) = self._prepare_copy(file_path, target_split, run_id)
        self._ensure_source_exists(source, video_id)
        return FileTransition(
            video_id=video_id,
            source=relative,
            destination=destination_relative,
            operation="copy",
        )

    def rollback(self, transitions: Sequence[FileTransition]) -> None:
        """Best-effort rollback for previously applied transitions."""

        for transition in reversed(list(transitions)):
            source = self._root / transition.source
            destination = self._root / transition.destination
            try:
                if transition.operation == "move":
                    if destination.exists():
                        source.parent.mkdir(parents=True, exist_ok=True)
                        os.replace(destination, source)
                        self._fsync_directory(source.parent)
                elif transition.operation == "copy":
                    if destination.exists():
                        destination.unlink()
                        self._fsync_directory(destination.parent)
            except Exception:  # noqa: BLE001 - best effort rollback
                continue

    @staticmethod
    def _to_relative_path(raw: str) -> Path:
        path = Path(raw)
        if path.is_absolute():
            raise FileMoverError("File paths must be repository-relative, not absolute.")
        return path

    def _prepare_stage(
        self,
        file_path: str,
        label: str,
    ) -> tuple[Path, Path, Path, Path]:
        relative = self._to_relative_path(file_path)
        if not relative.parts:
            raise FileMoverError("Video file_path is empty.")

        if relative.parts[0] != "temp":
            raise FileMoverError(f"File path {file_path} does not start with 'temp'.")

        normalized_label = label.strip().lower()
        if normalized_label not in {"happy", "sad", "neutral"}:
            raise FileMoverError(f"Unsupported label '{label}'.")

        destination_relative = Path("train") / normalized_label / relative.name
        source = self._root / relative
        destination = self._root / destination_relative
        return relative, destination_relative, source, destination

    def _prepare_copy(
        self,
        file_path: str,
        target_split: str,
        run_id: str,
    ) -> tuple[Path, Path, Path, Path]:
        relative = self._to_relative_path(file_path)
        normalized_split = target_split.strip().lower()
        if normalized_split not in {"train", "test"}:
            raise FileMoverError(f"Unsupported target_split '{target_split}'.")

        normalized_run_id = run_id.strip().lower()
        if not normalized_run_id.startswith("run_"):
            raise FileMoverError("run_id must follow run_xxxx naming.")

        if not relative.parts:
            raise FileMoverError("Video file_path is empty.")
        if relative.parts[0] not in {"train", "test"}:
            raise FileMoverError(
                f"File path {file_path} must originate in 'train' or 'test'."
            )

        suffix_parts = list(relative.parts[1:] if len(relative.parts) > 1 else (relative.name,))
        if normalized_run_id in suffix_parts:
            suffix_parts.remove(normalized_run_id)

        if normalized_split == "train":
            destination_relative = Path("train") / "run" / normalized_run_id / Path(*suffix_parts)
        else:
            destination_relative = Path("test") / normalized_run_id / Path(*suffix_parts)
        source = self._root / relative
        destination = self._root / destination_relative
        return relative, destination_relative, source, destination

    def _ensure_source_exists(self, source: Path, video_id: str) -> None:
        if not source.exists():
            raise FileMoverError(f"Source file missing for video {video_id}: {source}")

    def _atomic_move(self, video_id: str, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        tmp_destination = destination.with_suffix(destination.suffix + f".tmp-{uuid.uuid4().hex}")
        try:
            os.replace(source, tmp_destination)
            self._fsync_path(tmp_destination)
            os.replace(tmp_destination, destination)
            self._fsync_directory(destination.parent)
        except Exception as exc:  # noqa: BLE001
            if tmp_destination.exists():
                tmp_destination.unlink(missing_ok=True)
            raise FileMoverError(
                f"Failed to move {source} -> {destination}: {exc}"
            ) from exc

    def _atomic_copy(self, video_id: str, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        tmp_destination = destination.with_suffix(destination.suffix + f".tmp-{uuid.uuid4().hex}")
        temp_file_path: Path | None = None
        try:
            with source.open("rb") as src, tempfile.NamedTemporaryFile(
                dir=destination.parent,
                delete=False,
            ) as tmp_file:
                shutil.copyfileobj(src, tmp_file)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
                temp_file_path = Path(tmp_file.name)
            os.replace(temp_file_path, tmp_destination)
            self._fsync_path(tmp_destination)
            if destination.exists():
                destination.unlink()
            os.replace(tmp_destination, destination)
            self._fsync_directory(destination.parent)
        except Exception as exc:  # noqa: BLE001
            if temp_file_path and temp_file_path.exists():
                temp_file_path.unlink(missing_ok=True)
            if tmp_destination.exists():
                tmp_destination.unlink(missing_ok=True)
            raise FileMoverError(
                f"Failed to copy {source} -> {destination}: {exc}"
            ) from exc

    @staticmethod
    def _fsync_path(path: Path) -> None:
        try:
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
        except (OSError, ValueError):  # pragma: no cover - best effort
            return

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        try:
            dir_fd = os.open(path, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:  # pragma: no cover - best effort
            return
