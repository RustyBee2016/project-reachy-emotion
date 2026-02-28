from __future__ import annotations

import logging
import os
import time
import ipaddress
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar
from urllib.parse import urlparse

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

# Set up logging
logger = logging.getLogger(__name__)

# Type variable for generic function
F = TypeVar('F', bound=Callable[..., Any])

# Default URLs - can be overridden via environment variables
DEFAULT_MEDIA_BASE = "http://localhost:8083"
DEFAULT_GATEWAY_BASE = "http://localhost:8000"

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF = 1.0  # seconds


def retry_on_failure(max_retries: int = MAX_RETRIES, backoff: float = RETRY_BACKOFF) -> Callable[[F], F]:
    """Decorator to retry API calls on transient failures.
    
    Retries on connection errors, timeouts, and 5xx server errors.
    Uses exponential backoff between retries.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff: Initial backoff time in seconds (doubles each retry)
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, Timeout) as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = backoff * (2 ** attempt)
                        logger.warning(
                            f"API call failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {wait_time:.1f}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"API call failed after {max_retries + 1} attempts: {e}")
                except HTTPError as e:
                    # Retry on 5xx server errors, but not 4xx client errors
                    if e.response is not None and 500 <= e.response.status_code < 600:
                        last_exception = e
                        if attempt < max_retries:
                            wait_time = backoff * (2 ** attempt)
                            logger.warning(
                                f"Server error {e.response.status_code} (attempt {attempt + 1}/{max_retries + 1}). "
                                f"Retrying in {wait_time:.1f}s..."
                            )
                            time.sleep(wait_time)
                        else:
                            logger.error(f"Server error after {max_retries + 1} attempts: {e}")
                    else:
                        # Don't retry 4xx errors
                        raise
                except Exception as e:
                    # Don't retry unexpected errors
                    logger.error(f"Unexpected error in API call: {e}")
                    raise
            
            # If we get here, all retries failed
            if last_exception:
                raise last_exception
            raise RuntimeError("All retry attempts failed")
        
        return wrapper  # type: ignore
    return decorator


def _base_url() -> str:
    """Get the Media Mover API base URL from environment or use default."""
    return os.getenv("REACHY_API_BASE", DEFAULT_MEDIA_BASE).rstrip("/")


def _gateway_base() -> str:
    """Get the Gateway API base URL from environment or use default."""
    env = os.getenv("REACHY_GATEWAY_BASE")
    if env:
        return env.rstrip("/")
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


def _env_bool(name: str) -> Optional[bool]:
    raw = os.getenv(name)
    if raw is None:
        return None
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return None


def _is_private_or_local_host(hostname: Optional[str]) -> bool:
    if not hostname:
        return False
    lowered = hostname.lower()
    if lowered in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(lowered).is_private
    except ValueError:
        return lowered.endswith(".local")


def _allow_self_signed(service_name: str) -> bool:
    """Return True if self-signed certs are allowed for the given service."""
    service_env = _env_bool(f"REACHY_{service_name}_ALLOW_SELF_SIGNED")
    if service_env is not None:
        return service_env
    global_pref = _env_bool("REACHY_ALLOW_SELF_SIGNED")
    return bool(global_pref)


def _request_verify(base_url: str, service: str) -> bool | str:
    """Determine the requests.verify value for a given service call."""
    service_name = service.upper()
    ca_bundle = os.getenv(f"REACHY_{service_name}_CA_BUNDLE") or os.getenv("REACHY_CA_BUNDLE")
    if ca_bundle:
        return ca_bundle

    parsed = urlparse(base_url)
    hostname = parsed.hostname
    if parsed.scheme == "https" and _is_private_or_local_host(hostname):
        if _allow_self_signed(service_name):
            logger.warning(
                "TLS verification disabled for %s (%s). "
                "Use CA bundle env vars in production.",
                service_name,
                hostname,
            )
            return False

    return True


def media_api_base() -> str:
    """Return the configured Media Mover API base URL."""
    return _base_url()


def gateway_api_base() -> str:
    """Return the configured Gateway base URL."""
    return _gateway_base()


@retry_on_failure()
def list_videos(split: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
    """List videos from the specified split.
    
    Uses the v1 API endpoint which returns standardized response format.
    
    Args:
        split: Video split (temp, train, test, purged)
        limit: Maximum number of videos to return
        offset: Pagination offset
        
    Returns:
        Dictionary with 'items', 'pagination' keys (unwrapped from v1 response)
    """
    url = f"{_base_url()}/api/v1/media/list"
    requested_limit = max(1, int(limit))
    current_offset = max(0, int(offset))
    page_limit = 10  # Backend-enforced request cap
    items: list[dict] = []
    total: Optional[int] = None
    has_more = False

    while len(items) < requested_limit:
        batch_limit = min(page_limit, requested_limit - len(items))
        resp = requests.get(
            url,
            headers=_headers(),
            params={"split": split, "limit": batch_limit, "offset": current_offset},
            timeout=10,
            verify=_request_verify(_base_url(), "API"),
        )
        resp.raise_for_status()

        body = resp.json()
        if body.get("status") != "success" or "data" not in body:
            # Fallback for unexpected format
            return body

        data = body["data"]
        batch_items = data.get("items", [])
        pagination = data.get("pagination", {})
        if not isinstance(batch_items, list):
            batch_items = []
        items.extend(batch_items)
        total = pagination.get("total") if isinstance(pagination.get("total"), int) else total
        has_more = bool(pagination.get("has_more"))

        # Advance by number returned to avoid skipping when source size changes.
        current_offset += len(batch_items)
        if not batch_items or not has_more:
            break

    resolved_total = total if isinstance(total, int) else len(items)
    return {
        "items": items,
        "total": resolved_total,
        "limit": requested_limit,
        "offset": max(0, int(offset)),
        "has_more": bool((max(0, int(offset)) + len(items)) < resolved_total),
    }


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
    """Promote a video to a different split (gateway/media compatibility endpoint).
    
    Args:
        video_id: Video ID to promote
        dest_split: Destination split (train, test)
        label: Optional emotion label
        dry_run: If True, validate without executing
        correlation_id: Optional correlation ID for tracking
        use_gateway: If True, use gateway endpoint instead of media mover
        idempotency_key: Optional idempotency key for gateway
        
    Returns:
        Response dictionary
    """
    normalized_split = dest_split.strip().lower()
    if normalized_split not in {"train", "test"}:
        raise ValueError("dest_split must be one of: train, test")

    normalized_label: Optional[str] = None
    if label is not None:
        normalized_label = label.strip().lower()
    if normalized_split == "train":
        if normalized_label not in {"happy", "sad", "neutral"}:
            raise ValueError("train promotions require label in {happy, sad, neutral}")
    else:
        normalized_label = None

    payload: Dict[str, Any] = {"video_id": video_id, "dest_split": normalized_split, "dry_run": dry_run}
    if normalized_label is not None:
        payload["label"] = normalized_label
    if correlation_id:
        payload["correlation_id"] = correlation_id

    headers = _headers()

    if use_gateway:
        gateway_url = f"{_gateway_base()}/api/promote"
        headers = headers.copy()
        # Gateway requires Idempotency-Key; fall back to correlation/video id
        headers["Idempotency-Key"] = idempotency_key or correlation_id or video_id
        resp = requests.post(
            gateway_url,
            headers=headers,
            json=payload,
            timeout=15,
            verify=_request_verify(_gateway_base(), "GATEWAY"),
        )
        resp.raise_for_status()
        return resp.json()

    canonical_url = f"{_base_url()}/api/v1/media/promote"
    legacy_url = f"{_base_url()}/api/media/promote"
    resp = requests.post(
        canonical_url,
        headers=headers,
        json=payload,
        timeout=15,
        verify=_request_verify(_base_url(), "API"),
    )
    if resp.status_code == 404:
        resp = requests.post(
            legacy_url,
            headers=headers,
            json=payload,
            timeout=15,
            verify=_request_verify(_base_url(), "API"),
        )
    resp.raise_for_status()
    return resp.json()


def rebuild_manifest(
    *,
    splits: Optional[list[str]] = None,
    correlation_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    url = f"{_base_url()}/api/v1/ingest/manifest/rebuild"
    payload: Dict[str, Any] = {"splits": splits or ["train", "test"]}
    if correlation_id:
        payload["correlation_id"] = correlation_id

    headers = _headers()
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    resp = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30,
        verify=_request_verify(_base_url(), "API"),
    )
    resp.raise_for_status()
    return resp.json()


def prepare_run_frames(
    *,
    run_id: Optional[str] = None,
    train_fraction: float = 0.7,
    seed: Optional[int] = None,
    dry_run: bool = False,
    face_crop: bool = False,
    face_target_size: int = 224,
    face_confidence: float = 0.6,
    split_run: bool = False,
    split_train_ratio: float = 0.9,
    strip_valid_labels: bool = True,
    persist_valid_metadata: bool = False,
    correlation_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Trigger run-scoped frame extraction (10 random frames per train video)."""
    url = f"{_base_url()}/api/v1/ingest/prepare-run-frames"
    payload: Dict[str, Any] = {
        "train_fraction": train_fraction,
        "dry_run": bool(dry_run),
        "face_crop": bool(face_crop),
        "face_target_size": int(face_target_size),
        "face_confidence": float(face_confidence),
        "split_run": bool(split_run),
        "split_train_ratio": split_train_ratio,
        "strip_valid_labels": bool(strip_valid_labels),
        "persist_valid_metadata": bool(persist_valid_metadata),
    }
    if run_id:
        payload["run_id"] = run_id
    if seed is not None:
        payload["seed"] = seed
    if correlation_id:
        payload["correlation_id"] = correlation_id

    headers = _headers()
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    resp = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=120,
        verify=_request_verify(_base_url(), "API"),
    )
    resp.raise_for_status()
    return resp.json()


def get_training_status(pipeline_id: str) -> Dict[str, Any]:
    """Fetch persisted training status by run id (or 'latest')."""
    url = f"{_gateway_base()}/api/training/status/{pipeline_id}"
    resp = requests.get(
        url,
        headers=_headers(),
        timeout=10,
        verify=_request_verify(_gateway_base(), "GATEWAY"),
    )
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
    files = {"file": (file_name, file_bytes)}
    data: Dict[str, Any] = {
        "for_training": str(bool(upload_for_training)).lower(),
        "correlation_id": correlation_id,
    }
    if metadata:
        for key, value in metadata.items():
            data[f"meta[{key}]"] = value
    resp = requests.post(
        url,
        headers=headers,
        files=files,
        data=data,
        timeout=60,
        verify=_request_verify(_gateway_base(), "GATEWAY"),
    )
    resp.raise_for_status()
    return resp.json()


def register_local_video(
    file_path: str,
    *,
    correlation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    file_name: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Register a locally available video already on disk (temp/)."""
    url = f"{_base_url()}/api/v1/ingest/register-local"
    payload: Dict[str, Any] = {"file_path": file_path}
    if correlation_id:
        payload["correlation_id"] = correlation_id
    if metadata:
        payload["metadata"] = metadata
    if file_name:
        payload["file_name"] = file_name

    headers = _headers()
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    resp = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30,
        verify=_request_verify(_base_url(), "API"),
    )
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
    resp = requests.post(
        url,
        headers=_headers(),
        json=payload,
        timeout=30,
        verify=_request_verify(_gateway_base(), "GATEWAY"),
    )
    resp.raise_for_status()
    return resp.json()


@retry_on_failure()
def launch_ml_run(
    *,
    mode: str = "train",
    run_id: Optional[str] = None,
    config_path: Optional[str] = None,
    checkpoint: Optional[str] = None,
    test_data_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Launch a training, validation, or test run on the backend.

    Args:
        mode: 'train', 'validate', or 'test'
        run_id: Optional run identifier (auto-generated if omitted)
        config_path: Path to training YAML config (relative to project root)
        checkpoint: Checkpoint path (required for validate/test unless default exists)
        test_data_dir: Override test data directory (defaults to AffectNet test dataset for test mode)

    Returns:
        Response dict with run_id, status, pid, and message
    """
    url = f"{_base_url()}/api/v1/training/launch"
    payload: Dict[str, Any] = {"mode": mode}
    if run_id:
        payload["run_id"] = run_id
    if config_path:
        payload["config_path"] = config_path
    if checkpoint:
        payload["checkpoint"] = checkpoint
    if test_data_dir:
        payload["test_data_dir"] = test_data_dir

    resp = requests.post(
        url,
        headers=_headers(),
        json=payload,
        timeout=30,
        verify=_request_verify(_base_url(), "API"),
    )
    resp.raise_for_status()
    return resp.json()


@retry_on_failure()
def get_training_log(run_id: str, mode: str = "train", tail: int = 100) -> str:
    """Read the tail of a training run's log file.

    This is a convenience helper that reads the log file locally if available,
    or returns an empty string if not found.
    """
    import subprocess
    log_name = f"{run_id}_{mode}.log"
    log_path = f"logs/{log_name}"
    try:
        result = subprocess.run(
            ["tail", f"-n{tail}", log_path],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout
    except Exception:
        return ""


def reject_video(video_id: str, correlation_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    url = f"{_gateway_base()}/api/privacy/redact/{video_id}"
    payload: Dict[str, Any] = {"correlation_id": correlation_id}
    if reason:
        payload["reason"] = reason
    resp = requests.post(
        url,
        headers=_headers(),
        json=payload,
        timeout=15,
        verify=_request_verify(_gateway_base(), "GATEWAY"),
    )
    resp.raise_for_status()
    return resp.json()


@retry_on_failure()
def stage_to_train(
    video_ids: list[str],
    label: str,
    dry_run: bool = False,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Batch helper to promote videos from temp -> train/<label>."""
    promoted_ids: list[str] = []
    skipped_ids: list[str] = []
    failed_ids: list[str] = []

    for video_id in video_ids:
        try:
            _ = promote(
                video_id=video_id,
                dest_split="train",
                label=label,
                dry_run=dry_run,
                correlation_id=correlation_id,
                use_gateway=False,
            )
            promoted_ids.append(video_id)
        except Exception:
            failed_ids.append(video_id)

    return {
        "status": "accepted" if not failed_ids else "error",
        "promoted_ids": promoted_ids,
        "skipped_ids": skipped_ids,
        "failed_ids": failed_ids,
        "dry_run": dry_run,
        "message": "batch promotion completed via /api/v1/media/promote",
    }
