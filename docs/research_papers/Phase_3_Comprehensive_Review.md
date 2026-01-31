# Phase 3 Comprehensive Review: Edge Deployment and Real-Time Inference

**Deploying Emotion Recognition to Jetson Xavier NX with DeepStream and TensorRT**

---

## Abstract

This paper provides a detailed examination of Phase 3 of Project Reachy, focusing on the deployment of the trained EfficientNet-B0 emotion classifier to the Jetson Xavier NX edge device for real-time inference. Phase 3 encompasses: (1) **TensorRT Engine Conversion**—optimizing the trained ONNX model for edge inference using FP16 precision, (2) **DeepStream Pipeline Configuration**—integrating the TensorRT engine into NVIDIA's video analytics framework for efficient streaming inference, (3) **WebSocket Communication**—establishing bidirectional communication between the Jetson and the Ubuntu 2 gateway for emotion events and gesture cues, and (4) **Quality Gate Validation**—ensuring the deployed system meets latency (p50 ≤ 120 ms), memory (≤ 2.5 GB), and accuracy (F1 ≥ 0.80) requirements. Through annotated code examples and deployment workflows, we explain how the emotional intelligence developed in Phase 2 is delivered to end users through optimized edge inference.

**Keywords:** TensorRT, DeepStream, Jetson Xavier NX, edge inference, model deployment, WebSocket, real-time systems

---

## 1. Introduction

### 1.1 From Training to Production

Phases 1 and 2 established the foundation for emotion recognition: a fine-tuned EfficientNet-B0 classifier with calibrated confidence scores, degree-modulated gesture responses, and emotion-conditioned LLM interactions. However, these capabilities exist only on the training server (Ubuntu 1) and gateway (Ubuntu 2).

**Phase 3 bridges the gap** between trained model and deployed robot by:
1. Converting the model to an optimized TensorRT engine
2. Integrating inference into a DeepStream video pipeline
3. Establishing real-time communication with the gateway
4. Validating production-ready performance

### 1.2 Edge Deployment Challenges

Deploying neural networks to edge devices introduces constraints absent during training:

| Challenge | Impact | Mitigation |
|-----------|--------|------------|
| **Limited Memory** | Jetson Xavier NX has 16 GB shared CPU/GPU RAM | FP16 quantization, batch size 1 |
| **Thermal Throttling** | Sustained inference heats the device | EfficientNet-B0's 3× headroom |
| **Latency Requirements** | Real-time HRI demands p50 ≤ 120 ms | TensorRT optimization, pipelined inference |
| **Network Reliability** | LAN may experience transient failures | Auto-reconnection, heartbeat monitoring |

### 1.3 Phase 3 Objectives

1. **TensorRT Conversion**: Export ONNX → TensorRT engine with FP16 precision
2. **DeepStream Integration**: Configure `nvinfer` plugin for streaming inference
3. **WebSocket Client**: Implement robust Jetson ↔ Gateway communication
4. **Gate B Validation**: Verify latency, memory, and accuracy thresholds
5. **Staged Rollout**: Shadow → Canary → Production deployment

---

## 2. TensorRT Engine Conversion

### 2.1 Why TensorRT?

TensorRT is NVIDIA's inference optimization library that transforms trained models into highly efficient engines through:
- **Layer fusion**: Combining multiple operations into single kernels
- **Precision calibration**: FP32 → FP16/INT8 with minimal accuracy loss
- **Kernel auto-tuning**: Selecting optimal implementations for target hardware

### 2.2 Conversion Pipeline

The conversion occurs on the Jetson device (to ensure compatibility):

```
Ubuntu 1 (Training)          Jetson Xavier NX
┌─────────────────┐          ┌─────────────────┐
│ PyTorch Model   │          │                 │
│ (.pth weights)  │          │                 │
└────────┬────────┘          │                 │
         │ export            │                 │
         ▼                   │                 │
┌─────────────────┐   SCP    │                 │
│ ONNX Model      │ ────────►│ ONNX Model      │
│ (.onnx)         │          │                 │
└─────────────────┘          └────────┬────────┘
                                      │ trtexec
                                      ▼
                             ┌─────────────────┐
                             │ TensorRT Engine │
                             │ (.engine FP16)  │
                             └─────────────────┘
```

### 2.3 Implementation: ONNX Export

The training pipeline exports to ONNX after Gate A validation:

```python
# trainer/fer_finetune/export.py

def export_to_onnx(
    model: EmotionClassifier,
    output_path: Path,
    input_shape: Tuple[int, int, int, int] = (1, 3, 224, 224),
    opset_version: int = 17,
) -> Path:
    """
    Export trained model to ONNX format.
    
    Args:
        model: Trained EmotionClassifier
        output_path: Directory for output files
        input_shape: (batch, channels, height, width)
        opset_version: ONNX opset version
        
    Returns:
        Path to exported ONNX file
    """
    model.eval()
    
    # Create dummy input
    dummy_input = torch.randn(*input_shape, device=next(model.parameters()).device)
    
    onnx_path = output_path / "emotion_classifier.onnx"
    
    # Export with dynamic batch size
    torch.onnx.export(
        model,
        dummy_input,
        onnx_path,
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['logits'],
        dynamic_axes={
            'input': {0: 'batch_size'},
            'logits': {0: 'batch_size'}
        }
    )
    
    # Verify export
    import onnx
    onnx_model = onnx.load(onnx_path)
    onnx.checker.check_model(onnx_model)
    
    logger.info(f"ONNX model exported to: {onnx_path}")
    return onnx_path
```

### 2.4 Implementation: TensorRT Conversion

On the Jetson, `trtexec` converts ONNX to an optimized engine:

```bash
# jetson/deploy.sh (excerpt)

# Convert ONNX to TensorRT with FP16 precision
trtexec \
    --onnx=/opt/reachy/models/emotion_classifier.onnx \
    --saveEngine=/opt/reachy/engines/emotionnet_fp16.engine \
    --fp16 \
    --workspace=2048 \
    --minShapes=input:1x3x224x224 \
    --optShapes=input:1x3x224x224 \
    --maxShapes=input:4x3x224x224 \
    --verbose

# Verify engine
if [ ! -f /opt/reachy/engines/emotionnet_fp16.engine ]; then
    echo "ERROR: TensorRT conversion failed"
    exit 1
fi

echo "TensorRT engine created successfully"
```

**Key Parameters:**
- `--fp16`: Enable FP16 precision for 2× speedup with minimal accuracy loss
- `--workspace=2048`: 2 GB workspace for optimization algorithms
- `--optShapes`: Optimize for single-frame inference (batch=1)

---

## 3. DeepStream Pipeline Configuration

### 3.1 DeepStream Architecture

DeepStream is NVIDIA's streaming analytics framework built on GStreamer:

```
┌─────────────────────────────────────────────────────────────────────┐
│                       DeepStream Pipeline                            │
│                                                                      │
│  ┌─────────┐    ┌────────────┐    ┌─────────┐    ┌────────────────┐ │
│  │ Camera  │───►│ nvstreammux│───►│ nvinfer │───►│ Application    │ │
│  │ (V4L2)  │    │ (batching) │    │ (TRT)   │    │ (Python/C++)   │ │
│  └─────────┘    └────────────┘    └─────────┘    └────────────────┘ │
│                                         │                            │
│                                         ▼                            │
│                                   Emotion Event                      │
│                                   {emotion, confidence}              │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 nvinfer Configuration

The `nvinfer` plugin loads the TensorRT engine and performs inference:

```ini
# jetson/deepstream/emotion_inference.txt

[property]
gpu-id=0
batch-size=1
network-mode=2                              # FP16
model-engine-file=../engines/emotionnet_fp16.engine
labelfile-path=emotion_labels.txt
num-detected-classes=2
interval=0                                  # Infer every frame
gie-unique-id=1
process-mode=1                              # Primary detector
infer-dims=3;224;224                        # CHW format
output-blob-names=dense_2/Softmax           # Softmax output layer
output-tensor-meta=1                        # Attach tensor metadata
workspace-size=2048

# Normalization (ImageNet stats)
offsets=123.675;116.28;103.53
net-scale-factor=0.0171247538316637

[class-attrs-all]
pre-cluster-threshold=0.5                   # Confidence threshold
topk=1                                      # Return top prediction

[class-attrs-0]
threshold=0.5                               # Happy threshold

[class-attrs-1]
threshold=0.5                               # Sad threshold
```

### 3.3 Pipeline Wrapper

The Python wrapper manages the DeepStream pipeline lifecycle:

```python
# jetson/deepstream_wrapper.py

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
        
        # Performance tracking
        self.frame_count = 0
        self.inference_count = 0
        self.start_time = None
    
    def build_pipeline(self) -> bool:
        """Build GStreamer pipeline from config."""
        try:
            self.pipeline = Gst.parse_launch(
                f"v4l2src device=/dev/video0 ! "
                f"video/x-raw,width=640,height=480,framerate=30/1 ! "
                f"nvvideoconvert ! "
                f"video/x-raw(memory:NVMM),format=NV12 ! "
                f"nvstreammux name=mux batch-size=1 width=224 height=224 ! "
                f"nvinfer config-file-path={self.config_file} ! "
                f"fakesink"  # Output handled via probe
            )
            
            # Attach probe to extract inference results
            nvinfer = self.pipeline.get_by_name("nvinfer0")
            if nvinfer:
                srcpad = nvinfer.get_static_pad("src")
                srcpad.add_probe(Gst.PadProbeType.BUFFER, self._inference_probe)
            
            return True
        except Exception as e:
            logger.error(f"Failed to build pipeline: {e}")
            return False
    
    def _inference_probe(self, pad, info):
        """Extract emotion predictions from inference buffer."""
        buffer = info.get_buffer()
        
        # Extract metadata using pyds (DeepStream Python bindings)
        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(buffer))
        
        for frame_meta in pyds.nvds_frame_meta_list(batch_meta):
            for obj_meta in pyds.nvds_obj_meta_list(frame_meta):
                class_id = obj_meta.class_id
                confidence = obj_meta.confidence
                
                emotion = "happy" if class_id == 0 else "sad"
                
                # Create emotion event
                event = {
                    'emotion': emotion,
                    'confidence': confidence,
                    'inference_ms': self._last_inference_ms,
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'frame_number': self.frame_count
                }
                
                if self.on_emotion_callback:
                    self.on_emotion_callback(event)
        
        self.frame_count += 1
        return Gst.PadProbeReturn.OK
```

---

## 4. WebSocket Communication

### 4.1 Communication Architecture

The Jetson communicates with Ubuntu 2 via WebSocket for bidirectional messaging:

```
┌──────────────────┐                    ┌──────────────────┐
│  Jetson NX       │                    │  Ubuntu 2        │
│                  │                    │  (Gateway)       │
│  ┌────────────┐  │    WebSocket       │  ┌────────────┐  │
│  │ Emotion    │  │ ─────────────────► │  │ FastAPI    │  │
│  │ Client     │  │    emotion_event   │  │ WebSocket  │  │
│  │            │  │ ◄───────────────── │  │ Server     │  │
│  │            │  │    gesture_cue     │  │            │  │
│  └────────────┘  │                    │  └────────────┘  │
└──────────────────┘                    └──────────────────┘
```

### 4.2 Emotion Client Implementation

```python
# jetson/emotion_client.py

class EmotionClient:
    """WebSocket client for streaming emotion events from Jetson."""
    
    def __init__(
        self,
        gateway_url: str,
        device_id: str,
        heartbeat_interval: int = 30,
        reconnect_attempts: int = 0  # 0 = infinite
    ):
        self.gateway_url = gateway_url
        self.device_id = device_id
        
        # Socket.IO client with auto-reconnection
        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=reconnect_attempts,
            reconnection_delay=1,
            reconnection_delay_max=30
        )
        
        # Metrics
        self.events_sent = 0
        self.cues_received = 0
        self.gestures_executed = 0
        
        # Cue callbacks
        self._gesture_callback: Optional[Callable[[GestureCue], Any]] = None
        
        self._register_handlers()
    
    async def send_emotion_event(self, emotion_data: Dict[str, Any]):
        """
        Send emotion detection event to gateway.
        
        Args:
            emotion_data: Emotion event with keys:
                - emotion: str (emotion label)
                - confidence: float (0-1)
                - inference_ms: float
                - timestamp: str (ISO format)
        """
        if not self.connected:
            logger.warning("Not connected, cannot send event")
            return
        
        event = {
            'device_id': self.device_id,
            **emotion_data
        }
        
        await self.sio.emit('emotion_event', event)
        self.events_sent += 1
```

### 4.3 Emotion Event Schema

```json
{
  "device_id": "reachy-mini-01",
  "ts": "2026-01-31T14:22:33Z",
  "emotion": "happy",
  "confidence": 0.87,
  "inference_ms": 42,
  "window": {
    "fps": 30,
    "size_s": 1.2,
    "hop_s": 0.5
  },
  "meta": {
    "model_version": "efficientnet-b0-hsemotion-v1.0",
    "gpu_temp": 52.3
  }
}
```

### 4.4 Gesture Cue Handling

The Jetson receives gesture cues from the gateway and dispatches them to the robot:

```python
# jetson/emotion_client.py (continued)

@dataclass
class GestureCue:
    """Gesture cue received from gateway."""
    gesture_type: str
    priority: int = 1
    duration: Optional[float] = None
    parameters: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None


async def _handle_cue(self, cue_data: Dict[str, Any]) -> None:
    """Handle a gesture cue from the gateway."""
    cue_type = cue_data.get("type", "").lower()
    
    if cue_type == "gesture":
        gesture_cue = GestureCue(
            gesture_type=cue_data.get("gesture_type", ""),
            priority=cue_data.get("priority", 1),
            parameters=cue_data.get("parameters"),
            correlation_id=cue_data.get("correlation_id")
        )
        
        if self._gesture_callback:
            result = self._gesture_callback(gesture_cue)
            if asyncio.iscoroutine(result):
                await result
            self.gestures_executed += 1
            
            # Send acknowledgment
            await self.sio.emit('cue_ack', {
                'correlation_id': gesture_cue.correlation_id,
                'status': 'executed'
            })
```

---

## 5. Quality Gate Validation

### 5.1 Gate B: Shadow Mode Validation

Before production deployment, the system runs in shadow mode alongside the existing (or mock) system:

| Metric | Threshold | Measurement Method |
|--------|-----------|-------------------|
| **Latency p50** | ≤ 120 ms | End-to-end: frame capture → event sent |
| **Latency p95** | ≤ 250 ms | 95th percentile over 1-hour window |
| **GPU Memory** | ≤ 2.5 GB | `nvidia-smi` during sustained inference |
| **Macro F1** | ≥ 0.80 | Validation against human labels |
| **Throughput** | ≥ 20 FPS | Sustained frames per second |

### 5.2 EfficientNet-B0 Performance Profile

The model selection (EfficientNet-B0 vs ResNet-50) provides substantial margin:

| Metric | EfficientNet-B0 | Gate B Threshold | Margin |
|--------|-----------------|------------------|--------|
| Inference Latency | ~40 ms | ≤ 120 ms | **3× headroom** |
| GPU Memory | ~0.8 GB | ≤ 2.5 GB | **3× headroom** |
| GPU Utilization | ~30% | N/A | Allows gesture processing |

This margin ensures thermal stability and accommodates future features (gesture planning, multi-modal fusion).

### 5.3 Gate C: Limited User Rollout

After shadow validation, limited user testing validates real-world performance:

| Metric | Threshold | Measurement |
|--------|-----------|-------------|
| **End-to-End Latency** | ≤ 300 ms | User-perceived response time |
| **Abstention Rate** | ≤ 20% | Percentage of low-confidence predictions |
| **User Complaints** | < 1% | Negative feedback per session |

---

## 6. Deployment Workflow

### 6.1 Staged Rollout

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Shadow    │────►│   Canary    │────►│  Production │
│   (0%)      │     │   (10%)     │     │   (100%)    │
└─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │
     ▼                    ▼                    ▼
 Validation           A/B Testing         Full Rollout
 (Gate B)             (Gate C)            (Monitoring)
```

### 6.2 Deployment Script

```bash
#!/bin/bash
# jetson/deploy.sh

set -e

ENGINE_PATH="/opt/reachy/engines"
MODEL_PATH="/opt/reachy/models"
BACKUP_PATH="/opt/reachy/backup"

# 1. Backup current engine
echo "Backing up current engine..."
mkdir -p $BACKUP_PATH
cp $ENGINE_PATH/emotionnet_fp16.engine $BACKUP_PATH/emotionnet_fp16.engine.bak 2>/dev/null || true

# 2. Transfer new ONNX model from Ubuntu 1
echo "Transferring model..."
scp ubuntu1@10.0.4.130:/media/project_data/ml_models/emotion_classifier.onnx $MODEL_PATH/

# 3. Convert to TensorRT
echo "Converting to TensorRT..."
trtexec \
    --onnx=$MODEL_PATH/emotion_classifier.onnx \
    --saveEngine=$ENGINE_PATH/emotionnet_fp16.engine \
    --fp16 \
    --workspace=2048

# 4. Verify conversion
if [ ! -f $ENGINE_PATH/emotionnet_fp16.engine ]; then
    echo "ERROR: TensorRT conversion failed, rolling back..."
    cp $BACKUP_PATH/emotionnet_fp16.engine.bak $ENGINE_PATH/emotionnet_fp16.engine
    exit 1
fi

# 5. Update DeepStream config
sed -i "s|model-engine-file=.*|model-engine-file=$ENGINE_PATH/emotionnet_fp16.engine|" \
    /opt/reachy/deepstream/emotion_inference.txt

# 6. Restart service
echo "Restarting emotion service..."
sudo systemctl restart reachy-emotion

# 7. Verify service health
sleep 5
if systemctl is-active --quiet reachy-emotion; then
    echo "Deployment successful!"
else
    echo "ERROR: Service failed to start, rolling back..."
    cp $BACKUP_PATH/emotionnet_fp16.engine.bak $ENGINE_PATH/emotionnet_fp16.engine
    sudo systemctl restart reachy-emotion
    exit 1
fi
```

### 6.3 Rollback Procedure

If Gate B or C fails, automatic rollback restores the previous engine:

```bash
# Rollback to previous engine
cp /opt/reachy/backup/emotionnet_fp16.engine.bak /opt/reachy/engines/emotionnet_fp16.engine
sudo systemctl restart reachy-emotion

# Notify deployment agent
curl -X POST http://10.0.4.140:8000/api/deployment/rollback \
    -H "Content-Type: application/json" \
    -d '{"device_id": "reachy-mini-01", "reason": "Gate B latency exceeded"}'
```

---

## 7. Monitoring and Observability

### 7.1 System Metrics

The Jetson exposes metrics for the Observability Agent:

```python
# jetson/monitoring/system_monitor.py

def collect_metrics() -> Dict[str, Any]:
    """Collect system metrics for observability."""
    import pynvml
    
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    
    return {
        'gpu_utilization': pynvml.nvmlDeviceGetUtilizationRates(handle).gpu,
        'gpu_memory_used_mb': pynvml.nvmlDeviceGetMemoryInfo(handle).used / 1024**2,
        'gpu_temperature': pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU),
        'inference_fps': pipeline.get_stats()['fps'],
        'events_sent': emotion_client.events_sent,
        'reconnections': emotion_client.reconnection_count,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
```

### 7.2 Dashboard Metrics

Key metrics visualized in Grafana:

| Metric | Alert Threshold | Description |
|--------|----------------|-------------|
| `inference_latency_p50` | > 120 ms | Median inference time |
| `inference_latency_p95` | > 250 ms | 95th percentile latency |
| `gpu_temperature` | > 80°C | Thermal throttling risk |
| `websocket_reconnections` | > 5/hour | Connection stability |
| `abstention_rate` | > 20% | Low-confidence predictions |

---

## 8. Conclusion

Phase 3 completes the Project Reachy deployment pipeline by bringing the trained emotion classifier to the edge. Key achievements include:

1. **Optimized Inference**: TensorRT conversion achieves ~40 ms latency with FP16 precision, providing 3× margin below Gate B thresholds
2. **Robust Communication**: Socket.IO-based WebSocket client with auto-reconnection ensures reliable emotion event streaming
3. **Quality Assurance**: Staged rollout (Shadow → Canary → Production) with automatic rollback protects users from degraded models
4. **Observability**: Comprehensive metrics enable proactive monitoring and rapid incident response

The combination of EfficientNet-B0's efficiency and TensorRT optimization enables real-time, calibrated emotion recognition that seamlessly integrates with Phase 2's emotional intelligence layer.

---

## References

- NVIDIA Corporation. (2024). *TensorRT Developer Guide*. https://docs.nvidia.com/deeplearning/tensorrt/developer-guide/
- NVIDIA Corporation. (2024). *DeepStream SDK Developer Guide*. https://docs.nvidia.com/metropolis/deepstream/dev-guide/
- NVIDIA Corporation. (2024). *JetPack SDK Documentation*. https://developer.nvidia.com/embedded/jetpack
- Tan, M., & Le, Q. V. (2019). EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks. *ICML 2019*.
- Socket.IO. (2024). *Socket.IO Documentation*. https://socket.io/docs/v4/

---

**Document Version**: 1.0  
**Author**: Russell Bray  
**Date**: 2026-01-31  
**Status**: Draft
