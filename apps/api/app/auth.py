"""API key authentication for the Reachy Media Mover API.

Enforces Bearer token validation on mutating endpoints.  Health,
readiness, metrics, and WebSocket routes are exempt so monitoring
and the Streamlit UI can still reach them without extra config.
"""

from __future__ import annotations

import hmac
import logging
import os
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# Lazy-loaded from environment on first use.
_bearer_scheme = HTTPBearer(auto_error=False)

# Paths that never require authentication.
_PUBLIC_PREFIXES = (
    "/api/v1/health",
    "/api/v1/ready",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
)


def _get_valid_tokens() -> set[str]:
    """Collect all non-empty API tokens from environment variables."""
    tokens: set[str] = set()
    for key in ("GATEWAY_TOKEN", "MEDIA_MOVER_TOKEN", "REACHY_API_TOKEN"):
        value = os.getenv(key, "").strip()
        if value:
            tokens.add(value)
    return tokens


def _is_public_path(path: str) -> bool:
    """Return True if the request path is exempt from auth."""
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIXES)


async def require_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> Optional[str]:
    """FastAPI dependency that validates the Bearer token.

    Skips validation for public paths and WebSocket upgrades.
    When no tokens are configured in the environment, auth is
    disabled (development mode) with a startup warning.

    Returns the matched token (or None for public/dev-mode paths).
    """
    # WebSocket upgrades are authenticated by the WS handler itself.
    if request.scope.get("type") == "websocket":
        return None

    if _is_public_path(request.url.path):
        return None

    valid_tokens = _get_valid_tokens()

    # If no tokens are configured, run in open/dev mode.
    if not valid_tokens:
        return None

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Use: Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Constant-time comparison to prevent timing attacks.
    token = credentials.credentials
    for valid in valid_tokens:
        if hmac.compare_digest(token, valid):
            return token

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
