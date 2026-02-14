"""Gateway configuration for Ubuntu 2."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class GatewayConfig:
    """Configuration for the Reachy Gateway service on Ubuntu 2."""
    
    # Upstream service URLs (Ubuntu 1)
    media_mover_url: str = field(
        default_factory=lambda: os.getenv(
            "GATEWAY_MEDIA_MOVER_URL",
            "http://10.0.4.130:8083"
        )
    )
    
    nginx_media_url: str = field(
        default_factory=lambda: os.getenv(
            "GATEWAY_NGINX_MEDIA_URL",
            "http://10.0.4.130:8082"
        )
    )
    
    # Database connection (Ubuntu 1)
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "GATEWAY_DATABASE_URL",
            "postgresql+asyncpg://reachy_app:reachy_app@10.0.4.130:5432/reachy_local"
        )
    )
    
    # Gateway API settings
    api_host: str = field(
        default_factory=lambda: os.getenv("GATEWAY_API_HOST", "0.0.0.0")
    )
    
    api_port: int = field(
        default_factory=lambda: int(os.getenv("GATEWAY_API_PORT", "8000"))
    )
    
    api_root_path: str = field(
        default_factory=lambda: os.getenv("GATEWAY_API_ROOT_PATH", "")
    )
    
    # CORS settings
    enable_cors: bool = field(
        default_factory=lambda: os.getenv("GATEWAY_ENABLE_CORS", "true").lower() == "true"
    )
    
    ui_origins: list[str] = field(
        default_factory=lambda: os.getenv(
            "GATEWAY_UI_ORIGINS",
            "http://localhost:8501,http://10.0.4.140:8501"
        ).split(",")
    )
    
    # Logging
    log_level: str = field(
        default_factory=lambda: os.getenv("GATEWAY_LOG_LEVEL", "INFO")
    )
    
    def validate(self) -> None:
        """Validate configuration values."""
        if not self.media_mover_url.startswith("http"):
            raise ValueError(f"Invalid GATEWAY_MEDIA_MOVER_URL: {self.media_mover_url}")
        
        if not self.nginx_media_url.startswith("http"):
            raise ValueError(f"Invalid GATEWAY_NGINX_MEDIA_URL: {self.nginx_media_url}")
        
        if self.api_port < 1 or self.api_port > 65535:
            raise ValueError(f"Invalid GATEWAY_API_PORT: {self.api_port}")
    
    def log_configuration(self, mask_secrets: bool = True) -> dict:
        """Return configuration as a loggable dictionary."""
        config_dict = {
            "media_mover_url": self.media_mover_url,
            "nginx_media_url": self.nginx_media_url,
            "database_url": self._mask_db_password(self.database_url) if mask_secrets else self.database_url,
            "api_host": self.api_host,
            "api_port": self.api_port,
            "api_root_path": self.api_root_path,
            "enable_cors": self.enable_cors,
            "ui_origins": self.ui_origins,
            "log_level": self.log_level,
        }
        return config_dict
    
    @staticmethod
    def _mask_db_password(url: str) -> str:
        """Mask password in database URL for logging."""
        if "@" in url and "://" in url:
            parts = url.split("://", 1)
            if len(parts) == 2:
                scheme, rest = parts
                if "@" in rest:
                    creds, host = rest.split("@", 1)
                    if ":" in creds:
                        user, _ = creds.split(":", 1)
                        return f"{scheme}://{user}:****@{host}"
        return url


def load_config() -> GatewayConfig:
    """Load and validate gateway configuration."""
    config = GatewayConfig()
    config.validate()
    return config
