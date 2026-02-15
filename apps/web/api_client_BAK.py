import os
<<<<<<< Updated upstream
from typing import Any, Dict, Optional
=======
import time
import uuid
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar
>>>>>>> Stashed changes

import requests

DEFAULT_MEDIA_BASE = "http://localhost:8081/api/media"
DEFAULT_GATEWAY_BASE = "http://localhost:8000"


def _base_url() -> str:
    return os.getenv("REACHY_API_BASE", DEFAULT_MEDIA_BASE).rstrip("/")


def _gateway_base() -> str:
    env = os.getenv("REACHY_GATEWAY_BASE")
    if env:
        return env.rstrip("/")
    base = _base_url()
    if base.endswith("/api/media"):
        return base[: -len("/api/media")]
    return DEFAULT_GATEWAY_BASE.rstrip("/")


def _media_host_base() -> str:
    base = _base_url()
    if base.endswith("/api/media"):
        return base[: -len("/api/media")]
    return base


def _headers() -> Dict[str, str]:
    hdrs: Dict[str, str] = {"Accept": "application/json", "X-API-Version": "v1"}
    token = os.getenv("REACHY_API_TOKEN")
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    return hdrs


def media_api_base() -> str:
    """Return the configured Media Mover API base URL."""
    return _base_url()


def gateway_api_base() -> str:
    """Return the configured Gateway base URL."""
    return _gateway_base()


def list_videos(split: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    url = f"{_base_url()}/videos/list"
    resp = requests.get(url, headers=_headers(), params={"split": split, "limit": limit, "offset": offset}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def promote(
    video_id: str,
    dest_split: str,
    label: Optional[str] = None,
    dry_run: bool = False,
    *,
    correlation_id: Optional[str] = None,
    use_gateway: bool = False,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    # Keep compatibility alias in mind; prefer /api/media/promote
    payload: Dict[str, Any] = {"video_id": video_id, "dest_split": dest_split, "dry_run": dry_run}
    if label is not None:
        payload["label"] = label
    if correlation_id:
        payload["correlation_id"] = correlation_id

    url = f"{_base_url()}/promote"
    headers = _headers()

    if use_gateway:
        url = f"{_gateway_base()}/api/promote"
        headers = headers.copy()
        # Gateway requires Idempotency-Key; fall back to correlation/video id
        headers["Idempotency-Key"] = idempotency_key or correlation_id or video_id

    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def rebuild_manifest() -> Dict[str, Any]:
    url = f"{_base_url()}/manifest/rebuild"
    payload = {"splits": ["train", "test"], "correlation_id": str(uuid.uuid4())}
    headers = _headers()
    headers["Idempotency-Key"] = payload["correlation_id"]
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def thumb_url(video_id: str) -> str:
    # Thumbs are usually served directly by Nginx from /thumbs/{id}.jpg
    # If API base is https://host/api/media, derive host scheme for thumbs.
    base = _media_host_base()
    return f"{base}/thumbs/{video_id}.jpg"


def video_url(file_path: str) -> str:
    root = _media_host_base()
    rel = file_path.lstrip("/")
    return f"{root}/{rel}"


def video_storage_caption(split: str = "temp") -> str:
    base = _media_host_base()
    return f"{base}/videos/{split}"


def upload_video(
    file_name: str,
    file_bytes: bytes,
    upload_for_training: bool,
    correlation_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    url = f"{_gateway_base()}/api/media/ingest"
    headers = _headers()
    headers["Idempotency-Key"] = correlation_id or str(uuid.uuid4())
    files = {"file": (file_name, file_bytes)}
    data: Dict[str, Any] = {
        "for_training": str(bool(upload_for_training)).lower(),
        "correlation_id": correlation_id,
    }
    if metadata:
        import json
        data["metadata_json"] = json.dumps(metadata)
    resp = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    resp.raise_for_status()
    return resp.json()


def request_generation(prompt: str, correlation_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{_gateway_base()}/api/gen/request"
    payload: Dict[str, Any] = {
        "schema_version": "v1",
        "prompt": prompt,
        "correlation_id": correlation_id,
    }
    if params:
        payload.update(params)
    resp = requests.post(url, headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def reject_video(video_id: str, correlation_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    url = f"{_gateway_base()}/api/privacy/redact/{video_id}"
    payload: Dict[str, Any] = {"correlation_id": correlation_id}
    if reason:
        payload["reason"] = reason
    resp = requests.post(url, headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()
<<<<<<< Updated upstream
=======


def stage_videos(video_ids: list[str], label: str, dry_run: bool = True) -> Dict[str, Any]:
    url = f"{_base_url()}/api/v1/promote/stage"
    headers = _headers()
    headers["X-Correlation-ID"] = str(uuid.uuid4())
    payload = {"video_ids": video_ids, "label": label, "dry_run": dry_run}
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def sample_split(
    run_id: str,
    target_split: str,
    sample_fraction: float,
    strategy: str = "balanced_random",
    seed: Optional[int] = None,
    dry_run: bool = True,
) -> Dict[str, Any]:
    url = f"{_base_url()}/api/v1/promote/sample"
    headers = _headers()
    headers["X-Correlation-ID"] = str(uuid.uuid4())
    payload: Dict[str, Any] = {
        "run_id": run_id,
        "target_split": target_split,
        "sample_fraction": sample_fraction,
        "strategy": strategy,
        "dry_run": dry_run,
    }
    if seed is not None:
        payload["seed"] = seed
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_training_status(pipeline_id: str) -> Dict[str, Any]:
    url = f"{_gateway_base()}/api/training/status/{pipeline_id}"
    resp = requests.get(url, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def update_training_status(pipeline_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{_gateway_base()}/api/training/status/{pipeline_id}"
    resp = requests.post(url, headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_deployment_status(pipeline_id: str) -> Dict[str, Any]:
    url = f"{_gateway_base()}/api/deployment/status/{pipeline_id}"
    resp = requests.get(url, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def update_deployment_status(pipeline_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{_gateway_base()}/api/deployment/status/{pipeline_id}"
    resp = requests.post(url, headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


@retry_on_failure()
def stage_to_dataset_all(
    video_ids: list[str],
    label: str,
    dry_run: bool = False,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Stage videos from temp to dataset_all with emotion label metadata.
    
    This uses the database-backed promotion service that persists metadata
    to PostgreSQL and performs atomic filesystem operations.
    
    Args:
        video_ids: List of video IDs to stage
        label: Emotion label (happy, sad, neutral)
        dry_run: If True, validate without executing
        correlation_id: Optional correlation ID for tracking
        
    Returns:
        Response with promoted_ids, skipped_ids, failed_ids
    """
    url = f"{_base_url()}/api/v1/promote/stage"
    payload: Dict[str, Any] = {
        "video_ids": video_ids,
        "label": label,
        "dry_run": dry_run,
    }
    headers = _headers()
    if correlation_id:
        headers["X-Correlation-ID"] = correlation_id
    
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()
>>>>>>> Stashed changes
