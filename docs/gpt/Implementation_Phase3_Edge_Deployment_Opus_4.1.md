# Phase 3: Edge Deployment Implementation
**Weeks 6-7 | Jetson Xavier NX Deployment**

## Overview
Configure DeepStream pipeline, optimize TensorRT inference, implement WebSocket communication, deploy to Jetson.

## Components to Implement

### 3.1 DeepStream Pipeline (`jetson/deepstream/`)
- `emotion_pipeline.txt` - Main pipeline configuration
- `emotion_inference.txt` - nvinfer plugin config
- `emotion_labels.txt` - Class label mapping
- Camera input configuration (V4L2)
- Preprocessing pipeline
- Post-processing logic

### 3.2 TensorRT Inference (`jetson/inference/`)
- Engine loading and warmup
- Batch processing (if needed)
- FP16 precision optimization
- INT8 calibration (optional)
- Memory management
- Performance monitoring

### 3.3 WebSocket Client (`jetson/emotion_client.py`)
- Connection to Ubuntu 2 gateway
- Emotion event streaming
- Device registration
- Heartbeat mechanism
- Cue reception (gestures/TTS)
- Automatic reconnection

### 3.4 Video Processing (`jetson/video_processor.py`)
- Frame extraction
- Face detection (optional)
- ROI extraction
- Sliding window implementation
- Temporal smoothing
- Confidence thresholding

### 3.5 System Service (`jetson/systemd/`)
- `reachy-emotion.service` - Main service
- Auto-start on boot
- Restart on failure
- Log rotation
- Resource limits
- Health monitoring

### 3.6 Edge Monitoring (`jetson/monitoring/`)
- GPU utilization tracking
- Temperature monitoring
- FPS measurement
- Inference latency logging
- Memory usage tracking
- Network bandwidth monitoring

## DeepStream Pipeline Architecture

### Pipeline Flow
```
Camera → nvstreammux → nvinfer (TensorRT) → nvtracker → nvdsanalytics → nvmsgconv → nvmsgbroker
                           ↓
                      WebSocket Client → Ubuntu 2 Gateway
```

### Key Components
1. **Source**: V4L2 camera (1920x1080@30fps)
2. **Streammux**: Batch frames (batch-size=1 for real-time)
3. **Primary GIE**: EmotionNet TensorRT engine
4. **Tracker**: Disabled (no face tracking needed)
5. **Analytics**: Emotion statistics
6. **Message Converter**: JSON formatting
7. **Message Broker**: WebSocket transmission

## Performance Optimization

### TensorRT Optimization
- Use FP16 precision (2x speedup, minimal accuracy loss)
- Dynamic batching if multiple streams
- Optimize workspace size (2GB)
- Use DLA if available on platform

### Memory Management
- Pre-allocate buffers
- Use zero-copy where possible
- Implement buffer pooling
- Clear cache periodically

### Power Management
- Set Jetson to MAX-N mode for testing
- Use 15W mode for production
- Monitor thermal throttling
- Implement dynamic frequency scaling

## Testing Strategy

### Unit Tests
```python
# tests/test_inference.py
- test_engine_loading
- test_preprocessing
- test_inference_accuracy
- test_postprocessing

# tests/test_websocket.py
- test_connection_establishment
- test_event_transmission
- test_reconnection_logic
- test_heartbeat
```

### Performance Tests
```python
# tests/test_performance.py
- test_inference_latency (target: <100ms)
- test_throughput (target: 30 FPS)
- test_memory_usage (target: <1GB)
- test_power_consumption
```

### Integration Tests
```python
# tests/test_edge_integration.py
- test_camera_to_inference_pipeline
- test_websocket_delivery
- test_24_hour_stability
- test_thermal_behavior
```

## Deployment Process

1. **Prepare Jetson**
   - Flash JetPack 5.1
   - Install DeepStream 6.2
   - Configure networking
   - Mount NFS storage

2. **Transfer Models**
   - Copy TensorRT engine
   - Copy configuration files
   - Verify checksums

3. **Install Services**
   - Deploy systemd services
   - Configure auto-start
   - Setup logging

4. **Validation**
   - Run inference tests
   - Check WebSocket connectivity
   - Monitor performance metrics
   - Verify emotion detection accuracy

## Success Criteria
- [ ] DeepStream pipeline runs at 30 FPS
- [ ] Inference latency <100ms (p95)
- [ ] WebSocket maintains stable connection
- [ ] System runs 24 hours without crash
- [ ] GPU temperature stays <75°C
- [ ] Emotion accuracy >85% on test set
