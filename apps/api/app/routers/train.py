"""Router for training pipeline endpoints.

Provides frame extraction and training run management. The extract-frames
endpoint bridges the web UI to the trainer/prepare_dataset.py module and
records each run in the database (training_run + training_selection tables).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import AppConfig, get_config
from ..db import models
from ..deps import get_db
from ..schemas.train import (
    ExtractFramesRequest,
    ExtractFramesResponse,
    TrainingRunStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/train", tags=["train"])

CORRELATION_ID_HEADER = "X-Correlation-ID"


def _resolve_correlation_id(request: Request) -> str:
    header_value = request.headers.get(CORRELATION_ID_HEADER)
    if header_value:
        return header_value.strip()
    return str(uuid4())


@router.post(
    "/extract-frames",
    status_code=status.HTTP_200_OK,
    response_model=ExtractFramesResponse,
)
async def extract_frames(
    payload: ExtractFramesRequest,
    request_ctx: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
    config: AppConfig = Depends(get_config),
):
    """Extract random frames from classified training videos.

    For each emotion class (happy, sad, neutral), samples N random frames
    from every video in train/<emotion>/ and stores them in:
      - train/<emotion>/<run_id>/  (per-class frames)
      - train/run/<run_id>/<emotion>/  (consolidated training dataset)

    Also creates a TrainingRun database record and links source videos
    via TrainingSelection rows.
    """
    correlation_id = _resolve_correlation_id(request_ctx)
    response.headers[CORRELATION_ID_HEADER] = correlation_id

    # Late import to avoid pulling OpenCV at module load time.
    from trainer.prepare_dataset import DatasetPreparer

    videos_root = config.videos_root
    preparer = DatasetPreparer(str(videos_root))

    if payload.frames_per_video != DatasetPreparer.FRAMES_PER_VIDEO:
        preparer.FRAMES_PER_VIDEO = payload.frames_per_video

    # Resolve run_id (auto-generate if not provided).
    try:
        run_id = preparer.resolve_run_id(payload.run_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": str(exc), "correlation_id": correlation_id},
        ) from exc

    # Collect source videos to validate before touching the database.
    source_videos = preparer._collect_source_videos()
    emotion_counts = {label: len(videos) for label, videos in source_videos.items()}
    total_videos = sum(emotion_counts.values())

    # Dry-run: report what would happen without extracting.
    if payload.dry_run:
        return ExtractFramesResponse(
            status="dry_run",
            run_id=run_id,
            train_count=total_videos * payload.frames_per_video,
            test_count=0,
            videos_processed=total_videos,
            frames_per_video=payload.frames_per_video,
            seed=payload.seed or 0,
            dataset_hash="",
            dry_run=True,
            emotion_counts=emotion_counts,
            frame_output_dirs={
                label: str(videos_root / "train" / label / run_id)
                for label in preparer.EMOTIONS
            },
            consolidated_dir=str(videos_root / "train" / "run" / run_id),
        )

    # Validate that source videos exist for all emotion classes.
    try:
        preparer._validate_source_videos(source_videos)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": str(exc), "correlation_id": correlation_id},
        ) from exc

    # Create TrainingRun record with status='sampling'.
    training_run = models.TrainingRun(
        run_id=run_id,
        strategy="frame_extraction",
        train_fraction=1.0,
        test_fraction=0.0,
        seed=payload.seed,
        status="sampling",
        started_at=datetime.now(timezone.utc),
        config={
            "frames_per_video": payload.frames_per_video,
            "correlation_id": correlation_id,
            "source_emotion_counts": emotion_counts,
        },
    )
    session.add(training_run)
    await session.flush()

    # Run the frame extraction (synchronous, CPU-bound).
    try:
        result = preparer.prepare_training_dataset(
            run_id=run_id,
            seed=payload.seed,
        )
    except Exception as exc:
        # Mark the run as failed.
        training_run.status = "failed"
        training_run.error_message = str(exc)
        training_run.completed_at = datetime.now(timezone.utc)
        await session.commit()
        logger.error(
            "Frame extraction failed for %s: %s",
            run_id, exc, exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"Frame extraction failed: {exc}", "correlation_id": correlation_id},
        ) from exc

    # Link source videos to the training run via TrainingSelection.
    # Query video table for files in train/<emotion>/ directories.
    for label, video_paths in source_videos.items():
        for video_path in video_paths:
            rel_path = str(video_path.relative_to(videos_root))
            stmt = sa.select(models.Video.video_id).where(
                models.Video.file_path == rel_path,
                models.Video.split == "train",
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is not None:
                selection = models.TrainingSelection(
                    run_id=run_id,
                    video_id=row,
                    target_split="train",
                )
                session.add(selection)

    # Update TrainingRun with completion data.
    training_run.status = "completed"
    training_run.completed_at = datetime.now(timezone.utc)
    training_run.dataset_hash = result.get("dataset_hash")
    training_run.metrics = {
        "train_count": result["train_count"],
        "test_count": result["test_count"],
        "videos_processed": result["videos_processed"],
        "frames_per_video": result["frames_per_video"],
        "emotion_counts": emotion_counts,
    }

    await session.commit()

    logger.info(
        "Frame extraction completed: run_id=%s videos=%d frames=%d hash=%s",
        run_id,
        result["videos_processed"],
        result["train_count"],
        result.get("dataset_hash", "")[:12],
    )

    return ExtractFramesResponse(
        status="completed",
        run_id=run_id,
        train_count=result["train_count"],
        test_count=result["test_count"],
        videos_processed=result["videos_processed"],
        frames_per_video=result["frames_per_video"],
        seed=result["seed"],
        dataset_hash=result.get("dataset_hash", ""),
        dry_run=False,
        emotion_counts=emotion_counts,
        frame_output_dirs={
            label: str(videos_root / "train" / label / run_id)
            for label in preparer.EMOTIONS
        },
        consolidated_dir=str(videos_root / "train" / "run" / run_id),
    )


@router.get(
    "/runs/{run_id}",
    response_model=TrainingRunStatus,
)
async def get_training_run(
    run_id: str,
    session: AsyncSession = Depends(get_db),
):
    """Retrieve the status of a training run by its run_id."""
    row = await session.get(models.TrainingRun, run_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": f"Training run not found: {run_id}"},
        )
    metrics = row.metrics or {}
    return TrainingRunStatus(
        run_id=row.run_id,
        status=row.status,
        train_count=metrics.get("train_count", 0),
        test_count=metrics.get("test_count", 0),
        videos_processed=metrics.get("videos_processed", 0),
        dataset_hash=row.dataset_hash,
        seed=row.seed,
        error_message=row.error_message,
    )
