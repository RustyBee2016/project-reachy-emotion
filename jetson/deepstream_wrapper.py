#!/usr/bin/env python3
"""
DeepStream Pipeline Wrapper for EmotionNet.

Manages DeepStream pipeline lifecycle and emotion event extraction.
Uses GstPad probes on the nvinfer src pad to read classification
metadata from each frame.
"""

import sys
import logging
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
import json

try:
    import gi
    gi.require_version("Gst", "1.0")
    from gi.repository import GLib, Gst
except ImportError:
    Gst = None  # type: ignore[assignment]
    GLib = None  # type: ignore[assignment]

try:
    import pyds  # DeepStream Python bindings
except ImportError:
    pyds = None  # type: ignore[assignment]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EMOTION_LABELS = ["happy", "sad", "neutral"]


class DeepStreamPipeline:
    """Wrapper for DeepStream emotion detection pipeline."""

    def __init__(
        self,
        config_file: str,
        on_emotion_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Initialize DeepStream pipeline.

        Args:
            config_file: Path to DeepStream app config (e.g. emotion_pipeline.txt)
            on_emotion_callback: Callback invoked with each emotion event dict
        """
        if Gst is None:
            raise RuntimeError(
                "GStreamer/gi not available. Install GStreamer and PyGObject."
            )

        self.config_file = config_file
        self.on_emotion_callback = on_emotion_callback

        Gst.init(None)

        # Pipeline components
        self.pipeline: Any = None
        self.loop: Any = None
        self.bus: Any = None

        # Performance tracking
        self.frame_count = 0
        self.inference_count = 0
        self.start_time: Optional[datetime] = None

        logger.info("DeepStream pipeline initialized with config: %s", config_file)

    def build_pipeline(self) -> bool:
        """Build GStreamer pipeline from a DeepStream app config file.

        The config_file is parsed by deepstream-app (or we construct
        the pipeline from the individual element configs referenced
        within it).

        Returns:
            True if pipeline was created successfully.
        """
        try:
            # Build pipeline from the DeepStream app config.
            # deepstream-app uses its own parser; here we use
            # Gst.parse_launch with the standard camera → nvinfer
            # → osd chain described in emotion_pipeline.txt.
            pipeline_str = (
                "v4l2src device=/dev/video0 "
                "! video/x-raw,width=1920,height=1080,framerate=30/1 "
                "! nvvideoconvert "
                "! video/x-raw(memory:NVMM),format=NV12 "
                "! m.sink_0 "
                "nvstreammux name=m batch-size=1 width=224 height=224 "
                "! nvinfer name=emotion_infer "
                f"  config-file-path={self.config_file} "
                "! nvvideoconvert "
                "! nvdsosd "
                "! fakesink sync=false"
            )
            self.pipeline = Gst.parse_launch(pipeline_str)

            if not self.pipeline:
                logger.error("Failed to create pipeline")
                return False

            # Attach probe on nvinfer src pad to read classification metadata.
            nvinfer = self.pipeline.get_by_name("emotion_infer")
            if nvinfer:
                src_pad = nvinfer.get_static_pad("src")
                if src_pad:
                    src_pad.add_probe(
                        Gst.PadProbeType.BUFFER, self._inference_probe_callback, 0
                    )
                    logger.info("Attached inference probe on nvinfer src pad")
                else:
                    logger.warning("Could not get src pad from nvinfer element")
            else:
                logger.warning("Could not find nvinfer element 'emotion_infer'")

            # Bus for EOS / error messages.
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            self.bus.connect("message", self._on_bus_message)

            logger.info("Pipeline built successfully")
            return True

        except Exception as e:
            logger.error("Failed to build pipeline: %s", e)
            return False

    # ── Inference probe ────────────────────────────────────────────────

    def _inference_probe_callback(self, pad, info, _user_data):
        """GstPad probe callback invoked after nvinfer processes a frame.

        Extracts classification metadata from the DeepStream batch
        metadata and fires on_emotion_callback for each detected object.
        """
        buf = info.get_buffer()
        if not buf:
            return Gst.PadProbeReturn.OK

        events = self._extract_emotion_metadata(buf)
        for event in events:
            self.inference_count += 1
            if self.on_emotion_callback:
                try:
                    self.on_emotion_callback(event)
                except Exception:
                    logger.exception("Error in emotion callback")

        self.frame_count += 1
        return Gst.PadProbeReturn.OK

    def _extract_emotion_metadata(self, buf) -> List[Dict[str, Any]]:
        """Extract emotion classification metadata from a GStreamer buffer.

        Uses pyds (DeepStream Python bindings) to walk the batch →
        frame → object → classifier metadata hierarchy.

        Args:
            buf: GStreamer buffer with NvDs batch metadata attached.

        Returns:
            List of emotion event dicts (one per detected face).
        """
        events: List[Dict[str, Any]] = []

        if pyds is None:
            logger.debug("pyds not available — returning empty events")
            return events

        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(buf))
        if batch_meta is None:
            return events

        frame_list = batch_meta.frame_meta_list
        while frame_list is not None:
            try:
                frame_meta = pyds.NvDsFrameMeta.cast(frame_list.data)
            except StopIteration:
                break

            obj_list = frame_meta.obj_meta_list
            while obj_list is not None:
                try:
                    obj_meta = pyds.NvDsObjectMeta.cast(obj_list.data)
                except StopIteration:
                    break

                # Walk classifier metadata attached by nvinfer.
                cls_list = obj_meta.classifier_meta_list
                while cls_list is not None:
                    try:
                        cls_meta = pyds.NvDsClassifierMeta.cast(cls_list.data)
                    except StopIteration:
                        break

                    label_list = cls_meta.label_info_list
                    while label_list is not None:
                        try:
                            label_info = pyds.NvDsLabelInfo.cast(label_list.data)
                        except StopIteration:
                            break

                        class_id = label_info.result_class_id
                        confidence = label_info.result_prob
                        emotion = (
                            EMOTION_LABELS[class_id]
                            if class_id < len(EMOTION_LABELS)
                            else "unknown"
                        )

                        inference_ms = (
                            frame_meta.ntp_timestamp / 1e6
                            if hasattr(frame_meta, "ntp_timestamp")
                            else 0.0
                        )

                        events.append(
                            {
                                "emotion": emotion,
                                "confidence": round(float(confidence), 4),
                                "inference_ms": round(inference_ms, 2),
                                "timestamp": datetime.utcnow().isoformat() + "Z",
                                "frame_number": self.frame_count,
                            }
                        )

                        try:
                            label_list = label_list.next
                        except StopIteration:
                            break

                    try:
                        cls_list = cls_list.next
                    except StopIteration:
                        break

                try:
                    obj_list = obj_list.next
                except StopIteration:
                    break

            try:
                frame_list = frame_list.next
            except StopIteration:
                break

        return events

    # ── Pipeline lifecycle ────────────────────────────────────────────

    def start(self) -> bool:
        """Start the pipeline.

        Returns:
            True if started successfully.
        """
        if not self.pipeline:
            logger.error("Pipeline not built")
            return False

        try:
            ret = self.pipeline.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                logger.error("Unable to set pipeline to PLAYING state")
                return False

            self.start_time = datetime.now()
            self.loop = GLib.MainLoop()
            logger.info("Pipeline started")
            return True

        except Exception as e:
            logger.error("Failed to start pipeline: %s", e)
            return False

    def run(self):
        """Run the main loop (blocking)."""
        if not self.loop:
            logger.error("Main loop not created")
            return

        try:
            logger.info("Running main loop...")
            self.loop.run()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.stop()

    def stop(self):
        """Stop the pipeline and log stats."""
        if self.pipeline:
            logger.info("Stopping pipeline...")
            self.pipeline.set_state(Gst.State.NULL)

        if self.loop and self.loop.is_running():
            self.loop.quit()

        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            fps = self.frame_count / duration if duration > 0 else 0
            logger.info(
                "Performance: %.2f FPS, %d inferences in %.1f s",
                fps,
                self.inference_count,
                duration,
            )

    # ── Bus messages ──────────────────────────────────────────────────

    def _on_bus_message(self, bus, message):
        """Handle GStreamer bus messages."""
        msg_type = message.type

        if msg_type == Gst.MessageType.EOS:
            logger.info("End of stream")
            if self.loop:
                self.loop.quit()
        elif msg_type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error("Pipeline error: %s, %s", err, debug)
            if self.loop:
                self.loop.quit()
        elif msg_type == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning("Pipeline warning: %s, %s", warn, debug)
        elif msg_type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, _pending = message.parse_state_changed()
                logger.info(
                    "Pipeline state: %s -> %s",
                    old_state.value_nick,
                    new_state.value_nick,
                )

        return True

    # ── Stats ─────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        duration = 0.0
        fps = 0.0

        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            fps = self.frame_count / duration if duration > 0 else 0

        return {
            "frame_count": self.frame_count,
            "inference_count": self.inference_count,
            "duration_sec": round(duration, 1),
            "fps": round(fps, 2),
            "running": self.pipeline is not None and self.loop is not None,
        }


def main():
    """Standalone test entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run DeepStream emotion detection")
    parser.add_argument("--config", required=True, help="DeepStream inference config")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    def on_emotion(event):
        print(f"Emotion detected: {json.dumps(event, indent=2)}")

    pipeline = DeepStreamPipeline(
        config_file=args.config,
        on_emotion_callback=on_emotion,
    )

    if not pipeline.build_pipeline():
        sys.exit(1)

    if not pipeline.start():
        sys.exit(1)

    try:
        pipeline.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        stats = pipeline.get_stats()
        print(f"\nFinal stats: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    main()
