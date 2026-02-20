"""Helpers for resolving training/evaluation data roots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ResolvedDataRoots:
    """Resolved data roots for training and validation datasets."""

    train_root: Path
    val_root: Path
    uses_run_scoped_train: bool
    uses_run_scoped_val: bool


def resolve_training_data_roots(data_root: str, run_id: Optional[str] = None) -> ResolvedDataRoots:
    """Resolve data roots for a training run.

    Layout preference:
    - train: <data_root>/train/run/<run_id> when present, else <data_root>/train
    - val: <data_root>/test/<run_id> when present, else <data_root>/test
    """

    root = Path(data_root)
    default_train = root / "train"
    default_val = root / "test"

    if not run_id:
        return ResolvedDataRoots(
            train_root=default_train,
            val_root=default_val,
            uses_run_scoped_train=False,
            uses_run_scoped_val=False,
        )

    run_train = root / "train" / "run" / run_id
    run_val = root / "test" / run_id

    return ResolvedDataRoots(
        train_root=run_train if run_train.exists() else default_train,
        val_root=run_val if run_val.exists() else default_val,
        uses_run_scoped_train=run_train.exists(),
        uses_run_scoped_val=run_val.exists(),
    )
