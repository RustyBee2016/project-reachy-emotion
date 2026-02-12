#!/usr/bin/env python3
"""
Reachy Emotion Detection - Main Entry Point
Integrates DeepStream pipeline, WebSocket client, and system monitoring.
"""

import asyncio
import signal
import sys
import logging
import argparse
from pathlib import Path

from emotion_client import EmotionClient
from monitoring.system_monitor import JetsonMonitor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmotionDetectionService:
    """Main service coordinating all components."""
    
    def __init__(
        self,
        deepstream_config: str,
        gateway_url: str,
        device_id: str
    ):
        """
        Initialize emotion detection service.
        
        Args:
            deepstream_config: Path to DeepStream config
            gateway_url: WebSocket gateway URL
            device_id: Device identifier
        """
        self.deepstream_config = deepstream_config
        self.gateway_url = gateway_url
        self.device_id = device_id
        
        # Components
        self.ws_client = None
        self.monitor = None
        self.running = False
        
        logger.info(f"Emotion detection service initialized: {device_id}")
    
    async def start(self):
        """Start all service components."""
        logger.info("Starting emotion detection service...")
        
        try:
            # Initialize monitor
            self.monitor = JetsonMonitor(log_interval=5)
            logger.info("System monitor initialized")
            
            # Initialize WebSocket client
            self.ws_client = EmotionClient(
                gateway_url=self.gateway_url,
                device_id=self.device_id
            )
            
            # Connect to gateway
            await self.ws_client.connect()
            logger.info("Connected to gateway")
            
            # Start DeepStream pipeline (would be integrated here)
            # For now, simulate with mock events
            self.running = True
            
            # Start monitoring loop
            asyncio.create_task(self._monitoring_loop())
            
            # Start emotion processing loop
            await self._emotion_loop()
            
        except Exception as e:
            logger.error(f"Failed to start service: {e}", exc_info=True)
            raise
    
    async def stop(self):
        """Stop all service components."""
        logger.info("Stopping emotion detection service...")
        
        self.running = False
        
        if self.ws_client:
            await self.ws_client.disconnect()
        
        logger.info("Service stopped")
    
    async def _emotion_loop(self):
        """Main emotion detection loop."""
        logger.info("Starting emotion detection loop...")
        
        frame_count = 0
        
        while self.running:
            try:
                # In production, this would get emotions from DeepStream
                # For now, simulate
                import random
                from datetime import datetime
                
                emotion = random.choice(['happy', 'sad', 'neutral'])
                confidence = 0.80 + random.random() * 0.15
                inference_ms = 40.0 + random.random() * 20.0
                
                # Record inference time
                if self.monitor:
                    self.monitor.record_inference(inference_ms)
                
                # Send emotion event
                event = {
                    'emotion': emotion,
                    'confidence': confidence,
                    'inference_ms': inference_ms,
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'frame_number': frame_count
                }
                
                await self.ws_client.send_emotion_event(event)
                
                frame_count += 1
                
                # ~30 FPS
                await asyncio.sleep(0.033)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in emotion loop: {e}")
                await asyncio.sleep(1)
    
    async def _monitoring_loop(self):
        """System monitoring loop."""
        while self.running:
            try:
                # Log stats every 5 seconds
                await asyncio.sleep(5)
                
                if self.monitor:
                    self.monitor.log_stats()
                    
                    # Check thermal throttling
                    if self.monitor.check_thermal_throttling():
                        logger.warning("Thermal throttling detected!")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Reachy Emotion Detection Service')
    parser.add_argument('--config', required=True, help='DeepStream config file')
    parser.add_argument('--gateway', default='http://10.0.4.140:8000', help='Gateway URL')
    parser.add_argument('--device-id', default='reachy-mini-01', help='Device ID')
    
    args = parser.parse_args()
    
    # Create service
    service = EmotionDetectionService(
        deepstream_config=args.config,
        gateway_url=args.gateway,
        device_id=args.device_id
    )
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        asyncio.create_task(service.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start service
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Service error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await service.stop()


if __name__ == '__main__':
    asyncio.run(main())
