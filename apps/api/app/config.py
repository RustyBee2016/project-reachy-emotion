"""Centralized configuration for the Media Mover API.

This module provides a single source of truth for all application configuration,
including service settings, storage paths, database connections, and external services.
All configuration can be overridden via environment variables.
"""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List
from urllib.parse import urlparse


class ConfigurationError(Exception):
    """Raised when configuration is invalid or incomplete."""
    pass


def _env_list(key: str, default: List[str]) -> List[str]:
    """Read a comma-separated environment variable into a list."""
    raw = os.getenv(key)
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env_bool(key: str, default: bool) -> bool:
    """Read a boolean environment variable."""
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_int(key: str, default: int) -> int:
    """Read an integer environment variable."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        raise ConfigurationError(f"Invalid integer value for {key}: {value}")


def _is_port_available(port: int, host: str = "0.0.0.0") -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            return True
    except OSError:
        return False


@dataclass(frozen=True)
class AppConfig:
    """Application configuration with validation.
    
    All settings can be overridden via environment variables with the
    REACHY_ prefix (e.g., REACHY_API_PORT=8083).
    """
    
    # =========================================================================
    # Service Configuration
    # =========================================================================
    
    api_host: str = field(
        default_factory=lambda: os.getenv("REACHY_API_HOST", "0.0.0.0")
    )
    
    api_port: int = field(
        default_factory=lambda: _env_int("REACHY_API_PORT", 8083)
    )
    
    api_version: str = field(
        default_factory=lambda: os.getenv("REACHY_API_VERSION", "v1")
    )
    
    api_root_path: str = field(
        default_factory=lambda: os.getenv("REACHY_API_ROOT_PATH", "")
    )
    
    # =========================================================================
    # Storage Configuration
    # =========================================================================
    
    videos_root: Path = field(
        default_factory=lambda: Path(
            os.getenv(
                "REACHY_VIDEOS_ROOT",
                "/media/rusty_admin/project_data/reachy_emotion/videos"
            )
        )
    )
    
    temp_dir: str = field(
        default_factory=lambda: os.getenv("REACHY_TEMP_DIR", "temp")
    )
    
    dataset_dir: str = field(
        default_factory=lambda: os.getenv("REACHY_DATASET_DIR", "dataset_all")
    )
    
    train_dir: str = field(
        default_factory=lambda: os.getenv("REACHY_TRAIN_DIR", "train")
    )
    
    test_dir: str = field(
        default_factory=lambda: os.getenv("REACHY_TEST_DIR", "test")
    )
    
    thumbs_dir: str = field(
        default_factory=lambda: os.getenv("REACHY_THUMBS_DIR", "thumbs")
    )
    
    manifests_dir: str = field(
        default_factory=lambda: os.getenv("REACHY_MANIFESTS_DIR", "manifests")
    )
    
    # =========================================================================
    # Database Configuration
    # =========================================================================
    
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "REACHY_DATABASE_URL",
            "postgresql+asyncpg://reachy_app:reachy_app@localhost:5432/reachy_local"
        )
    )
    
    # =========================================================================
    # External Services
    # =========================================================================
    
    nginx_host: str = field(
        default_factory=lambda: os.getenv("REACHY_NGINX_HOST", "10.0.4.130")
    )
    
    nginx_port: int = field(
        default_factory=lambda: _env_int("REACHY_NGINX_PORT", 8082)
    )
    
    n8n_host: str = field(
        default_factory=lambda: os.getenv("REACHY_N8N_HOST", "10.0.4.130")
    )
    
    n8n_port: int = field(
        default_factory=lambda: _env_int("REACHY_N8N_PORT", 5678)
    )
    
    gateway_host: str = field(
        default_factory=lambda: os.getenv("REACHY_GATEWAY_HOST", "10.0.4.140")
    )
    
    gateway_port: int = field(
        default_factory=lambda: _env_int("REACHY_GATEWAY_PORT", 8000)
    )

    lm_studio_host: str = field(
        default_factory=lambda: os.getenv("REACHY_LM_STUDIO_HOST", "10.0.4.130")
    )

    lm_studio_port: int = field(
        default_factory=lambda: _env_int("REACHY_LM_STUDIO_PORT", 1234)
    )    
    
    # =========================================================================
    # Feature Flags
    # =========================================================================
    
    enable_cors: bool = field(
        default_factory=lambda: _env_bool("REACHY_ENABLE_CORS", True)
    )
    
    enable_legacy_endpoints: bool = field(
        default_factory=lambda: _env_bool("REACHY_ENABLE_LEGACY_ENDPOINTS", True)
    )
    
    # =========================================================================
    # CORS Configuration
    # =========================================================================
    
    ui_origins: List[str] = field(
        default_factory=lambda: _env_list(
            "REACHY_UI_ORIGINS",
            ["http://10.0.4.140:8501", "http://10.0.4.130:8501", "http://localhost:8501"]
        )
    )
    
    # =========================================================================
    # Computed Properties
    # =========================================================================
    
    @property
    def api_base_url(self) -> str:
        """Full API base URL."""
        return f"http://{self.api_host}:{self.api_port}"
    
    @property
    def nginx_base_url(self) -> str:
        """Nginx base URL for static files."""
        return f"http://{self.nginx_host}:{self.nginx_port}"
    
    @property
    def gateway_base_url(self) -> str:
        """Gateway base URL."""
        return f"http://{self.gateway_host}:{self.gateway_port}"
    
    @property
    def n8n_webhook_url(self) -> str:
        """n8n webhook base URL."""
        return f"http://{self.n8n_host}:{self.n8n_port}"
    
    @property
    def temp_path(self) -> Path:
        """Full path to temp directory."""
        return self.videos_root / self.temp_dir
    
    @property
    def dataset_path(self) -> Path:
        """Full path to dataset_all directory."""
        return self.videos_root / self.dataset_dir
    
    @property
    def train_path(self) -> Path:
        """Full path to train directory."""
        return self.videos_root / self.train_dir
    
    @property
    def test_path(self) -> Path:
        """Full path to test directory."""
        return self.videos_root / self.test_dir
    
    @property
    def thumbs_path(self) -> Path:
        """Full path to thumbs directory."""
        return self.videos_root / self.thumbs_dir
    
    @property
    def manifests_path(self) -> Path:
        """Full path to manifests directory."""
        return self.videos_root / self.manifests_dir
    
    # =========================================================================
    # Validation Methods
    # =========================================================================
    
    def validate(self, check_port: bool = True) -> None:
        """Validate configuration and raise ConfigurationError if invalid.
        
        Args:
            check_port: If True, check if API port is available
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        errors = []
        
        # Validate videos_root exists
        if not self.videos_root.exists():
            errors.append(
                f"VIDEOS_ROOT does not exist: {self.videos_root}\n"
                f"  Set REACHY_VIDEOS_ROOT environment variable or create the directory"
            )
        elif not self.videos_root.is_dir():
            errors.append(f"VIDEOS_ROOT is not a directory: {self.videos_root}")
        
        # Check if videos_root is writable
        if self.videos_root.exists() and not os.access(self.videos_root, os.W_OK):
            errors.append(f"VIDEOS_ROOT is not writable: {self.videos_root}")
        
        # Validate required subdirectories exist or can be created
        required_dirs = [
            self.temp_path,
            self.dataset_path,
            self.train_path,
            self.test_path,
            self.thumbs_path,
            self.manifests_path,
        ]
        
        for dir_path in required_dirs:
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    errors.append(f"Cannot create directory {dir_path}: {e}")
        
        # Validate API port
        if self.api_port < 1 or self.api_port > 65535:
            errors.append(f"Invalid API port: {self.api_port} (must be 1-65535)")
        
        # Check if port is available (optional, as it may be in use by current instance)
        if check_port and not _is_port_available(self.api_port, self.api_host):
            errors.append(
                f"Port {self.api_port} is already in use on {self.api_host}\n"
                f"  Set REACHY_API_PORT to a different port or stop the conflicting service"
            )
        
        # Validate database URL format
        try:
            parsed = urlparse(self.database_url)
            if not parsed.scheme or not parsed.netloc:
                errors.append(f"Invalid database URL format: {self.database_url}")
        except Exception as e:
            errors.append(f"Invalid database URL: {e}")
        
        # Validate external service ports
        for name, port in [
            ("NGINX", self.nginx_port),
            ("N8N", self.n8n_port),
            ("GATEWAY", self.gateway_port),
        ]:
            if port < 1 or port > 65535:
                errors.append(f"Invalid {name} port: {port} (must be 1-65535)")
        
        if errors:
            raise ConfigurationError(
                "Configuration validation failed:\n\n" + "\n\n".join(f"  • {e}" for e in errors)
            )
    
    def log_configuration(self, mask_secrets: bool = True) -> dict:
        """Return configuration as a dictionary for logging.
        
        Args:
            mask_secrets: If True, mask sensitive values like database passwords
            
        Returns:
            Dictionary of configuration values
        """
        config_dict = {
            "service": {
                "api_host": self.api_host,
                "api_port": self.api_port,
                "api_version": self.api_version,
                "api_root_path": self.api_root_path,
                "api_base_url": self.api_base_url,
            },
            "storage": {
                "videos_root": str(self.videos_root),
                "temp_path": str(self.temp_path),
                "dataset_path": str(self.dataset_path),
                "train_path": str(self.train_path),
                "test_path": str(self.test_path),
                "thumbs_path": str(self.thumbs_path),
                "manifests_path": str(self.manifests_path),
            },
            "database": {
                "database_url": self._mask_database_url() if mask_secrets else self.database_url,
            },
            "external_services": {
                "nginx": self.nginx_base_url,
                "n8n": self.n8n_webhook_url,
                "gateway": self.gateway_base_url,
            },
            "features": {
                "enable_cors": self.enable_cors,
                "enable_legacy_endpoints": self.enable_legacy_endpoints,
                "ui_origins": self.ui_origins,
            },
        }
        
        return config_dict
    
    def _mask_database_url(self) -> str:
        """Mask password in database URL for logging."""
        try:
            parsed = urlparse(self.database_url)
            if parsed.password:
                masked = self.database_url.replace(parsed.password, "***")
                return masked
            return self.database_url
        except Exception:
            return "***"


@lru_cache
def get_config() -> AppConfig:
    """Return a cached AppConfig instance.
    
    This function is cached to ensure the same configuration is used
    throughout the application lifecycle.
    """
    return AppConfig()


def load_and_validate_config(check_port: bool = True) -> AppConfig:
    """Load configuration and validate it.
    
    Args:
        check_port: If True, check if API port is available
        
    Returns:
        Validated AppConfig instance
        
    Raises:
        ConfigurationError: If configuration is invalid
    """
    config = get_config()
    config.validate(check_port=check_port)
    return config
