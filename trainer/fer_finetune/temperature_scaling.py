"""
Post-hoc Temperature Scaling for calibration improvement.

Temperature scaling learns a single scalar T on a held-out calibration set
that divides logits before softmax:  p = softmax(z / T).

- T > 1 softens predictions (reduces overconfidence)
- T < 1 sharpens predictions (increases confidence)
- T = 1 is the identity (no change)

This is a zero-cost inference technique — it does not change the model's
accuracy or predicted class labels (argmax is preserved), only the
confidence scores.  It is the simplest and most widely-used post-hoc
calibration method (Guo et al., 2017).

Usage:
    from trainer.fer_finetune.temperature_scaling import (
        learn_temperature,
        apply_temperature,
    )

    # Learn T from validation logits + labels
    T = learn_temperature(val_logits, val_labels)

    # Apply at inference time
    calibrated_probs = apply_temperature(test_logits, T)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

logger = logging.getLogger(__name__)


class _TemperatureModel(nn.Module):
    """Thin wrapper that holds a learnable temperature parameter.

    Uses log-parameterization to guarantee T > 0:
        T = exp(log_temperature)
    Initialized at log(1.5) ≈ 0.405 since overconfident models
    typically need T > 1 (softening).
    """

    def __init__(self, init_temp: float = 1.5) -> None:
        super().__init__()
        self.log_temperature = nn.Parameter(
            torch.tensor([float(np.log(init_temp))])
        )

    @property
    def temperature(self) -> torch.Tensor:
        return self.log_temperature.exp()

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        return logits / self.temperature


def learn_temperature(
    logits: torch.Tensor,
    labels: torch.Tensor,
    *,
    lr: float = 0.01,
    max_iter: int = 200,
    tol: float = 1e-7,
) -> float:
    """Learn optimal temperature T by minimizing NLL on calibration data.

    Uses log-parameterization so T = exp(log_T) is always positive.
    Initialized at T=1.5 (slight softening, typical for overconfident models).

    Args:
        logits: Raw model logits, shape [N, C].
        labels: Ground-truth class indices, shape [N].
        lr: Learning rate for LBFGS optimizer.
        max_iter: Maximum optimization iterations.
        tol: Convergence tolerance.

    Returns:
        Optimal temperature scalar (float, always > 0).
    """
    temp_model = _TemperatureModel(init_temp=1.5)
    if logits.is_cuda:
        temp_model = temp_model.cuda()

    nll_criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.LBFGS(
        temp_model.parameters(), lr=lr, max_iter=max_iter, tolerance_change=tol,
    )

    best_loss = float("inf")
    best_T = 1.5

    def _closure():
        nonlocal best_loss, best_T
        optimizer.zero_grad()
        scaled = temp_model(logits)
        loss = nll_criterion(scaled, labels)
        loss.backward()
        current_T = temp_model.temperature.item()
        if loss.item() < best_loss:
            best_loss = loss.item()
            best_T = current_T
        return loss

    optimizer.step(_closure)
    optimal_T = temp_model.temperature.item()

    # Sanity check — T should be in a reasonable range [0.01, 100]
    if not (0.01 <= optimal_T <= 100.0):
        logger.warning(
            f"Learned T={optimal_T:.4f} is outside [0.01, 100]. "
            f"Using best seen T={best_T:.4f} instead."
        )
        optimal_T = best_T

    logger.info(f"Learned temperature T = {optimal_T:.6f} (NLL={best_loss:.6f})")
    return optimal_T


def apply_temperature(
    logits: np.ndarray,
    temperature: float,
) -> np.ndarray:
    """Apply temperature scaling to logits and return calibrated probabilities.

    Args:
        logits: Raw logits array, shape [N, C].
        temperature: Learned temperature scalar.

    Returns:
        Calibrated probability array, shape [N, C].
    """
    scaled = logits / temperature
    # Numerically stable softmax
    exp_scaled = np.exp(scaled - np.max(scaled, axis=1, keepdims=True))
    return exp_scaled / np.sum(exp_scaled, axis=1, keepdims=True)


def collect_logits(
    checkpoint_path: str,
    data_root: str,
    class_names: List[str],
    input_size: int,
    batch_size: int,
    num_workers: int,
    *,
    val_dir: Optional[str] = None,
    val_dataset_type: str = "emotion",
    ground_truth_manifest: Optional[str] = None,
    run_id: Optional[str] = None,
    frames_per_video: int = 1,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run forward pass and collect raw logits, labels, and probabilities.

    Returns:
        Tuple of (logits [N,C], labels [N], probs [N,C]).
    """
    from trainer.fer_finetune.model_efficientnet import load_pretrained_model

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = load_pretrained_model(
        checkpoint_path, num_classes=len(class_names), device=device,
    )

    if ground_truth_manifest:
        from trainer.fer_finetune.dataset import EmotionDataset, get_val_transforms

        dataset = EmotionDataset(
            data_dir=data_root,
            split="",
            transform=get_val_transforms(input_size),
            class_names=class_names,
            frame_sampling="middle",
            frames_per_video=frames_per_video,
            manifest_path=ground_truth_manifest,
        )
        loader = DataLoader(
            dataset,
            batch_size=batch_size * 2,
            shuffle=False,
            num_workers=num_workers,
            pin_memory=True,
        )
    else:
        from trainer.fer_finetune.dataset import create_dataloaders

        _, loader = create_dataloaders(
            data_dir=data_root,
            batch_size=batch_size,
            num_workers=num_workers,
            input_size=input_size,
            class_names=class_names,
            frame_sampling_train="random",
            frame_sampling_val="middle",
            run_id=run_id,
            frames_per_video=frames_per_video,
            val_dir=val_dir,
            val_dataset_type=val_dataset_type,
        )

    all_logits: List[np.ndarray] = []
    all_labels: List[int] = []
    all_probs: List[np.ndarray] = []

    model.eval()
    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            outputs = model(images)
            logits = outputs["logits"] if isinstance(outputs, dict) else outputs
            probs = torch.softmax(logits, dim=1)

            all_logits.extend(logits.cpu().numpy())
            all_labels.extend(labels.cpu().numpy().tolist())
            all_probs.extend(probs.cpu().numpy())

    return (
        np.array(all_logits, dtype=np.float32),
        np.array(all_labels, dtype=np.int64),
        np.array(all_probs, dtype=np.float32),
    )


def calibrate_checkpoint(
    checkpoint_path: str,
    calibration_data_dir: str,
    class_names: List[str],
    input_size: int = 224,
    batch_size: int = 32,
    num_workers: int = 0,
    *,
    val_dir: Optional[str] = None,
    val_dataset_type: str = "emotion",
    ground_truth_manifest: Optional[str] = None,
    run_id: Optional[str] = None,
    frames_per_video: int = 1,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """End-to-end: learn T on calibration set and save results.

    Args:
        checkpoint_path: Path to trained model checkpoint.
        calibration_data_dir: Root data directory for calibration set.
        class_names: List of class names.
        input_size: Image input size.
        batch_size: Batch size for inference.
        num_workers: DataLoader workers.
        val_dir: Explicit validation directory.
        val_dataset_type: Dataset type for validation.
        ground_truth_manifest: Optional manifest for test-set evaluation.
        run_id: Run ID for dataset resolution.
        frames_per_video: Frames per video for dataset.
        output_path: Where to save temperature_scaling.json.

    Returns:
        Dict with learned temperature, before/after ECE, and file path.
    """
    logger.info(f"Collecting logits from {checkpoint_path}")
    logits, labels, probs_before = collect_logits(
        checkpoint_path=checkpoint_path,
        data_root=calibration_data_dir,
        class_names=class_names,
        input_size=input_size,
        batch_size=batch_size,
        num_workers=num_workers,
        val_dir=val_dir,
        val_dataset_type=val_dataset_type,
        ground_truth_manifest=ground_truth_manifest,
        run_id=run_id,
        frames_per_video=frames_per_video,
    )

    logger.info(f"Learning temperature on {len(labels)} samples")
    logits_t = torch.from_numpy(logits)
    labels_t = torch.from_numpy(labels)
    if torch.cuda.is_available():
        logits_t = logits_t.cuda()
        labels_t = labels_t.cuda()

    temperature = learn_temperature(logits_t, labels_t)

    # Compute calibrated probabilities
    probs_after = apply_temperature(logits, temperature)

    # Recompute predictions from calibrated probs (argmax unchanged)
    preds_after = np.argmax(probs_after, axis=1)

    # Compute before/after calibration metrics
    from trainer.fer_finetune.evaluate import compute_calibration_metrics

    cal_before = compute_calibration_metrics(labels.tolist(), probs_before)
    cal_after = compute_calibration_metrics(labels.tolist(), probs_after)

    result = {
        "temperature": temperature,
        "samples": len(labels),
        "calibration_before": {
            "ece": cal_before.get("ece"),
            "brier": cal_before.get("brier"),
            "mce": cal_before.get("mce"),
        },
        "calibration_after": {
            "ece": cal_after.get("ece"),
            "brier": cal_after.get("brier"),
            "mce": cal_after.get("mce"),
        },
    }

    logger.info(
        f"Temperature scaling: T={temperature:.4f}, "
        f"ECE {cal_before['ece']:.4f} → {cal_after['ece']:.4f}, "
        f"Brier {cal_before['brier']:.4f} → {cal_after['brier']:.4f}"
    )

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2))
        result["output_path"] = str(out)
        logger.info(f"Saved temperature scaling results → {out}")

    return result
