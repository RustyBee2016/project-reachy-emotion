#!/usr/bin/env python3
"""
DeepStream Pipeline Wrapper for EmotionNet
Manages DeepStream pipeline lifecycle and emotion event extraction.
"""

import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeepStreamPipeline:
    """Wrapper for DeepStream emotion detection pipeline."""
    
    def __init__(
        self,
        config_file: str,
        on_emotion_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Initialize DeepStream pipeline.
        
        Args:
            config_file: Path to DeepStream config file
            on_emotion_callback: Callback for emotion events
        """
        self.config_file = config_file
        self.on_emotion_callback = on_emotion_callback
        
        # Initialize GStreamer
        Gst.init(None)
        
        # Pipeline components
        self.pipeline = None
        self.loop = None
        self.bus = None
        
        # Performance tracking
        self.frame_count = 0
        self.inference_count = 0
        self.start_time = None
        
        logger.info(f"DeepStream pipeline initialized with config: {config_file}")
    
    def build_pipeline(self) -> bool:
        """
        Build GStreamer pipeline from config.
        
        Returns:
            True if successful
        """
        try:
            # Create pipeline using nvinfer config
            self.pipeline = Gst.parse_launch(
                f"filesrc location={self.config_file} ! "
                "nvstreammux ! nvinfer ! nvvideoconvert ! "
                "nvdsosd ! nvegltransform ! nveglglessink"
            )
            
            if not self.pipeline:
                logger.error("Failed to create pipeline")
                return False
            
            # Get bus for messages
            self.bus = self.pipeline.get_bus()
            self.bus.add_signal_watch()
            self.bus.connect("message", self._on_bus_message)
            
            logger.info("Pipeline built successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to build pipeline: {e}")
            return False
    
    def start(self) -> bool:
        """
        Start the pipeline.
        
        Returns:
            True if started successfully
        """
        if not self.pipeline:
            logger.error("Pipeline not built")
            return False
        
        try:
            # Set pipeline to PLAYING state
            ret = self.pipeline.set_state(Gst.State.PLAYING)
            
            if ret == Gst.StateChangeReturn.FAILURE:
                logger.error("Unable to set pipeline to PLAYING state")
                return False
            
            self.start_time = datetime.now()
            
            # Create main loop
            self.loop = GLib.MainLoop()
            
            logger.info("Pipeline started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start pipeline: {e}")
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
        """Stop the pipeline."""
        if self.pipeline:
            logger.info("Stopping pipeline...")
            self.pipeline.set_state(Gst.State.NULL)
        
        if self.loop:
            self.loop.quit()
        
        # Log performance stats
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            fps = self.frame_count / duration if duration > 0 else 0
            logger.info(f"Performance: {fps:.2f} FPS, {self.inference_count} inferences")
    
    def _on_bus_message(self, bus, message):
        """
        Handle GStreamer bus messages.
        
        Args:
            bus: GStreamer bus
            message: Bus message
        """
        msg_type = message.type
        
        if msg_type == Gst.MessageType.EOS:
            logger.info("End of stream")
            if self.loop:
                self.loop.quit()
        
        elif msg_type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"Pipeline error: {err}, {debug}")
            if self.loop:
                self.loop.quit()
        
        elif msg_type == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"Pipeline warning: {warn}, {debug}")
        
        elif msg_type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending = message.parse_state_changed()
                logger.info(f"Pipeline state: {old_state.value_nick} -> {new_state.value_nick}")
        
        return True
    
    def _extract_emotion_metadata(self, buffer) -> Optional[Dict[str, Any]]:
        """
        Extract emotion metadata from buffer.
        
        Args:
            buffer: GStreamer buffer with metadata
        
        Returns:
            Emotion event dictionary or None
        """
        try:
            # This is a placeholder - actual implementation would use
            # nvds_get_obj_meta_from_frame_meta() and similar DeepStream APIs
            
            # For now, return mock data
            emotion_event = {
                'emotion': 'happy',
                'confidence': 0.87,
                'inference_ms': 45.2,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'frame_number': self.frame_count
            }
            
            return emotion_event
            
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics.
        
        Returns:
            Statistics dictionary
        """
        duration = 0
        fps = 0
        
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            fps = self.frame_count / duration if duration > 0 else 0
        
        return {
            'frame_count': self.frame_count,
            'inference_count': self.inference_count,
            'duration_sec': duration,
            'fps': round(fps, 2),
            'running': self.pipeline is not None and self.loop is not None
        }


def main():
    """Main entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run DeepStream emotion detection')
    parser.add_argument('--config', required=True, help='DeepStream config file')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create pipeline
    def on_emotion(event):
        print(f"Emotion detected: {json.dumps(event, indent=2)}")
    
    pipeline = DeepStreamPipeline(
        config_file=args.config,
        on_emotion_callback=on_emotion
    )
    
    # Build and start
    if not pipeline.build_pipeline():
        sys.exit(1)
    
    if not pipeline.start():
        sys.exit(1)
    
    # Run
    try:
        pipeline.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        stats = pipeline.get_stats()
        print(f"\nFinal stats: {json.dumps(stats, indent=2)}")


if __name__ == '__main__':
    main()
