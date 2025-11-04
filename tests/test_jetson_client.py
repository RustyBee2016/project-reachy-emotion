"""
Tests for Jetson WebSocket client and monitoring.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from jetson.monitoring.system_monitor import JetsonMonitor


class TestEmotionClient:
    """Test Jetson emotion WebSocket client."""
    
    def test_client_file_exists(self):
        """Test client file exists."""
        client_file = Path(__file__).parent.parent / "jetson/emotion_client.py"
        assert client_file.exists()
    
    def test_client_has_shebang(self):
        """Test client script has shebang."""
        client_file = Path(__file__).parent.parent / "jetson/emotion_client.py"
        
        with open(client_file) as f:
            first_line = f.readline()
        
        assert first_line.startswith('#!')
        assert 'python' in first_line.lower()


class TestSystemMonitor:
    """Test Jetson system monitor."""
    
    def test_monitor_initialization(self):
        """Test monitor initialization."""
        monitor = JetsonMonitor(log_interval=5)
        
        assert monitor.log_interval == 5
        assert monitor.frame_count == 0
        assert len(monitor.inference_times) == 0
    
    def test_record_inference(self):
        """Test recording inference times."""
        monitor = JetsonMonitor()
        
        # Record some inferences
        for i in range(10):
            monitor.record_inference(45.0 + i)
        
        assert monitor.frame_count == 10
        assert len(monitor.inference_times) == 10
    
    def test_inference_buffer_limit(self):
        """Test inference time buffer is limited."""
        monitor = JetsonMonitor()
        
        # Record more than buffer size
        for i in range(1500):
            monitor.record_inference(45.0)
        
        # Should keep only last 1000
        assert len(monitor.inference_times) == 1000
        assert monitor.frame_count == 1500
    
    def test_get_performance_stats_empty(self):
        """Test performance stats with no data."""
        monitor = JetsonMonitor()
        
        stats = monitor.get_performance_stats()
        
        assert stats['frame_count'] == 0
        assert stats['fps'] == 0.0
        assert stats['latency_mean_ms'] is None
    
    def test_get_performance_stats_with_data(self):
        """Test performance stats with data."""
        monitor = JetsonMonitor()
        
        # Record some inferences
        times = [40.0, 45.0, 50.0, 55.0, 60.0]
        for t in times:
            monitor.record_inference(t)
        
        stats = monitor.get_performance_stats()
        
        assert stats['frame_count'] == 5
        assert stats['fps'] > 0
        assert stats['latency_mean_ms'] == 50.0
        assert stats['latency_p50_ms'] == 50.0
    
    def test_get_cpu_stats(self):
        """Test CPU statistics retrieval."""
        monitor = JetsonMonitor()
        
        stats = monitor.get_cpu_stats()
        
        assert 'cpu_percent' in stats
        assert 'cpu_count' in stats
        assert isinstance(stats['cpu_count'], int)
    
    def test_get_memory_stats(self):
        """Test memory statistics retrieval."""
        monitor = JetsonMonitor()
        
        stats = monitor.get_memory_stats()
        
        assert 'total_mb' in stats
        assert 'used_mb' in stats
        assert 'percent' in stats
        assert stats['total_mb'] > 0
    
    def test_get_disk_stats(self):
        """Test disk statistics retrieval."""
        monitor = JetsonMonitor()
        
        stats = monitor.get_disk_stats()
        
        assert 'total_gb' in stats
        assert 'used_gb' in stats
        assert 'free_gb' in stats
        assert 'percent' in stats
    
    def test_get_gpu_stats_mock(self):
        """Test GPU stats returns mock data on non-Jetson."""
        monitor = JetsonMonitor()
        
        # Should return mock data since not on Jetson
        stats = monitor.get_gpu_stats()
        
        # Mock data should have these fields
        assert 'gpu_util' in stats or len(stats) == 0
    
    def test_get_all_stats(self):
        """Test getting all statistics."""
        monitor = JetsonMonitor()
        
        # Record some data
        monitor.record_inference(45.0)
        
        stats = monitor.get_all_stats()
        
        assert 'timestamp' in stats
        assert 'uptime_seconds' in stats
        assert 'gpu' in stats
        assert 'cpu' in stats
        assert 'memory' in stats
        assert 'disk' in stats
        assert 'performance' in stats
    
    def test_check_thermal_throttling_normal(self):
        """Test thermal throttling check with normal temps."""
        monitor = JetsonMonitor()
        
        with patch.object(monitor, 'get_gpu_stats', return_value={
            'temp_gpu': 55.0,
            'temp_cpu': 60.0
        }):
            throttling = monitor.check_thermal_throttling()
            assert throttling is False
    
    def test_check_thermal_throttling_high_gpu(self):
        """Test thermal throttling with high GPU temp."""
        monitor = JetsonMonitor()
        
        with patch.object(monitor, 'get_gpu_stats', return_value={
            'temp_gpu': 80.0,
            'temp_cpu': 60.0
        }):
            throttling = monitor.check_thermal_throttling()
            assert throttling is True
    
    def test_check_thermal_throttling_high_cpu(self):
        """Test thermal throttling with high CPU temp."""
        monitor = JetsonMonitor()
        
        with patch.object(monitor, 'get_gpu_stats', return_value={
            'temp_gpu': 55.0,
            'temp_cpu': 85.0
        }):
            throttling = monitor.check_thermal_throttling()
            assert throttling is True
    
    def test_parse_tegrastats(self):
        """Test parsing tegrastats output."""
        monitor = JetsonMonitor()
        
        # Sample tegrastats output
        output = """
RAM 2847/7850MB (lfb 1x4MB) CPU [25%@1420,25%@1420,25%@1420,25%@1420] 
EMC_FREQ 0% GR3D_FREQ 45% PLL@42C CPU@44.5C PMIC@100C GPU@43C
"""
        
        stats = monitor._parse_tegrastats(output)
        
        # Should parse GPU utilization
        assert stats['gpu_util'] == 45.0
        
        # Should parse temperatures
        assert stats['temp_gpu'] == 43.0
        assert stats['temp_cpu'] == 44.5
        
        # Should parse RAM
        assert stats['ram_used_mb'] == 2847
        assert stats['ram_total_mb'] == 7850


class TestMonitoringFiles:
    """Test monitoring file structure."""
    
    def test_monitoring_directory_exists(self):
        """Test monitoring directory exists."""
        monitoring_dir = Path(__file__).parent.parent / "jetson/monitoring"
        assert monitoring_dir.exists()
        assert monitoring_dir.is_dir()
    
    def test_system_monitor_exists(self):
        """Test system monitor file exists."""
        monitor_file = Path(__file__).parent.parent / "jetson/monitoring/system_monitor.py"
        assert monitor_file.exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
