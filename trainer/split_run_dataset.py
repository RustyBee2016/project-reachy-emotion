#!/usr/bin/env python3
"""Split run-scoped extracted frames into train/validation datasets by moving files.

Example:
    python trainer/split_run_dataset.py --run-id run_0007 --videos-root /media/.../videos
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trainer.prepare_dataset import DatasetPreparer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Move run frames into train/valid datasets")
    parser.add_argument("--run-id", required=True, help="Run ID in run_xxxx format")
    parser.add_argument(
        "--videos-root",
        default="/media/rusty_admin/project_data/reachy_emotion/videos",
        help="Videos base root containing train/, test/, manifests/",
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.9,
        help="Fraction moved into train_ds_<run_id> (default: 0.9)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional seed for deterministic splitting",
    )
    parser.add_argument(
        "--keep-valid-prefix",
        action="store_true",
        help="Keep emotion label prefixes on files moved to valid_ds_<run_id>",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    preparer = DatasetPreparer(str(Path(args.videos_root)))
    result = preparer.split_run_dataset(
        args.run_id,
        train_ratio=args.train_ratio,
        seed=args.seed,
        strip_valid_labels=not args.keep_valid_prefix,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
