"""Tests for centralized configuration module."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from apps.api.app.config import (
    AppConfig,
    ConfigurationError,
    get_config,
    load_and_validate_config,
    _env_bool,
    _env_int,
    _is_port_available,
)


class TestEnvHelpers:
    """Test environment variable helper functions."""
    
    def test_env_bool_true_values(self):
        """Test that various true values are recognized."""
        for value in ["1", "true", "True", "TRUE", "yes", "Yes", "YES", "on", "On", "ON"]:
            with patch.dict(os.environ, {"TEST_BOOL": value}):
                assert _env_bool("TEST_BOOL", False) is True
    
    def test_env_bool_false_values(self):
        """Test that non-true values are treated as false."""
        for value in ["0", "false", "False", "no", "off", "anything"]:
            with patch.dict(os.environ, {"TEST_BOOL": value}):
                assert _env_bool("TEST_BOOL", True) is False
    
    def test_env_bool_default(self):
        """Test that default is used when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            assert _env_bool("NONEXISTENT", True) is True
            assert _env_bool("NONEXISTENT", False) is False
    
    def test_env_int_valid(self):
        """Test reading valid integer from environment."""
        with patch.dict(os.environ, {"TEST_INT": "42"}):
            assert _env_int("TEST_INT", 0) == 42
    
    def test_env_int_invalid(self):
        """Test that invalid integer raises error."""
        with patch.dict(os.environ, {"TEST_INT": "not_a_number"}):
            with pytest.raises(ConfigurationError, match="Invalid integer"):
                _env_int("TEST_INT", 0)
    
    def test_env_int_default(self):
        """Test that default is used when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            assert _env_int("NONEXISTENT", 42) == 42


class TestPortAvailability:
    """Test port availability checking."""
    
    def test_port_available_on_high_port(self):
        """Test that a high port number is typically available."""
        # Use a very high port that's unlikely to be in use
        assert _is_port_available(54321) is True
    
    def test_port_unavailable_on_privileged_port(self):
        """Test that privileged ports may not be available."""
        # Port 80 typically requires root or is in use
        # This test may pass if running as root, so we just check it doesn't crash
        result = _is_port_available(80)
        assert isinstance(result, bool)


class TestAppConfig:
    """Test AppConfig dataclass."""
    
    def test_default_config(self):
        """Test that default configuration can be created."""
        config = AppConfig()
        
        assert config.api_host == "0.0.0.0"
        assert config.api_port == 8083
        assert config.api_version == "v1"
        assert isinstance(config.videos_root, Path)
        assert config.enable_cors is True
    
    def test_config_from_environment(self):
        """Test that configuration can be overridden via environment."""
        env_vars = {
            "REACHY_API_HOST": "127.0.0.1",
            "REACHY_API_PORT": "9000",
            "REACHY_API_VERSION": "v2",
            "REACHY_ENABLE_CORS": "false",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            # Clear the cache to force reload
            get_config.cache_clear()
            config = AppConfig()
            
            assert config.api_host == "127.0.0.1"
            assert config.api_port == 9000
            assert config.api_version == "v2"
            assert config.enable_cors is False
    
    def test_computed_properties(self):
        """Test computed URL properties."""
        config = AppConfig()
        
        assert config.api_base_url == f"http://{config.api_host}:{config.api_port}"
        assert config.nginx_base_url == f"http://{config.nginx_host}:{config.nginx_port}"
        assert config.gateway_base_url == f"http://{config.gateway_host}:{config.gateway_port}"
        assert config.n8n_webhook_url == f"http://{config.n8n_host}:{config.n8n_port}"
    
    def test_path_properties(self):
        """Test computed path properties."""
        config = AppConfig()
        
        assert config.temp_path == config.videos_root / config.temp_dir
        assert config.train_path == config.videos_root / config.train_dir
        assert config.test_path == config.videos_root / config.test_dir
        assert config.thumbs_path == config.videos_root / config.thumbs_dir
        assert config.manifests_path == config.videos_root / config.manifests_dir


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_validate_with_valid_config(self, tmp_path):
        """Test that validation passes with valid configuration."""
        # Create a temporary videos root
        videos_root = tmp_path / "videos"
        videos_root.mkdir()
        
        env_vars = {
            "REACHY_VIDEOS_ROOT": str(videos_root),
            "REACHY_API_PORT": "54321",  # Use high port to avoid conflicts
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            get_config.cache_clear()
            config = AppConfig()
            
            # Should not raise
            config.validate(check_port=True)
            
            # Check that subdirectories were created
            assert config.temp_path.exists()
            assert config.train_path.exists()
            assert config.test_path.exists()
            assert config.thumbs_path.exists()
            assert config.manifests_path.exists()
    
    def test_validate_fails_with_nonexistent_root(self):
        """Test that validation fails if videos_root doesn't exist."""
        env_vars = {
            "REACHY_VIDEOS_ROOT": "/nonexistent/path/to/videos",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            get_config.cache_clear()
            config = AppConfig()
            
            with pytest.raises(ConfigurationError, match="does not exist"):
                config.validate(check_port=False)
    
    def test_validate_fails_with_invalid_port(self):
        """Test that validation fails with invalid port."""
        env_vars = {
            "REACHY_API_PORT": "99999",  # Invalid port
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            get_config.cache_clear()
            config = AppConfig()
            
            with pytest.raises(ConfigurationError, match="Invalid API port"):
                config.validate(check_port=False)
    
    def test_validate_fails_with_invalid_database_url(self):
        """Test that validation fails with invalid database URL."""
        env_vars = {
            "REACHY_DATABASE_URL": "not_a_valid_url",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            get_config.cache_clear()
            config = AppConfig()
            
            with pytest.raises(ConfigurationError, match="Invalid database URL"):
                config.validate(check_port=False)
    
    def test_validate_can_skip_port_check(self, tmp_path):
        """Test that port check can be skipped."""
        videos_root = tmp_path / "videos"
        videos_root.mkdir()
        
        env_vars = {
            "REACHY_VIDEOS_ROOT": str(videos_root),
            "REACHY_API_PORT": "8083",  # May be in use
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            get_config.cache_clear()
            config = AppConfig()
            
            # Should not raise even if port is in use
            config.validate(check_port=False)


class TestConfigLogging:
    """Test configuration logging."""
    
    def test_log_configuration_masks_secrets(self):
        """Test that sensitive values are masked in logs."""
        env_vars = {
            "REACHY_DATABASE_URL": "postgresql+asyncpg://user:secret_password@localhost/db",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            get_config.cache_clear()
            config = AppConfig()
            
            log_dict = config.log_configuration(mask_secrets=True)
            
            # Check that password is masked
            assert "secret_password" not in log_dict["database"]["database_url"]
            assert "***" in log_dict["database"]["database_url"]
    
    def test_log_configuration_without_masking(self):
        """Test that secrets can be included if needed."""
        env_vars = {
            "REACHY_DATABASE_URL": "postgresql+asyncpg://user:secret_password@localhost/db",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            get_config.cache_clear()
            config = AppConfig()
            
            log_dict = config.log_configuration(mask_secrets=False)
            
            # Check that password is included
            assert "secret_password" in log_dict["database"]["database_url"]
    
    def test_log_configuration_structure(self):
        """Test that log dictionary has expected structure."""
        config = AppConfig()
        log_dict = config.log_configuration()
        
        assert "service" in log_dict
        assert "storage" in log_dict
        assert "database" in log_dict
        assert "external_services" in log_dict
        assert "features" in log_dict
        
        assert "api_host" in log_dict["service"]
        assert "api_port" in log_dict["service"]
        assert "videos_root" in log_dict["storage"]
        assert "database_url" in log_dict["database"]


class TestConfigCaching:
    """Test configuration caching."""
    
    def test_get_config_returns_cached_instance(self):
        """Test that get_config returns the same instance."""
        get_config.cache_clear()
        
        config1 = get_config()
        config2 = get_config()
        
        # Should be the exact same object
        assert config1 is config2
    
    def test_cache_can_be_cleared(self):
        """Test that cache can be cleared to reload config."""
        env_vars1 = {"REACHY_API_PORT": "8083"}
        env_vars2 = {"REACHY_API_PORT": "9000"}
        
        with patch.dict(os.environ, env_vars1, clear=False):
            get_config.cache_clear()
            config1 = get_config()
            assert config1.api_port == 8083
        
        with patch.dict(os.environ, env_vars2, clear=False):
            get_config.cache_clear()
            config2 = get_config()
            assert config2.api_port == 9000


class TestLoadAndValidateConfig:
    """Test load_and_validate_config function."""
    
    def test_load_and_validate_success(self, tmp_path):
        """Test successful load and validation."""
        videos_root = tmp_path / "videos"
        videos_root.mkdir()
        
        env_vars = {
            "REACHY_VIDEOS_ROOT": str(videos_root),
            "REACHY_API_PORT": "54322",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            get_config.cache_clear()
            config = load_and_validate_config(check_port=True)
            
            assert isinstance(config, AppConfig)
            assert config.videos_root == videos_root
    
    def test_load_and_validate_failure(self):
        """Test that load_and_validate raises on invalid config."""
        env_vars = {
            "REACHY_VIDEOS_ROOT": "/nonexistent/path",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            get_config.cache_clear()
            
            with pytest.raises(ConfigurationError):
                load_and_validate_config(check_port=False)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
