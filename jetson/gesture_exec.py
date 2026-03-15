#!/usr/bin/env python3
"""
gesture_exec.py — Gesture Execution CLI for Reachy Mini

Called by the Agent 10 n8n workflow via SSH:
    python3 /opt/reachy/gesture_exec.py \
        --gesture EMPATHY \
        --tier 3 \
        --amplitude 0.50 \
        --speed slow \
        --emotion sad \
        --ekman-class sad \
        --correlation-id abc-123

Deploy this file to /opt/reachy/gesture_exec.py on the Jetson NX.

Exit codes:
    0  — gesture executed or abstained cleanly
    1  — unknown gesture type
    2  — Reachy connection failed
    3  — unexpected error
"""

import argparse
import asyncio
import json
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("gesture_exec")

# Allow running from the repo root on the Jetson
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# Tier → representative confidence midpoints for modulation
_TIER_CONFIDENCE = {
    1: 0.20,  # Abstain (caller should not reach here, but handled gracefully)
    2: 0.50,  # Minimal
    3: 0.67,  # Subtle
    4: 0.82,  # Moderate
    5: 0.95,  # Full
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute a modulated gesture on Reachy Mini"
    )
    parser.add_argument(
        "--gesture",
        required=True,
        help="GestureType name, e.g. EMPATHY, NOD, CELEBRATE, WAVE",
    )
    parser.add_argument(
        "--tier",
        type=int,
        required=True,
        choices=[1, 2, 3, 4, 5],
        help="Expressiveness tier (1=abstain, 5=full)",
    )
    parser.add_argument(
        "--amplitude",
        type=float,
        default=1.0,
        help="Pre-computed amplitude multiplier (0.0–1.0), overrides tier default",
    )
    parser.add_argument(
        "--speed",
        default="normal",
        choices=["none", "slow", "normal", "fast"],
        help="Speed descriptor from Agent 10",
    )
    parser.add_argument("--emotion", default="neutral", help="Source 3-class emotion label")
    parser.add_argument(
        "--ekman-class",
        default=None,
        help="Ekman 8-class label (may differ from source emotion after phase1_to_ekman mapping)",
    )
    parser.add_argument(
        "--correlation-id",
        default="",
        help="Correlation ID for distributed tracing across n8n → pipeline → Jetson",
    )
    parser.add_argument(
        "--sim",
        action="store_true",
        help="Simulation mode: compute modulation but do not call Reachy SDK",
    )
    return parser.parse_args()


async def run(args: argparse.Namespace) -> None:
    try:
        from apps.reachy.gestures.gesture_definitions import GESTURE_LIBRARY, GestureType
        from apps.reachy.gestures.gesture_modulator import GestureModulator
        from apps.reachy.gestures.gesture_controller import GestureController
        from apps.reachy.config import ReachyConfig
    except ImportError as exc:
        logger.error(f"Import error — is the repo root in PYTHONPATH? {exc}")
        sys.exit(3)

    correlation = args.correlation_id or "—"

    # Tier 1 is an abstain signal — nothing to execute
    if args.tier == 1:
        _emit({"status": "abstained", "tier": 1, "gesture": args.gesture, "correlation_id": correlation})
        sys.exit(0)

    # Resolve gesture type from library
    try:
        gesture_type = GestureType[args.gesture.upper()]
    except KeyError:
        logger.error(f"Unknown GestureType: '{args.gesture}'")
        _emit({"status": "error", "reason": f"unknown_gesture:{args.gesture}", "correlation_id": correlation})
        sys.exit(1)

    base_gesture = GESTURE_LIBRARY.get(gesture_type)
    if base_gesture is None:
        logger.error(f"GestureType '{args.gesture}' not in GESTURE_LIBRARY")
        _emit({"status": "error", "reason": "gesture_not_in_library", "correlation_id": correlation})
        sys.exit(1)

    # Modulate gesture using tier-derived confidence
    confidence = _TIER_CONFIDENCE.get(args.tier, 0.67)
    modulator = GestureModulator()
    modulated = modulator.modulate(base_gesture, confidence)
    expressiveness = modulator.last_expressiveness.value if modulator.last_expressiveness else "unknown"

    if modulated is None:
        _emit({"status": "abstained", "reason": "modulator_abstain", "tier": args.tier, "correlation_id": correlation})
        sys.exit(0)

    sim_mode = args.sim or os.getenv("REACHY_SIM_MODE", "0") == "1"

    if sim_mode:
        _emit({
            "status": "simulated",
            "gesture": modulated.name,
            "tier": args.tier,
            "expressiveness": expressiveness,
            "duration_s": round(modulated.total_duration, 2),
            "emotion": args.emotion,
            "ekman_class": args.ekman_class or args.emotion,
            "correlation_id": correlation,
        })
        sys.exit(0)

    # Live execution via Reachy SDK
    reachy_host = os.getenv("REACHY_HOST", "localhost")
    reachy_port = int(os.getenv("REACHY_PORT", "50055"))
    config = ReachyConfig(host=reachy_host, port=reachy_port, simulation_mode=False)
    controller = GestureController(config)

    connected = await controller.connect()
    if not connected:
        logger.error(f"Failed to connect to Reachy at {reachy_host}:{reachy_port}")
        _emit({
            "status": "error",
            "reason": f"reachy_connect_failed:{reachy_host}:{reachy_port}",
            "correlation_id": correlation,
        })
        sys.exit(2)

    try:
        gesture_result = await controller.execute_gesture(modulated)
        success = getattr(gesture_result, "success", True)
        _emit({
            "status": "executed",
            "gesture": modulated.name,
            "tier": args.tier,
            "expressiveness": expressiveness,
            "duration_s": round(modulated.total_duration, 2),
            "success": success,
            "emotion": args.emotion,
            "ekman_class": args.ekman_class or args.emotion,
            "correlation_id": correlation,
        })
        sys.exit(0)
    except Exception as exc:
        logger.error(f"Gesture execution error: {exc}")
        _emit({"status": "error", "reason": str(exc), "correlation_id": correlation})
        sys.exit(3)
    finally:
        await controller.disconnect()


def _emit(payload: dict) -> None:
    """Write JSON result to stdout for n8n SSH node to capture."""
    print(json.dumps(payload), flush=True)


if __name__ == "__main__":
    asyncio.run(run(_parse_args()))
