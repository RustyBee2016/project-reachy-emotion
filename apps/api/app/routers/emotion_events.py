"""Emotion event endpoints for Phase 3 edge event persistence.

Receives, stores, and queries real-time emotion events from Jetson devices.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import EmotionEvent
from ..deps import get_db
from ..schemas.emotion_event import (
    EmotionEventCreate,
    EmotionEventData,
    EmotionEventStatsData,
)
from ..schemas.responses import create_success_response

router = APIRouter(prefix="/api/v1/events", tags=["emotion-events"])

logger = logging.getLogger(__name__)

ABSTENTION_THRESHOLD = 0.6


def _correlation_id(request: Request) -> str:
    return request.headers.get("X-Correlation-ID", "")


@router.post(
    "/emotion",
    status_code=status.HTTP_201_CREATED,
    summary="Record an emotion event from a Jetson device",
)
async def create_emotion_event(
    body: EmotionEventCreate,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    row = EmotionEvent(
        id=str(uuid.uuid4()),
        device_id=body.device_id,
        emotion=body.emotion,
        confidence=body.confidence,
        inference_ms=body.inference_ms,
        correlation_id=body.correlation_id,
        session_id=body.session_id,
        device_ts=body.ts,
        meta=body.meta,
    )
    session.add(row)
    await session.commit()

    data = EmotionEventData(
        id=row.id,
        device_id=row.device_id,
        emotion=row.emotion,
        confidence=row.confidence,
        inference_ms=row.inference_ms,
        correlation_id=row.correlation_id,
        session_id=row.session_id,
        device_ts=row.device_ts,
        created_at=row.created_at,
    )
    return create_success_response(data, _correlation_id(request))


@router.get(
    "/emotion",
    summary="Query emotion events with optional filters",
)
async def list_emotion_events(
    request: Request,
    device_id: Optional[str] = Query(None),
    emotion: Optional[str] = Query(None, pattern="^(happy|sad|neutral)$"),
    session_id: Optional[str] = Query(None),
    minutes: int = Query(60, ge=1, le=10080, description="Look-back window in minutes"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    stmt = select(EmotionEvent).where(EmotionEvent.created_at >= since)

    if device_id:
        stmt = stmt.where(EmotionEvent.device_id == device_id)
    if emotion:
        stmt = stmt.where(EmotionEvent.emotion == emotion)
    if session_id:
        stmt = stmt.where(EmotionEvent.session_id == session_id)

    stmt = stmt.order_by(EmotionEvent.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    rows = result.scalars().all()

    items = [
        EmotionEventData(
            id=r.id,
            device_id=r.device_id,
            emotion=r.emotion,
            confidence=r.confidence,
            inference_ms=r.inference_ms,
            correlation_id=r.correlation_id,
            session_id=r.session_id,
            device_ts=r.device_ts,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return create_success_response(items, _correlation_id(request))


@router.get(
    "/emotion/stats",
    summary="Aggregated emotion event statistics over a time window",
)
async def emotion_event_stats(
    request: Request,
    device_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    minutes: int = Query(60, ge=1, le=10080),
    session: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    base = select(EmotionEvent).where(EmotionEvent.created_at >= since)

    if device_id:
        base = base.where(EmotionEvent.device_id == device_id)
    if session_id:
        base = base.where(EmotionEvent.session_id == session_id)

    # Total count
    total_q = select(func.count()).select_from(base.subquery())
    total = (await session.execute(total_q)).scalar() or 0

    # Per-emotion counts
    emotion_q = (
        select(EmotionEvent.emotion, func.count())
        .where(EmotionEvent.created_at >= since)
    )
    if device_id:
        emotion_q = emotion_q.where(EmotionEvent.device_id == device_id)
    if session_id:
        emotion_q = emotion_q.where(EmotionEvent.session_id == session_id)
    emotion_q = emotion_q.group_by(EmotionEvent.emotion)
    emotion_result = await session.execute(emotion_q)
    by_emotion = {row[0]: row[1] for row in emotion_result.all()}

    # Averages
    avg_q = (
        select(
            func.avg(EmotionEvent.confidence),
            func.avg(EmotionEvent.inference_ms),
        )
        .where(EmotionEvent.created_at >= since)
    )
    if device_id:
        avg_q = avg_q.where(EmotionEvent.device_id == device_id)
    if session_id:
        avg_q = avg_q.where(EmotionEvent.session_id == session_id)
    avg_row = (await session.execute(avg_q)).one_or_none()
    avg_confidence = float(avg_row[0]) if avg_row and avg_row[0] else None
    avg_inference = float(avg_row[1]) if avg_row and avg_row[1] else None

    # Abstention count (confidence below threshold)
    abs_q = (
        select(func.count())
        .select_from(EmotionEvent)
        .where(
            EmotionEvent.created_at >= since,
            EmotionEvent.confidence < ABSTENTION_THRESHOLD,
        )
    )
    if device_id:
        abs_q = abs_q.where(EmotionEvent.device_id == device_id)
    if session_id:
        abs_q = abs_q.where(EmotionEvent.session_id == session_id)
    abstention_count = (await session.execute(abs_q)).scalar() or 0
    abstention_rate = abstention_count / total if total > 0 else None

    # Active devices
    dev_q = (
        select(func.distinct(EmotionEvent.device_id))
        .where(EmotionEvent.created_at >= since)
    )
    dev_result = await session.execute(dev_q)
    device_ids = [row[0] for row in dev_result.all()]

    data = EmotionEventStatsData(
        total_events=total,
        by_emotion=by_emotion,
        avg_confidence=avg_confidence,
        avg_inference_ms=avg_inference,
        abstention_count=abstention_count,
        abstention_rate=abstention_rate,
        device_ids=device_ids,
    )
    return create_success_response(data, _correlation_id(request))
