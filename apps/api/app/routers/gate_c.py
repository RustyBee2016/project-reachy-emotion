"""Gate C metrics and canary promotion logic.

Gate C thresholds (from requirements.md):
  - User-visible latency <= 300 ms end-to-end
  - Abstention rate     <= 20%
  - Complaints          <  1% of sessions

Endpoints:
  POST /api/v1/gate-c/session     — start or end a user session
  POST /api/v1/gate-c/complaint   — record a user complaint
  GET  /api/v1/gate-c/metrics     — compute Gate C metrics over a window
  GET  /api/v1/gate-c/validate    — pass/fail evaluation
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import EmotionEvent
from ..deps import get_db
from ..schemas.responses import SuccessResponse, create_success_response

router = APIRouter(prefix="/api/v1/gate-c", tags=["gate-c"])

logger = logging.getLogger(__name__)


# ── Gate C threshold defaults ───────────────────────────────────────

LATENCY_E2E_MAX_MS = 300.0
ABSTENTION_RATE_MAX = 0.20
COMPLAINT_RATE_MAX = 0.01
ABSTENTION_CONFIDENCE_THRESHOLD = 0.6


# ── Request / response schemas ──────────────────────────────────────

class SessionAction(BaseModel):
    device_id: str = Field(..., max_length=100)
    session_id: str = Field(..., max_length=64)
    action: str = Field(..., pattern="^(start|end)$")


class ComplaintRecord(BaseModel):
    device_id: str = Field(..., max_length=100)
    session_id: str = Field(..., max_length=64)
    reason: Optional[str] = Field(None, max_length=500)
    correlation_id: Optional[str] = Field(None, max_length=64)


class GateCMetrics(BaseModel):
    window_minutes: int
    total_events: int
    unique_sessions: int
    avg_inference_ms: Optional[float] = None
    latency_e2e_est_ms: Optional[float] = None
    abstention_count: int = 0
    abstention_rate: Optional[float] = None
    complaint_count: int = 0
    complaint_rate: Optional[float] = None


class GateCValidation(BaseModel):
    passed: bool
    metrics: GateCMetrics
    checks: dict


# ── In-memory complaint store (upgrade to DB table in production) ──
# Kept simple — complaints are low-volume and ephemeral during canary.

_complaints: list[dict] = []
_sessions: dict[str, dict] = {}  # session_id -> {device_id, started_at, ended_at}


def _correlation_id(request: Request) -> str:
    return request.headers.get("X-Correlation-ID", "")


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/session", status_code=status.HTTP_200_OK)
async def session_action(body: SessionAction, request: Request):
    now = datetime.now(timezone.utc)
    if body.action == "start":
        _sessions[body.session_id] = {
            "device_id": body.device_id,
            "started_at": now.isoformat(),
            "ended_at": None,
        }
    elif body.action == "end":
        if body.session_id in _sessions:
            _sessions[body.session_id]["ended_at"] = now.isoformat()

    return create_success_response(
        {"session_id": body.session_id, "action": body.action},
        _correlation_id(request),
    )


@router.post("/complaint", status_code=status.HTTP_201_CREATED)
async def record_complaint(body: ComplaintRecord, request: Request):
    entry = {
        "id": str(uuid.uuid4()),
        "device_id": body.device_id,
        "session_id": body.session_id,
        "reason": body.reason,
        "correlation_id": body.correlation_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _complaints.append(entry)
    logger.warning("Complaint recorded: session=%s reason=%s", body.session_id, body.reason)
    return create_success_response(entry, _correlation_id(request))


@router.get("/metrics")
async def gate_c_metrics(
    request: Request,
    minutes: int = Query(60, ge=1, le=10080),
    device_id: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    # Total emotion events
    q = select(func.count()).select_from(EmotionEvent).where(EmotionEvent.created_at >= since)
    if device_id:
        q = q.where(EmotionEvent.device_id == device_id)
    total_events = (await session.execute(q)).scalar() or 0

    # Unique sessions
    sq = select(func.count(func.distinct(EmotionEvent.session_id))).where(
        EmotionEvent.created_at >= since,
        EmotionEvent.session_id.isnot(None),
    )
    if device_id:
        sq = sq.where(EmotionEvent.device_id == device_id)
    unique_sessions = (await session.execute(sq)).scalar() or 0

    # Average inference latency
    avg_q = select(func.avg(EmotionEvent.inference_ms)).where(EmotionEvent.created_at >= since)
    if device_id:
        avg_q = avg_q.where(EmotionEvent.device_id == device_id)
    avg_inference = (await session.execute(avg_q)).scalar()
    avg_inference_ms = round(float(avg_inference), 2) if avg_inference else None

    # Rough E2E latency estimate: inference + network overhead (~30 ms)
    latency_e2e = round(avg_inference_ms + 30.0, 2) if avg_inference_ms else None

    # Abstention count
    abs_q = (
        select(func.count())
        .select_from(EmotionEvent)
        .where(
            EmotionEvent.created_at >= since,
            EmotionEvent.confidence < ABSTENTION_CONFIDENCE_THRESHOLD,
        )
    )
    if device_id:
        abs_q = abs_q.where(EmotionEvent.device_id == device_id)
    abstention_count = (await session.execute(abs_q)).scalar() or 0
    abstention_rate = round(abstention_count / total_events, 4) if total_events else None

    # Complaints in window
    since_str = since.isoformat()
    complaint_count = sum(
        1 for c in _complaints if c["created_at"] >= since_str
    )
    complaint_rate = (
        round(complaint_count / unique_sessions, 4) if unique_sessions else None
    )

    data = GateCMetrics(
        window_minutes=minutes,
        total_events=total_events,
        unique_sessions=unique_sessions,
        avg_inference_ms=avg_inference_ms,
        latency_e2e_est_ms=latency_e2e,
        abstention_count=abstention_count,
        abstention_rate=abstention_rate,
        complaint_count=complaint_count,
        complaint_rate=complaint_rate,
    )
    return create_success_response(data, _correlation_id(request))


@router.get("/validate")
async def gate_c_validate(
    request: Request,
    minutes: int = Query(60, ge=1, le=10080),
    device_id: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
):
    # Reuse the metrics computation
    resp = await gate_c_metrics(request, minutes, device_id, session)
    m: GateCMetrics = resp.data

    checks = {}

    # Latency check
    if m.latency_e2e_est_ms is not None:
        checks["latency_e2e"] = {
            "passed": m.latency_e2e_est_ms <= LATENCY_E2E_MAX_MS,
            "value": m.latency_e2e_est_ms,
            "threshold": LATENCY_E2E_MAX_MS,
        }
    else:
        checks["latency_e2e"] = {"passed": False, "value": None, "reason": "no data"}

    # Abstention rate check
    if m.abstention_rate is not None:
        checks["abstention_rate"] = {
            "passed": m.abstention_rate <= ABSTENTION_RATE_MAX,
            "value": m.abstention_rate,
            "threshold": ABSTENTION_RATE_MAX,
        }
    else:
        checks["abstention_rate"] = {"passed": False, "value": None, "reason": "no data"}

    # Complaint rate check
    if m.complaint_rate is not None:
        checks["complaint_rate"] = {
            "passed": m.complaint_rate < COMPLAINT_RATE_MAX,
            "value": m.complaint_rate,
            "threshold": COMPLAINT_RATE_MAX,
        }
    else:
        # No sessions → can't compute; pass vacuously if no complaints
        checks["complaint_rate"] = {
            "passed": m.complaint_count == 0,
            "value": None,
            "reason": "no sessions" if m.unique_sessions == 0 else "no data",
        }

    passed = all(c.get("passed", False) for c in checks.values())

    data = GateCValidation(passed=passed, metrics=m, checks=checks)
    return create_success_response(data, _correlation_id(request))
