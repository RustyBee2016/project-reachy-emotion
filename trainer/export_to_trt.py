#!/usr/bin/env python3
"""
TensorRT Export Pipeline
Converts trained EmotionNet models to optimized TensorRT engines.
"""

import os
import sys
import argparse
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TensorRTExporter:
    """Export TAO models to TensorRT engines."""
    
    def __init__(
        self,
        model_path: str,
        output_dir: str,
        calibration_data: Optional[str] = None
    ):
        """
        Initialize TensorRT exporter.
        
        Args:
            model_path: Path to trained TAO model
            output_dir: Directory for exported engines
            calibration_data: Optional path to calibration data for INT8
        """
        self.model_path = Path(model_path)
        self.output_dir = Path(output_dir)
        self.calibration_data = Path(calibration_data) if calibration_data else None
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"TensorRT exporter initialized")
        logger.info(f"Model: {self.model_path}")
        logger.info(f"Output: {self.output_dir}")
    
    def export_fp16(
        self,
        engine_name: str,
        batch_size: int = 1,
        input_dims: List[int] = [3, 224, 224]
    ) -> Dict[str, Any]:
        """
        Export model to FP16 TensorRT engine.
        
        Args:
            engine_name: Name for output engine file
            batch_size: Batch size for engine
            input_dims: Input dimensions [C, H, W]
        
        Returns:
            Export results dictionary
        """
        logger.info(f"Exporting FP16 engine: {engine_name}")
        
        output_path = self.output_dir / f"{engine_name}_fp16.engine"
        
        # Build TAO export command
        export_cmd = [
            "docker", "exec", "reachy-tao-export",
            "tao", "emotionnet", "export",
            "-m", f"/workspace/experiments/{self.model_path.name}",
            "-k", os.getenv("TAO_API_KEY", "tlt_encode"),
            "-o", f"/workspace/engines/{output_path.name}",
            "--data_type", "fp16",
            "--batch_size", str(batch_size),
            "--input_dims", ",".join(map(str, input_dims))
        ]
        
        logger.info(f"Export command: {' '.join(export_cmd)}")
        
        try:
            result = subprocess.run(
                export_cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Export failed: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr,
                    'engine_path': None
                }
            
            logger.info(f"FP16 export completed: {output_path}")
            
            # Verify engine was created
            if not output_path.exists():
                return {
                    'success': False,
                    'error': 'Engine file not found after export',
                    'engine_path': None
                }
            
            # Get engine size
            engine_size_mb = output_path.stat().st_size / (1024 * 1024)
            
            return {
                'success': True,
                'engine_path': str(output_path),
                'precision': 'fp16',
                'batch_size': batch_size,
                'input_dims': input_dims,
                'size_mb': round(engine_size_mb, 2)
            }
            
        except subprocess.TimeoutExpired:
            logger.error("Export timeout exceeded")
            return {
                'success': False,
                'error': 'Export timeout',
                'engine_path': None
            }
        except Exception as e:
            logger.error(f"Export error: {e}")
            return {
                'success': False,
                'error': str(e),
                'engine_path': None
            }
    
    def export_int8(
        self,
        engine_name: str,
        batch_size: int = 1,
        input_dims: List[int] = [3, 224, 224],
        calibration_images: int = 500
    ) -> Dict[str, Any]:
        """
        Export model to INT8 TensorRT engine with calibration.
        
        Args:
            engine_name: Name for output engine file
            batch_size: Batch size for engine
            input_dims: Input dimensions [C, H, W]
            calibration_images: Number of images for calibration
        
        Returns:
            Export results dictionary
        """
        logger.info(f"Exporting INT8 engine: {engine_name}")
        
        if not self.calibration_data or not self.calibration_data.exists():
            logger.warning("No calibration data provided, falling back to FP16")
            return self.export_fp16(engine_name, batch_size, input_dims)
        
        output_path = self.output_dir / f"{engine_name}_int8.engine"
        
        # Build TAO export command with calibration
        export_cmd = [
            "docker", "exec", "reachy-tao-export",
            "tao", "emotionnet", "export",
            "-m", f"/workspace/experiments/{self.model_path.name}",
            "-k", os.getenv("TAO_API_KEY", "tlt_encode"),
            "-o", f"/workspace/engines/{output_path.name}",
            "--data_type", "int8",
            "--batch_size", str(batch_size),
            "--input_dims", ",".join(map(str, input_dims)),
            "--cal_data_file", f"/workspace/calibration/{self.calibration_data.name}",
            "--cal_image_dir", "/workspace/calibration",
            "--cal_cache_file", f"/workspace/engines/{engine_name}_cal.bin",
            "--max_calibration_batches", str(calibration_images // batch_size)
        ]
        
        logger.info(f"Export command: {' '.join(export_cmd)}")
        
        try:
            result = subprocess.run(
                export_cmd,
                capture_output=True,
                text=True,
                timeout=900  # 15 minute timeout for INT8
            )
            
            if result.returncode != 0:
                logger.error(f"INT8 export failed: {result.stderr}")
                logger.info("Falling back to FP16")
                return self.export_fp16(engine_name, batch_size, input_dims)
            
            logger.info(f"INT8 export completed: {output_path}")
            
            if not output_path.exists():
                return {
                    'success': False,
                    'error': 'Engine file not found after export',
                    'engine_path': None
                }
            
            engine_size_mb = output_path.stat().st_size / (1024 * 1024)
            
            return {
                'success': True,
                'engine_path': str(output_path),
                'precision': 'int8',
                'batch_size': batch_size,
                'input_dims': input_dims,
                'size_mb': round(engine_size_mb, 2),
                'calibration_images': calibration_images
            }
            
        except subprocess.TimeoutExpired:
            logger.error("INT8 export timeout, falling back to FP16")
            return self.export_fp16(engine_name, batch_size, input_dims)
        except Exception as e:
            logger.error(f"INT8 export error: {e}, falling back to FP16")
            return self.export_fp16(engine_name, batch_size, input_dims)
    
    def verify_engine(
        self,
        engine_path: str,
        input_dims: List[int] = [3, 224, 224]
    ) -> Dict[str, Any]:
        """
        Verify TensorRT engine with trtexec.
        
        Args:
            engine_path: Path to engine file
            input_dims: Input dimensions for verification
        
        Returns:
            Verification results
        """
        logger.info(f"Verifying engine: {engine_path}")
        
        engine_file = Path(engine_path)
        if not engine_file.exists():
            return {
                'success': False,
                'error': 'Engine file not found'
            }
        
        # Build trtexec command
        verify_cmd = [
            "docker", "exec", "reachy-tao-export",
            "trtexec",
            "--loadEngine", f"/workspace/engines/{engine_file.name}",
            "--shapes", f"input:1x{input_dims[0]}x{input_dims[1]}x{input_dims[2]}",
            "--verbose"
        ]
        
        try:
            result = subprocess.run(
                verify_cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                logger.error(f"Verification failed: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr
                }
            
            # Parse performance metrics from output
            metrics = self._parse_trtexec_output(result.stdout)
            
            logger.info(f"Engine verified successfully")
            logger.info(f"Performance: {metrics}")
            
            return {
                'success': True,
                'metrics': metrics
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Verification timeout'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _parse_trtexec_output(self, output: str) -> Dict[str, float]:
        """
        Parse trtexec output for performance metrics.
        
        Args:
            output: trtexec stdout
        
        Returns:
            Dictionary of performance metrics
        """
        metrics = {
            'latency_mean_ms': None,
            'latency_p50_ms': None,
            'latency_p95_ms': None,
            'latency_p99_ms': None,
            'throughput_qps': None
        }
        
        lines = output.split('\n')
        for line in lines:
            # Parse latency metrics
            if 'mean' in line.lower() and 'ms' in line.lower():
                try:
                    # Example: "[I] mean: 45.2 ms" or "mean = 45.2 ms"
                    if ':' in line:
                        parts = line.split(':')
                    else:
                        parts = line.split('=')
                    if len(parts) >= 2:
                        value_str = parts[1].strip().split()[0]
                        value = float(value_str)
                        metrics['latency_mean_ms'] = value
                except (ValueError, IndexError):
                    pass
            
            # Parse percentiles
            if 'percentile' in line.lower():
                try:
                    # Handle both "percentile(50%): 44.8 ms" and "percentile(50%) = 44.8 ms"
                    if ':' in line:
                        value_str = line.split(':')[1].strip().split()[0]
                    else:
                        value_str = line.split('=')[1].strip().split()[0]
                    value = float(value_str)
                    
                    if '50%' in line or 'p50' in line.lower():
                        metrics['latency_p50_ms'] = value
                    elif '95%' in line or 'p95' in line.lower():
                        metrics['latency_p95_ms'] = value
                    elif '99%' in line or 'p99' in line.lower():
                        metrics['latency_p99_ms'] = value
                except (ValueError, IndexError):
                    pass
            
            # Parse throughput
            if 'throughput' in line.lower() or 'qps' in line.lower():
                try:
                    # Handle both "throughput: 22.1 qps" and "throughput = 22.1 qps"
                    if ':' in line:
                        value_str = line.split(':')[1].strip().split()[0]
                    else:
                        value_str = line.split('=')[1].strip().split()[0]
                    value = float(value_str)
                    metrics['throughput_qps'] = value
                except (ValueError, IndexError):
                    pass
        
        return metrics
    
    def export_pipeline(
        self,
        engine_name: str,
        precision: str = 'fp16',
        batch_size: int = 1,
        verify: bool = True
    ) -> Dict[str, Any]:
        """
        Run complete export pipeline.
        
        Args:
            engine_name: Name for output engine
            precision: 'fp16' or 'int8'
            batch_size: Batch size for engine
            verify: Whether to verify engine after export
        
        Returns:
            Pipeline results
        """
        logger.info(f"=" * 60)
        logger.info(f"Starting export pipeline: {engine_name}")
        logger.info(f"Precision: {precision}, Batch size: {batch_size}")
        logger.info(f"=" * 60)
        
        results = {
            'engine_name': engine_name,
            'precision': precision,
            'batch_size': batch_size
        }
        
        # Export model
        if precision == 'int8':
            export_result = self.export_int8(engine_name, batch_size)
        else:
            export_result = self.export_fp16(engine_name, batch_size)
        
        results['export'] = export_result
        
        if not export_result['success']:
            results['status'] = 'failed'
            return results
        
        # Verify engine
        if verify:
            verify_result = self.verify_engine(export_result['engine_path'])
            results['verification'] = verify_result
            
            if verify_result['success']:
                results['status'] = 'completed'
            else:
                results['status'] = 'completed_verification_failed'
        else:
            results['status'] = 'completed'
        
        logger.info(f"=" * 60)
        logger.info(f"Export pipeline finished: {results['status']}")
        logger.info(f"=" * 60)
        
        return results


def main():
    """Main entry point for TensorRT export."""
    parser = argparse.ArgumentParser(description='Export EmotionNet to TensorRT')
    parser.add_argument('--model', required=True, help='Path to trained TAO model')
    parser.add_argument('--output', required=True, help='Output directory for engines')
    parser.add_argument('--name', required=True, help='Engine name')
    parser.add_argument('--precision', choices=['fp16', 'int8'], default='fp16', help='Precision mode')
    parser.add_argument('--batch-size', type=int, default=1, help='Batch size')
    parser.add_argument('--calibration-data', help='Path to calibration data for INT8')
    parser.add_argument('--no-verify', action='store_true', help='Skip engine verification')
    
    args = parser.parse_args()
    
    # Create exporter
    exporter = TensorRTExporter(
        model_path=args.model,
        output_dir=args.output,
        calibration_data=args.calibration_data
    )
    
    # Run export pipeline
    results = exporter.export_pipeline(
        engine_name=args.name,
        precision=args.precision,
        batch_size=args.batch_size,
        verify=not args.no_verify
    )
    
    # Print results
    print("\n" + "=" * 60)
    print("EXPORT RESULTS")
    print("=" * 60)
    print(json.dumps(results, indent=2))
    print("=" * 60)
    
    # Exit with appropriate code
    if results['status'] in ['completed', 'completed_verification_failed']:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
