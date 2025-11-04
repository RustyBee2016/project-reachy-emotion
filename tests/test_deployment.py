"""
Tests for Jetson deployment components.
"""
import pytest
from pathlib import Path


class TestSystemdService:
    """Test systemd service configuration."""
    
    def test_service_file_exists(self):
        """Test service file exists."""
        service_file = Path(__file__).parent.parent / "jetson/systemd/reachy-emotion.service"
        assert service_file.exists()
    
    def test_service_file_structure(self):
        """Test service file has required sections."""
        service_file = Path(__file__).parent.parent / "jetson/systemd/reachy-emotion.service"
        
        with open(service_file) as f:
            content = f.read()
        
        # Check required sections
        assert '[Unit]' in content
        assert '[Service]' in content
        assert '[Install]' in content
        
        # Check key directives
        assert 'ExecStart=' in content
        assert 'Restart=' in content
        assert 'WantedBy=' in content
    
    def test_service_restart_policy(self):
        """Test service has restart policy."""
        service_file = Path(__file__).parent.parent / "jetson/systemd/reachy-emotion.service"
        
        with open(service_file) as f:
            content = f.read()
        
        assert 'Restart=always' in content
        assert 'RestartSec=' in content
    
    def test_service_resource_limits(self):
        """Test service has resource limits."""
        service_file = Path(__file__).parent.parent / "jetson/systemd/reachy-emotion.service"
        
        with open(service_file) as f:
            content = f.read()
        
        assert 'MemoryLimit=' in content
        assert 'CPUQuota=' in content


class TestMainService:
    """Test main service entry point."""
    
    def test_main_file_exists(self):
        """Test main service file exists."""
        main_file = Path(__file__).parent.parent / "jetson/emotion_main.py"
        assert main_file.exists()
    
    def test_main_has_shebang(self):
        """Test main script has shebang."""
        main_file = Path(__file__).parent.parent / "jetson/emotion_main.py"
        
        with open(main_file) as f:
            first_line = f.readline()
        
        assert first_line.startswith('#!')
        assert 'python' in first_line.lower()
    
    def test_main_imports(self):
        """Test main script has required imports."""
        main_file = Path(__file__).parent.parent / "jetson/emotion_main.py"
        
        with open(main_file) as f:
            content = f.read()
        
        # Check key imports
        assert 'import asyncio' in content
        assert 'import signal' in content
        assert 'from emotion_client import EmotionClient' in content
        assert 'from monitoring.system_monitor import JetsonMonitor' in content


class TestDeploymentScript:
    """Test deployment script."""
    
    def test_deploy_script_exists(self):
        """Test deployment script exists."""
        deploy_script = Path(__file__).parent.parent / "jetson/deploy.sh"
        assert deploy_script.exists()
    
    def test_deploy_script_is_bash(self):
        """Test deployment script is bash."""
        deploy_script = Path(__file__).parent.parent / "jetson/deploy.sh"
        
        with open(deploy_script) as f:
            first_line = f.readline()
        
        assert first_line.startswith('#!')
        assert 'bash' in first_line.lower()
    
    def test_deploy_script_has_error_handling(self):
        """Test deployment script has error handling."""
        deploy_script = Path(__file__).parent.parent / "jetson/deploy.sh"
        
        with open(deploy_script) as f:
            content = f.read()
        
        assert 'set -e' in content  # Exit on error
    
    def test_deploy_script_checks_prerequisites(self):
        """Test deployment script checks prerequisites."""
        deploy_script = Path(__file__).parent.parent / "jetson/deploy.sh"
        
        with open(deploy_script) as f:
            content = f.read()
        
        # Should check for required commands
        assert 'command -v' in content or 'which' in content


class TestJetsonFileStructure:
    """Test Jetson directory structure."""
    
    def test_jetson_directory_exists(self):
        """Test jetson directory exists."""
        jetson_dir = Path(__file__).parent.parent / "jetson"
        assert jetson_dir.exists()
        assert jetson_dir.is_dir()
    
    def test_deepstream_directory_exists(self):
        """Test deepstream directory exists."""
        deepstream_dir = Path(__file__).parent.parent / "jetson/deepstream"
        assert deepstream_dir.exists()
        assert deepstream_dir.is_dir()
    
    def test_systemd_directory_exists(self):
        """Test systemd directory exists."""
        systemd_dir = Path(__file__).parent.parent / "jetson/systemd"
        assert systemd_dir.exists()
        assert systemd_dir.is_dir()
    
    def test_monitoring_directory_exists(self):
        """Test monitoring directory exists."""
        monitoring_dir = Path(__file__).parent.parent / "jetson/monitoring"
        assert monitoring_dir.exists()
        assert monitoring_dir.is_dir()
    
    def test_all_required_files_present(self):
        """Test all required files are present."""
        jetson_dir = Path(__file__).parent.parent / "jetson"
        
        required_files = [
            'emotion_main.py',
            'emotion_client.py',
            'deepstream_wrapper.py',
            'deploy.sh',
            'deepstream/emotion_pipeline.txt',
            'deepstream/emotion_inference.txt',
            'deepstream/emotion_labels.txt',
            'systemd/reachy-emotion.service',
            'monitoring/system_monitor.py'
        ]
        
        for file_path in required_files:
            full_path = jetson_dir / file_path
            assert full_path.exists(), f"Missing required file: {file_path}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
