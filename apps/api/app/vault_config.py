"""HashiCorp Vault integration for secure credential management.

This module provides functions to retrieve database credentials and API tokens
from HashiCorp Vault instead of storing them in .env files.

Environment Variables Required:
    VAULT_ADDR: Vault server URL (default: http://10.0.4.130:8200)
    VAULT_TOKEN: Authentication token for Vault access
    USE_VAULT: Set to 'true' to enable Vault (default: false for dev)

Example:
    export VAULT_ADDR=http://10.0.4.130:8200
    export VAULT_TOKEN=root
    export USE_VAULT=true
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Lazy import to avoid hard dependency when USE_VAULT=false
_hvac = None


def _get_hvac():
    """Lazy import hvac library."""
    global _hvac
    if _hvac is None:
        try:
            import hvac
            _hvac = hvac
        except ImportError:
            logger.error(
                "hvac library not installed. Install with: pip install hvac"
            )
            raise
    return _hvac


def get_vault_client():
    """Create and return a HashiCorp Vault client.
    
    Returns:
        hvac.Client: Authenticated Vault client
        
    Raises:
        RuntimeError: If VAULT_ADDR or VAULT_TOKEN not set
    """
    hvac = _get_hvac()
    
    vault_addr = os.getenv("VAULT_ADDR")
    vault_token = os.getenv("VAULT_TOKEN")
    
    if not vault_addr:
        raise RuntimeError(
            "VAULT_ADDR environment variable not set. "
            "Example: export VAULT_ADDR=http://10.0.4.130:8200"
        )
    
    if not vault_token:
        raise RuntimeError(
            "VAULT_TOKEN environment variable not set. "
            "Example: export VAULT_TOKEN=<your_token>"
        )
    
    client = hvac.Client(url=vault_addr, token=vault_token)
    
    if not client.is_authenticated():
        raise RuntimeError(
            f"Failed to authenticate with Vault at {vault_addr}. "
            "Check VAULT_TOKEN is valid."
        )
    
    logger.info("Successfully authenticated with Vault at %s", vault_addr)
    return client


def get_db_credentials() -> Dict[str, Any]:
    """Retrieve database credentials from Vault.
    
    Returns:
        Dict with keys: host, port, database, username, password
        
    Example:
        >>> creds = get_db_credentials()
        >>> print(creds['host'])
        10.0.4.130
    """
    client = get_vault_client()
    
    try:
        secret = client.secrets.kv.v2.read_secret_version(path="reachy/db")
        data = secret["data"]["data"]
        
        required_keys = ["host", "port", "database", "username", "password"]
        missing = [k for k in required_keys if k not in data]
        if missing:
            raise ValueError(
                f"Missing required keys in Vault secret: {missing}"
            )
        
        logger.info("Retrieved DB credentials from Vault (path: reachy/db)")
        return data
        
    except Exception as exc:
        logger.error("Failed to retrieve DB credentials from Vault: %s", exc)
        raise


def get_api_tokens() -> Dict[str, str]:
    """Retrieve API authentication tokens from Vault.
    
    Returns:
        Dict with keys: gateway_token, media_mover_token
    """
    client = get_vault_client()
    
    try:
        secret = client.secrets.kv.v2.read_secret_version(path="reachy/tokens")
        data = secret["data"]["data"]
        
        logger.info("Retrieved API tokens from Vault (path: reachy/tokens)")
        return data
        
    except Exception as exc:
        logger.error("Failed to retrieve API tokens from Vault: %s", exc)
        raise


def is_vault_enabled() -> bool:
    """Check if Vault integration is enabled.
    
    Returns:
        True if USE_VAULT=true, False otherwise
    """
    return os.getenv("USE_VAULT", "false").lower() in {"true", "1", "yes"}
