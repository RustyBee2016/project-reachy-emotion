"""
LLM Configuration

Configuration for OpenAI GPT-5.2 API integration.
"""

from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class LLMConfig:
    """Configuration for LLM API client."""
    
    api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )
    
    model: str = field(
        default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-5.2")
    )
    
    base_url: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENAI_BASE_URL")
    )
    
    max_tokens: int = 500
    temperature: float = 0.7
    
    timeout: float = 30.0
    max_retries: int = 3
    
    enable_gesture_keywords: bool = True
    
    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create config from environment variables."""
        return cls(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-5.2"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "500")),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
        )
    
    def validate(self) -> bool:
        """Validate configuration."""
        if not self.api_key:
            return False
        return True
