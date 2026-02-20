"""
Reachy Mini Configuration

Connection settings and hardware configuration for Reachy Mini robot.
"""

from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class ReachyConfig:
    """Configuration for Reachy Mini robot connection."""
    
    host: str = field(default_factory=lambda: os.getenv("REACHY_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("REACHY_PORT", "50051")))
    
    connection_timeout: float = 10.0
    command_timeout: float = 5.0
    
    enable_left_arm: bool = True
    enable_right_arm: bool = True
    enable_head: bool = True
    
    gesture_speed: float = 1.0
    
    simulation_mode: bool = field(
        default_factory=lambda: os.getenv("REACHY_SIMULATION", "false").lower() == "true"
    )
    
    @property
    def grpc_address(self) -> str:
        """Get gRPC address for Reachy SDK."""
        return f"{self.host}:{self.port}"
    
    @classmethod
    def from_env(cls) -> "ReachyConfig":
        """Create config from environment variables."""
        return cls(
            host=os.getenv("REACHY_HOST", "localhost"),
            port=int(os.getenv("REACHY_PORT", "50051")),
            simulation_mode=os.getenv("REACHY_SIMULATION", "false").lower() == "true",
            gesture_speed=float(os.getenv("REACHY_GESTURE_SPEED", "1.0")),
        )
