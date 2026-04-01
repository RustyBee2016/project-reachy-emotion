#!/usr/bin/env python3
"""Lightweight HTTP health endpoint for Jetson emotion service.

Exposes ``GET /healthz`` on port 8090 so the deployment agent (n8n Agent 7)
can verify service liveness after deploying a new TensorRT engine.

Usage:
    Integrated into EmotionDetectionService — starts automatically.
    Standalone for testing::

        python health_server.py --port 8090
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from monitoring.system_monitor import JetsonMonitor
    from emotion_client import EmotionClient

try:
    from aiohttp import web
except ImportError:
    web = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

DEFAULT_PORT = 8090


class HealthServer:
    """Async HTTP health server backed by ``aiohttp``."""

    def __init__(
        self,
        *,
        port: int = DEFAULT_PORT,
        monitor: Optional["JetsonMonitor"] = None,
        ws_client: Optional["EmotionClient"] = None,
        deepstream_running_fn: Optional[callable] = None,
    ):
        if web is None:
            raise ImportError(
                "aiohttp is required for the health server. "
                "Install it with: pip install aiohttp>=3.9"
            )
        self.port = port
        self.monitor = monitor
        self.ws_client = ws_client
        self._ds_running_fn = deepstream_running_fn
        self._start_time = time.monotonic()
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None

    async def start(self) -> None:
        self._app = web.Application()
        self._app.router.add_get("/healthz", self._handle_healthz)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "0.0.0.0", self.port)
        await site.start()
        logger.info("Health server listening on port %d", self.port)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            logger.info("Health server stopped")

    async def _handle_healthz(self, request: web.Request) -> web.Response:
        body = self._build_status()
        status_code = 200 if body["status"] != "unhealthy" else 503
        return web.Response(
            body=json.dumps(body),
            content_type="application/json",
            status=status_code,
        )

    def _build_status(self) -> Dict[str, Any]:
        uptime_s = round(time.monotonic() - self._start_time, 1)
        now = datetime.now(timezone.utc).isoformat()

        ds_running = bool(self._ds_running_fn and self._ds_running_fn())
        ws_connected = bool(self.ws_client and self.ws_client.connected)

        perf: Dict[str, Any] = {}
        gpu_temp: Optional[float] = None
        gpu_memory_mb: Optional[float] = None
        last_inference_ts: Optional[str] = None

        if self.monitor:
            perf = self.monitor.get_performance_stats()
            gpu = self.monitor.get_gpu_stats()
            gpu_temp = gpu.get("temp_gpu")
            gpu_memory_mb = gpu.get("ram_used_mb")
            if perf.get("frame_count", 0) > 0:
                last_inference_ts = now  # approximate

        # Determine overall status
        status = "healthy"
        if not ws_connected:
            status = "degraded"
        if not ds_running and not ws_connected:
            status = "unhealthy"

        return {
            "status": status,
            "timestamp": now,
            "deepstream_running": ds_running,
            "websocket_connected": ws_connected,
            "last_inference_ts": last_inference_ts,
            "gpu_temp_c": gpu_temp,
            "gpu_memory_mb": gpu_memory_mb,
            "uptime_s": uptime_s,
            "inference_fps": perf.get("fps", 0.0),
            "latency_p50_ms": perf.get("latency_p50_ms"),
            "latency_p95_ms": perf.get("latency_p95_ms"),
        }


async def _standalone_main():
    """Run the health server standalone (for testing)."""
    import argparse

    parser = argparse.ArgumentParser(description="Jetson Health Server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    server = HealthServer(port=args.port)
    await server.start()
    logger.info("Health server running standalone (ctrl+c to stop)")
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_standalone_main())
