#!/usr/bin/env python3
"""
Jetson System Monitor
Tracks GPU utilization, temperature, memory, and performance metrics.
"""

import os
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import subprocess

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JetsonMonitor:
    """Monitor Jetson system resources and performance."""
    
    def __init__(self, log_interval: int = 5):
        """
        Initialize system monitor.
        
        Args:
            log_interval: Logging interval in seconds
        """
        self.log_interval = log_interval
        self.start_time = datetime.now()
        
        # Performance tracking
        self.frame_count = 0
        self.inference_times = []
        
        logger.info("Jetson monitor initialized")
    
    def get_gpu_stats(self) -> Dict[str, Any]:
        """
        Get GPU statistics using tegrastats.
        
        Returns:
            GPU statistics dictionary
        """
        try:
            # Run tegrastats once
            result = subprocess.run(
                ['tegrastats', '--interval', '100'],
                capture_output=True,
                text=True,
                timeout=1
            )
            
            # Parse output
            output = result.stdout
            stats = self._parse_tegrastats(output)
            
            return stats
            
        except subprocess.TimeoutExpired:
            # Expected - tegrastats runs continuously
            return {}
        except FileNotFoundError:
            # tegrastats not available (not on Jetson)
            return self._get_mock_gpu_stats()
        except Exception as e:
            logger.error(f"Failed to get GPU stats: {e}")
            return {}
    
    def _parse_tegrastats(self, output: str) -> Dict[str, Any]:
        """
        Parse tegrastats output.
        
        Args:
            output: tegrastats output string
        
        Returns:
            Parsed statistics
        """
        stats = {
            'gpu_util': None,
            'gpu_freq_mhz': None,
            'cpu_util': None,
            'temp_cpu': None,
            'temp_gpu': None,
            'power_mw': None,
            'ram_used_mb': None,
            'ram_total_mb': None
        }
        
        try:
            # Example tegrastats output:
            # RAM 2847/7850MB (lfb 1x4MB) CPU [25%@1420,25%@1420,25%@1420,25%@1420] 
            # EMC_FREQ 0% GR3D_FREQ 0% PLL@42C CPU@44.5C PMIC@100C GPU@43C
            
            lines = output.strip().split('\n')
            if not lines:
                return stats
            
            line = lines[-1]  # Get last line
            
            # Parse GPU frequency
            if 'GR3D_FREQ' in line:
                parts = line.split('GR3D_FREQ')
                if len(parts) > 1:
                    freq_str = parts[1].split('%')[0].strip()
                    try:
                        stats['gpu_util'] = float(freq_str)
                    except ValueError:
                        pass
            
            # Parse temperatures
            if 'GPU@' in line:
                temp_str = line.split('GPU@')[1].split('C')[0]
                try:
                    stats['temp_gpu'] = float(temp_str)
                except ValueError:
                    pass
            
            if 'CPU@' in line:
                temp_str = line.split('CPU@')[1].split('C')[0]
                try:
                    stats['temp_cpu'] = float(temp_str)
                except ValueError:
                    pass
            
            # Parse RAM
            if 'RAM' in line:
                ram_str = line.split('RAM')[1].split('MB')[0].strip()
                if '/' in ram_str:
                    used, total = ram_str.split('/')
                    try:
                        stats['ram_used_mb'] = int(used)
                        stats['ram_total_mb'] = int(total)
                    except ValueError:
                        pass
        
        except Exception as e:
            logger.error(f"Failed to parse tegrastats: {e}")
        
        return stats
    
    def _get_mock_gpu_stats(self) -> Dict[str, Any]:
        """Get mock GPU stats for testing on non-Jetson systems."""
        return {
            'gpu_util': 45.0,
            'gpu_freq_mhz': 1300,
            'cpu_util': 35.0,
            'temp_cpu': 55.0,
            'temp_gpu': 52.0,
            'power_mw': 8500,
            'ram_used_mb': 2847,
            'ram_total_mb': 7850
        }
    
    def get_cpu_stats(self) -> Dict[str, Any]:
        """
        Get CPU statistics using psutil.
        
        Returns:
            CPU statistics dictionary
        """
        if not PSUTIL_AVAILABLE:
            return {}
        
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'cpu_count': psutil.cpu_count(),
                'cpu_freq_mhz': psutil.cpu_freq().current if psutil.cpu_freq() else None,
                'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else None
            }
        except Exception as e:
            logger.error(f"Failed to get CPU stats: {e}")
            return {}
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics.
        
        Returns:
            Memory statistics dictionary
        """
        if not PSUTIL_AVAILABLE:
            return {}
        
        try:
            mem = psutil.virtual_memory()
            return {
                'total_mb': mem.total / (1024 * 1024),
                'used_mb': mem.used / (1024 * 1024),
                'available_mb': mem.available / (1024 * 1024),
                'percent': mem.percent
            }
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {}
    
    def get_disk_stats(self) -> Dict[str, Any]:
        """
        Get disk statistics.
        
        Returns:
            Disk statistics dictionary
        """
        if not PSUTIL_AVAILABLE:
            return {}
        
        try:
            disk = psutil.disk_usage('/')
            return {
                'total_gb': disk.total / (1024 ** 3),
                'used_gb': disk.used / (1024 ** 3),
                'free_gb': disk.free / (1024 ** 3),
                'percent': disk.percent
            }
        except Exception as e:
            logger.error(f"Failed to get disk stats: {e}")
            return {}
    
    def record_inference(self, inference_time_ms: float):
        """
        Record inference time for performance tracking.
        
        Args:
            inference_time_ms: Inference time in milliseconds
        """
        self.frame_count += 1
        self.inference_times.append(inference_time_ms)
        
        # Keep only last 1000 samples
        if len(self.inference_times) > 1000:
            self.inference_times = self.inference_times[-1000:]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            Performance statistics dictionary
        """
        if not self.inference_times:
            return {
                'frame_count': self.frame_count,
                'fps': 0.0,
                'latency_mean_ms': None,
                'latency_p50_ms': None,
                'latency_p95_ms': None,
                'latency_p99_ms': None
            }
        
        # Calculate FPS
        uptime = (datetime.now() - self.start_time).total_seconds()
        fps = self.frame_count / uptime if uptime > 0 else 0.0
        
        # Calculate latency percentiles
        sorted_times = sorted(self.inference_times)
        n = len(sorted_times)
        
        return {
            'frame_count': self.frame_count,
            'fps': round(fps, 2),
            'latency_mean_ms': round(sum(sorted_times) / n, 2),
            'latency_p50_ms': round(sorted_times[int(n * 0.50)], 2),
            'latency_p95_ms': round(sorted_times[int(n * 0.95)], 2),
            'latency_p99_ms': round(sorted_times[int(n * 0.99)], 2)
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """
        Get all system statistics.
        
        Returns:
            Complete statistics dictionary
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
            'gpu': self.get_gpu_stats(),
            'cpu': self.get_cpu_stats(),
            'memory': self.get_memory_stats(),
            'disk': self.get_disk_stats(),
            'performance': self.get_performance_stats()
        }
    
    def check_thermal_throttling(self) -> bool:
        """
        Check if system is thermal throttling.
        
        Returns:
            True if throttling detected
        """
        gpu_stats = self.get_gpu_stats()
        
        # Check GPU temperature
        if gpu_stats.get('temp_gpu'):
            if gpu_stats['temp_gpu'] > 75.0:
                logger.warning(f"High GPU temperature: {gpu_stats['temp_gpu']}°C")
                return True
        
        # Check CPU temperature
        if gpu_stats.get('temp_cpu'):
            if gpu_stats['temp_cpu'] > 80.0:
                logger.warning(f"High CPU temperature: {gpu_stats['temp_cpu']}°C")
                return True
        
        return False
    
    def log_stats(self):
        """Log current statistics."""
        stats = self.get_all_stats()
        
        logger.info(f"Performance: {stats['performance']['fps']:.1f} FPS, "
                   f"Latency: {stats['performance']['latency_p95_ms']:.1f}ms (p95)")
        
        if stats['gpu'].get('temp_gpu'):
            logger.info(f"GPU: {stats['gpu']['gpu_util']:.0f}% @ {stats['gpu']['temp_gpu']:.1f}°C")
        
        logger.info(f"Memory: {stats['memory']['used_mb']:.0f}/{stats['memory']['total_mb']:.0f} MB "
                   f"({stats['memory']['percent']:.1f}%)")


def main():
    """Main entry point for testing."""
    monitor = JetsonMonitor(log_interval=5)
    
    print("Jetson System Monitor")
    print("=" * 60)
    
    try:
        while True:
            # Simulate inference
            import random
            inference_time = 45.0 + random.uniform(-5, 5)
            monitor.record_inference(inference_time)
            
            # Log stats periodically
            if monitor.frame_count % 30 == 0:
                monitor.log_stats()
                
                # Check thermal throttling
                if monitor.check_thermal_throttling():
                    print("⚠️  Thermal throttling detected!")
            
            time.sleep(0.033)  # ~30 FPS
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        
        # Final stats
        stats = monitor.get_all_stats()
        import json
        print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    main()
