"""
Observability router — Phase 2 EQ tracking and LLM health.

Endpoints:
  GET  /api/v1/obs/samples               — list recent obs_samples rows
  POST /api/v1/obs/samples               — batch-insert confidence/expressiveness samples
  GET  /api/v1/obs/calibration_summary   — aggregate EQ calibration stats
  GET  /api/v1/llm/health                — probe LLM endpoint health
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.deps import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["observability"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ObsSampleIn(BaseModel):
    emotion: str
    confidence: float = Field(ge=0.0, le=1.0)
    expressiveness_level: str = "unknown"
    abstained: bool = False
    src: str = "pipeline"


class ObsSamplesBatchIn(BaseModel):
    samples: List[ObsSampleIn]


class ObsSampleOut(BaseModel):
    id: int
    ts: datetime
    emotion: str
    confidence: float
    expressiveness_level: str
    abstained: bool
    src: str


class CalibrationSummaryOut(BaseModel):
    sample_count: int
    mean_confidence: Optional[float]
    abstention_rate: Optional[float]
    expressiveness_distribution: Dict[str, int]
    emotion_distribution: Dict[str, int]
    gate_a_ece: Optional[float]
    gate_a_brier: Optional[float]
    gate_a_mce: Optional[float]
    gate_a_passed: Optional[bool]
    latest_run_id: Optional[str]


class LLMHealthOut(BaseModel):
    status: str
    model: str
    base_url: str
    latency_ms: float
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

OBS_SELECT = sa.text(
    "SELECT id, ts, src, metric, value, labels "
    "FROM obs_samples WHERE metric = 'confidence' "
    "ORDER BY ts DESC LIMIT :limit"
)

OBS_SELECT_EMOTION = sa.text(
    "SELECT id, ts, src, metric, value, labels "
    "FROM obs_samples WHERE metric = 'confidence' "
    "AND labels->>'emotion' = :emotion "
    "ORDER BY ts DESC LIMIT :limit"
)

OBS_INSERT = sa.text(
    "INSERT INTO obs_samples (ts, src, metric, value, labels) "
    "VALUES (:ts, :src, 'confidence', :value, CAST(:labels AS jsonb))"
)

OBS_AGGREGATE = sa.text(
    "SELECT COUNT(*) as cnt, "
    "AVG(value) as mean_conf, "
    "SUM(CASE WHEN labels->>'abstained' = 'true' THEN 1 ELSE 0 END) as abstained_cnt "
    "FROM obs_samples WHERE metric = 'confidence'"
)


def _load_mlflow_calibration() -> Dict[str, Any]:
    """Query MLflow for the latest run's calibration metrics."""
    result: Dict[str, Any] = {}
    mlflow_uri = os.getenv(
        "MLFLOW_TRACKING_URI",
        "file:///media/rusty_admin/project_data/reachy_emotion/mlruns",
    )
    try:
        import mlflow
        from mlflow.tracking import MlflowClient
        mlflow.set_tracking_uri(mlflow_uri)
        client = MlflowClient()
        experiments = client.search_experiments()
        latest_run = None
        for exp in experiments:
            runs = client.search_runs(
                experiment_ids=[exp.experiment_id],
                order_by=["start_time DESC"],
                max_results=1,
            )
            if runs:
                latest_run = runs[0]
                break
        if latest_run:
            m = latest_run.data.metrics
            result["gate_a_ece"] = m.get("ece")
            result["gate_a_brier"] = m.get("brier")
            result["gate_a_mce"] = m.get("mce")
            result["latest_run_id"] = latest_run.info.run_id[:8]
            ece = m.get("ece", 1.0)
            brier = m.get("brier", 1.0)
            f1 = m.get("f1_macro", 0.0)
            bal_acc = m.get("balanced_accuracy", 0.0)
            result["gate_a_passed"] = (
                ece <= 0.08 and brier <= 0.16
                and f1 >= 0.84 and bal_acc >= 0.85
            )
    except Exception as exc:
        logger.warning(f"MLflow calibration load failed: {exc}")
    return result


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/api/v1/obs/samples", response_model=Dict[str, Any])
async def list_obs_samples(
    limit: int = Query(default=500, ge=1, le=5000),
    emotion: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return recent confidence/expressiveness samples from obs_samples."""
    try:
        if emotion:
            result = await session.execute(OBS_SELECT_EMOTION, {"limit": limit, "emotion": emotion})
        else:
            result = await session.execute(OBS_SELECT, {"limit": limit})
        rows = result.mappings().all()
        samples = []
        for row in rows:
            labels = row["labels"] or {}
            samples.append(
                {
                    "id": row["id"],
                    "ts": row["ts"].isoformat() if row["ts"] else None,
                    "emotion": labels.get("emotion", "unknown"),
                    "confidence": float(row["value"] or 0),
                    "expressiveness_level": labels.get("expressiveness_level", "unknown"),
                    "abstained": labels.get("abstained", False),
                    "src": row["src"],
                }
            )
        return {"samples": samples, "count": len(samples)}
    except Exception as exc:
        logger.error(f"obs/samples GET failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/api/v1/obs/samples", response_model=Dict[str, Any])
async def insert_obs_samples(
    body: ObsSamplesBatchIn,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Batch-insert confidence/expressiveness samples from the pipeline."""
    if not body.samples:
        return {"inserted": 0}
    try:
        import json
        now = datetime.now(timezone.utc)
        for s in body.samples:
            labels_json = json.dumps({
                "emotion": s.emotion,
                "expressiveness_level": s.expressiveness_level,
                "abstained": s.abstained,
            })
            await session.execute(
                OBS_INSERT,
                {"ts": now, "src": s.src, "value": round(s.confidence, 4), "labels": labels_json},
            )
        await session.commit()
        return {"inserted": len(body.samples)}
    except Exception as exc:
        await session.rollback()
        logger.error(f"obs/samples POST failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/v1/obs/calibration_summary", response_model=Dict[str, Any])
async def calibration_summary(
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Aggregate calibration summary from obs_samples + latest MLflow run."""
    summary: Dict[str, Any] = {
        "sample_count": 0,
        "mean_confidence": None,
        "abstention_rate": None,
        "expressiveness_distribution": {},
        "emotion_distribution": {},
        "gate_a_ece": None,
        "gate_a_brier": None,
        "gate_a_mce": None,
        "gate_a_passed": None,
        "latest_run_id": None,
    }
    try:
        result = await session.execute(OBS_SELECT, {"limit": 5000})
        rows = result.mappings().all()
        if rows:
            values = [float(r["value"] or 0) for r in rows]
            labels_list = [r["labels"] or {} for r in rows]
            summary["sample_count"] = len(values)
            summary["mean_confidence"] = round(sum(values) / len(values), 4)
            abstained = sum(1 for lb in labels_list if lb.get("abstained"))
            summary["abstention_rate"] = round(abstained / len(values), 4)
            exp_dist: Dict[str, int] = {}
            emo_dist: Dict[str, int] = {}
            for lb in labels_list:
                tier = lb.get("expressiveness_level", "unknown")
                exp_dist[tier] = exp_dist.get(tier, 0) + 1
                emo = lb.get("emotion", "unknown")
                emo_dist[emo] = emo_dist.get(emo, 0) + 1
            summary["expressiveness_distribution"] = exp_dist
            summary["emotion_distribution"] = emo_dist
    except Exception as exc:
        logger.warning(f"obs_samples aggregate failed: {exc}")
    summary.update(_load_mlflow_calibration())
    return summary


@router.get("/api/v1/llm/health", response_model=Dict[str, Any])
async def llm_health() -> Dict[str, Any]:
    """Probe the configured LLM endpoint with a minimal request."""
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-5.2")
    api_key = os.getenv("OPENAI_API_KEY", "")

    start = time.monotonic()
    try:
        import httpx
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            )
        latency_ms = (time.monotonic() - start) * 1000
        if resp.status_code == 200:
            data = resp.json()
            actual_model = data.get("model", model)
            return {
                "status": "ok",
                "model": actual_model,
                "base_url": base_url,
                "latency_ms": round(latency_ms, 1),
                "error": None,
            }
        else:
            return {
                "status": "error",
                "model": model,
                "base_url": base_url,
                "latency_ms": round(latency_ms, 1),
                "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
            }
    except Exception as exc:
        latency_ms = (time.monotonic() - start) * 1000
        return {
            "status": "unreachable",
            "model": model,
            "base_url": base_url,
            "latency_ms": round(latency_ms, 1),
            "error": str(exc),
        }
