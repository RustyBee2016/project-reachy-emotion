#!/usr/bin/env python3
"""
Reachy Emotion Detection - Main Entry Point.

Integrates DeepStream pipeline, WebSocket client, and system monitoring.
Supports two modes:
  --mode deepstream  (default) — real inference via DeepStream + nvinfer
  --mode simulate               — mock emotion loop for development/testing
"""

import asyncio
import logging
import argparse
import signal
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from emotion_client import EmotionClient
from monitoring.system_monitor import JetsonMonitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class EmotionDetectionService:
    """Main service coordinating DeepStream, WebSocket, and monitoring."""

    def __init__(
        self,
        deepstream_config: str,
        gateway_url: str,
        device_id: str,
        *,
        mode: str = "deepstream",
    ):
        self.deepstream_config = deepstream_config
        self.gateway_url = gateway_url
        self.device_id = device_id
        self.mode = mode

        self.ws_client: Optional[EmotionClient] = None
        self.monitor: Optional[JetsonMonitor] = None
        self.running = False

        # DeepStream pipeline (only used in deepstream mode).
        self._ds_pipeline = None
        self._ds_thread: Optional[threading.Thread] = None

        # Queue for passing DeepStream events to the async loop.
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=128)

        logger.info("Emotion detection service initialized: %s (mode=%s)", device_id, mode)

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def start(self):
        """Start all service components."""
        logger.info("Starting emotion detection service...")

        self.monitor = JetsonMonitor(log_interval=5)
        logger.info("System monitor initialized")

        self.ws_client = EmotionClient(
            gateway_url=self.gateway_url,
            device_id=self.device_id,
        )
        await self.ws_client.connect()
        logger.info("Connected to gateway")

        self.running = True
        asyncio.create_task(self._monitoring_loop())

        if self.mode == "deepstream":
            self._start_deepstream()
            await self._event_dispatch_loop()
        else:
            await self._simulated_emotion_loop()

    async def stop(self):
        """Stop all service components."""
        logger.info("Stopping emotion detection service...")
        self.running = False

        if self._ds_pipeline:
            self._ds_pipeline.stop()
        if self._ds_thread and self._ds_thread.is_alive():
            self._ds_thread.join(timeout=5)

        if self.ws_client:
            await self.ws_client.disconnect()

        logger.info("Service stopped")

    # ── DeepStream integration ─────────────────────────────────────────

    def _start_deepstream(self):
        """Build and start DeepStream in a background thread.

        DeepStream's GLib.MainLoop is blocking so it must run off the
        asyncio event loop.  Emotion events are pushed into an asyncio
        Queue via the on_emotion_callback.
        """
        from deepstream_wrapper import DeepStreamPipeline

        loop = asyncio.get_running_loop()

        def _on_emotion(event: dict):
            """Thread-safe callback from DeepStream probe."""
            try:
                loop.call_soon_threadsafe(self._event_queue.put_nowait, event)
            except asyncio.QueueFull:
                pass  # Drop frame rather than block DeepStream

        self._ds_pipeline = DeepStreamPipeline(
            config_file=self.deepstream_config,
            on_emotion_callback=_on_emotion,
        )

        if not self._ds_pipeline.build_pipeline():
            raise RuntimeError("Failed to build DeepStream pipeline")
        if not self._ds_pipeline.start():
            raise RuntimeError("Failed to start DeepStream pipeline")

        self._ds_thread = threading.Thread(
            target=self._ds_pipeline.run, name="deepstream", daemon=True
        )
        self._ds_thread.start()
        logger.info("DeepStream pipeline running in background thread")

    async def _event_dispatch_loop(self):
        """Consume DeepStream events from the queue and forward via WebSocket."""
        logger.info("Starting event dispatch loop (DeepStream mode)...")

        while self.running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                if self.monitor:
                    self.monitor.record_inference(event.get("inference_ms", 0))
                await self.ws_client.send_emotion_event(event)
            except Exception as e:
                logger.error("Error dispatching emotion event: %s", e)

    # ── Simulation mode ────────────────────────────────────────────────

    async def _simulated_emotion_loop(self):
        """Generate synthetic emotion events at ~30 FPS for dev/testing."""
        import random

        logger.info("Starting SIMULATED emotion loop (not real inference)...")

        frame_count = 0
        while self.running:
            try:
                emotion = random.choice(["happy", "sad", "neutral"])
                confidence = 0.80 + random.random() * 0.15
                inference_ms = 40.0 + random.random() * 20.0

                if self.monitor:
                    self.monitor.record_inference(inference_ms)

                event = {
                    "emotion": emotion,
                    "confidence": round(confidence, 4),
                    "inference_ms": round(inference_ms, 2),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "frame_number": frame_count,
                }
                await self.ws_client.send_emotion_event(event)
                frame_count += 1
                await asyncio.sleep(0.033)  # ~30 FPS

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in simulated emotion loop: %s", e)
                await asyncio.sleep(1)

    # ── Monitoring ────────────────────────────────────────────────────

    async def _monitoring_loop(self):
        """Periodic system stats and thermal throttle check."""
        while self.running:
            try:
                await asyncio.sleep(5)
                if self.monitor:
                    self.monitor.log_stats()
                    if self.monitor.check_thermal_throttling():
                        logger.warning("Thermal throttling detected!")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in monitoring loop: %s", e)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Reachy Emotion Detection Service")
    parser.add_argument("--config", required=True, help="DeepStream inference config file")
    parser.add_argument("--gateway", default="http://10.0.4.140:8000", help="Gateway URL")
    parser.add_argument("--device-id", default="reachy-mini-01", help="Device ID")
    parser.add_argument(
        "--mode",
        choices=["deepstream", "simulate"],
        default="deepstream",
        help="Run mode: 'deepstream' for real inference, 'simulate' for mock data",
    )
    args = parser.parse_args()

    service = EmotionDetectionService(
        deepstream_config=args.config,
        gateway_url=args.gateway,
        device_id=args.device_id,
        mode=args.mode,
    )

    def signal_handler(sig, _frame):
        logger.info("Received signal %s, shutting down...", sig)
        asyncio.create_task(service.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error("Service error: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
