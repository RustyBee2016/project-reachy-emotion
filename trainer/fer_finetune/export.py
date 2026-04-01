"""
Model export module for deployment.

Exports trained PyTorch models to:
- ONNX (intermediate format)
- TensorRT engine (for Jetson inference)

Model storage path: /media/rusty_admin/project_data/ml_models/efficientnet_b0
"""

import torch
from pathlib import Path
from typing import Optional, Dict, Tuple
import logging
import json

logger = logging.getLogger(__name__)

# Model storage constants
MODEL_STORAGE_PATH = "/media/rusty_admin/project_data/ml_models/efficientnet_b0"
MODEL_PLACEHOLDER = "efficientnet-b0-hsemotion"


def export_to_onnx(
    model: torch.nn.Module,
    output_path: str,
    input_size: int = 224,
    batch_size: int = 1,
    opset_version: int = 17,
    dynamic_batch: bool = True,
    simplify: bool = True,
) -> str:
    """
    Export PyTorch model to ONNX format.
    
    Args:
        model: Trained PyTorch model
        output_path: Path for ONNX file
        input_size: Input image size
        batch_size: Batch size for export
        opset_version: ONNX opset version (17 for TensorRT 8.6+)
        dynamic_batch: Enable dynamic batch size
        simplify: Simplify ONNX graph
    
    Returns:
        Path to exported ONNX file
    """
    model.eval()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create dummy input
    dummy_input = torch.randn(batch_size, 3, input_size, input_size)
    
    # Move to same device as model
    device = next(model.parameters()).device
    dummy_input = dummy_input.to(device)
    
    # Dynamic axes for variable batch size
    dynamic_axes = None
    if dynamic_batch:
        dynamic_axes = {
            'input': {0: 'batch_size'},
            'output': {0: 'batch_size'},
        }
    
    logger.info(f"Exporting model to ONNX: {output_path}")
    
    # Export
    torch.onnx.export(
        model,
        dummy_input,
        str(output_path),
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        dynamic_axes=dynamic_axes,
    )
    
    # Verify export
    try:
        import onnx
        onnx_model = onnx.load(str(output_path))
        onnx.checker.check_model(onnx_model)
        logger.info("ONNX model verification passed")
        
        # Simplify if requested
        if simplify:
            try:
                import onnxsim
                onnx_model, check = onnxsim.simplify(onnx_model)
                if check:
                    onnx.save(onnx_model, str(output_path))
                    logger.info("ONNX model simplified")
            except ImportError:
                logger.warning("onnxsim not available, skipping simplification")
    except ImportError:
        logger.warning("onnx package not available, skipping verification")
    
    logger.info(f"ONNX export complete: {output_path}")
    return str(output_path)


def _build_int8_calibrator(
    calibration_dir: str,
    input_shape: tuple,
    trt_logger,
    max_images: int = 500,
):
    """Build an IInt8EntropyCalibrator2 from a directory of JPEG images.

    The directory should contain representative images (any class) that
    are pre-processed to 224x224 and normalised the same way the model
    expects.  Returns *None* if TensorRT or image loading fails.
    """
    try:
        import tensorrt as trt
        import numpy as np
        from pathlib import Path
    except ImportError:
        return None

    cal_dir = Path(calibration_dir)
    image_files = sorted(
        [p for p in cal_dir.rglob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    )[:max_images]

    if not image_files:
        logger.warning("No images found in calibration directory: %s", cal_dir)
        return None

    # Pre-load all images as a float32 numpy array.
    try:
        import cv2
    except ImportError:
        logger.warning("cv2 not available — cannot build INT8 calibrator")
        return None

    _, c, h, w = 1, input_shape[1], input_shape[2], input_shape[3]
    batch = np.empty((len(image_files), c, h, w), dtype=np.float32)

    for idx, fp in enumerate(image_files):
        img = cv2.imread(str(fp))
        if img is None:
            continue
        img = cv2.resize(img, (w, h))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        batch[idx] = np.transpose(img, (2, 0, 1))  # HWC → CHW

    cache_path = str(cal_dir / "calibration_cache.bin")

    class _Calibrator(trt.IInt8EntropyCalibrator2):
        def __init__(self):
            super().__init__()
            self._idx = 0
            import cuda  # type: ignore[import-untyped]

            self._device_input = cuda.mem_alloc(batch[0].nbytes)

        def get_batch_size(self):
            return 1

        def get_batch(self, names, p_str=None):
            if self._idx >= len(batch):
                return None
            import cuda  # type: ignore[import-untyped]

            cuda.memcpy_htod(self._device_input, np.ascontiguousarray(batch[self._idx]))
            self._idx += 1
            return [int(self._device_input)]

        def read_calibration_cache(self):
            cp = Path(cache_path)
            if cp.exists():
                return cp.read_bytes()
            return None

        def write_calibration_cache(self, cache):
            Path(cache_path).write_bytes(cache)

    try:
        return _Calibrator()
    except Exception as exc:
        logger.warning("Failed to create INT8 calibrator: %s", exc)
        return None


def convert_to_tensorrt(
    onnx_path: str,
    engine_path: str,
    precision: str = "fp16",
    workspace_gb: int = 2,
    min_batch: int = 1,
    opt_batch: int = 1,
    max_batch: int = 8,
    calibration_data: Optional[str] = None,
) -> str:
    """
    Convert ONNX model to TensorRT engine.
    
    NOTE: This should be run ON THE TARGET DEVICE (Jetson Xavier NX)
    to ensure the engine is optimized for that specific GPU architecture.
    
    Args:
        onnx_path: Path to ONNX model
        engine_path: Output path for TensorRT engine
        precision: Precision mode ("fp32", "fp16", "int8")
        workspace_gb: GPU workspace memory in GB
        min_batch: Minimum batch size for optimization
        opt_batch: Optimal batch size for optimization
        max_batch: Maximum batch size for optimization
        calibration_data: Path to calibration data for INT8
    
    Returns:
        Path to TensorRT engine
    """
    try:
        import tensorrt as trt
    except ImportError:
        logger.error("TensorRT not available. Run this on the Jetson device.")
        raise
    
    logger.info(f"Converting ONNX to TensorRT: {onnx_path} -> {engine_path}")
    logger.info(f"Precision: {precision}, Workspace: {workspace_gb}GB")
    
    # Create builder and network
    trt_logger = trt.Logger(trt.Logger.WARNING)
    builder = trt.Builder(trt_logger)
    
    network_flags = 1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
    network = builder.create_network(network_flags)
    
    # Parse ONNX
    parser = trt.OnnxParser(network, trt_logger)
    
    with open(onnx_path, 'rb') as f:
        if not parser.parse(f.read()):
            for i in range(parser.num_errors):
                logger.error(f"ONNX parse error: {parser.get_error(i)}")
            raise RuntimeError("Failed to parse ONNX model")
    
    logger.info(f"ONNX parsed successfully: {network.num_inputs} inputs, {network.num_outputs} outputs")
    
    # Build configuration
    config = builder.create_builder_config()
    config.set_memory_pool_limit(
        trt.MemoryPoolType.WORKSPACE,
        workspace_gb * (1 << 30)
    )
    
    # Set precision
    if precision == "fp16":
        if builder.platform_has_fast_fp16:
            config.set_flag(trt.BuilderFlag.FP16)
            logger.info("FP16 mode enabled")
        else:
            logger.warning("FP16 not supported on this platform, using FP32")
    
    elif precision == "int8":
        if builder.platform_has_fast_int8:
            config.set_flag(trt.BuilderFlag.INT8)
            # Also enable FP16 as a fallback for layers that don't quantize well.
            if builder.platform_has_fast_fp16:
                config.set_flag(trt.BuilderFlag.FP16)

            if calibration_data:
                calibrator = _build_int8_calibrator(
                    calibration_data, input_shape, trt_logger
                )
                if calibrator is not None:
                    config.int8_calibrator = calibrator
                    logger.info("INT8 calibrator attached (%s)", calibration_data)
                else:
                    logger.warning("Calibrator build failed, falling back to FP16")
            else:
                logger.warning("No calibration data for INT8, falling back to FP16")
        else:
            logger.warning("INT8 not supported on this platform, using FP32")
    
    # Set optimization profile for dynamic batch
    profile = builder.create_optimization_profile()
    input_name = network.get_input(0).name
    input_shape = network.get_input(0).shape
    
    # Shape: [batch, channels, height, width]
    min_shape = (min_batch, input_shape[1], input_shape[2], input_shape[3])
    opt_shape = (opt_batch, input_shape[1], input_shape[2], input_shape[3])
    max_shape = (max_batch, input_shape[1], input_shape[2], input_shape[3])
    
    profile.set_shape(input_name, min_shape, opt_shape, max_shape)
    config.add_optimization_profile(profile)
    
    # Build engine
    logger.info("Building TensorRT engine (this may take several minutes)...")
    serialized_engine = builder.build_serialized_network(network, config)
    
    if serialized_engine is None:
        raise RuntimeError("Failed to build TensorRT engine")
    
    # Save engine
    engine_path = Path(engine_path)
    engine_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(engine_path, 'wb') as f:
        f.write(serialized_engine)
    
    logger.info(f"TensorRT engine saved: {engine_path}")
    return str(engine_path)


def export_for_deployment(
    checkpoint_path: str,
    output_dir: str,
    model_name: str = "emotion_classifier",
    precision: str = "fp16",
    input_size: int = 224,
    num_classes: int = 3,
) -> Dict[str, str]:
    """
    Complete export pipeline for deployment.
    
    Exports model to ONNX and generates deployment metadata.
    TensorRT conversion should be done on the target device.
    
    Args:
        checkpoint_path: Path to trained model checkpoint
        output_dir: Output directory for exported files
        model_name: Name for exported model
        precision: Target precision for TensorRT
        input_size: Input image size
        num_classes: Number of classes (3 for Phase 1: happy/sad/neutral)
    
    Returns:
        Dictionary of exported file paths
    """
    from .model_efficientnet import load_pretrained_model
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load model
    logger.info(f"Loading model from {checkpoint_path}")
    model = load_pretrained_model(checkpoint_path, num_classes=num_classes, device='cpu')
    
    # Export to ONNX
    onnx_path = output_dir / f"{model_name}.onnx"
    export_to_onnx(model, str(onnx_path), input_size=input_size)
    
    # Generate deployment metadata
    metadata = {
        'model_name': model_name,
        'model_placeholder': MODEL_PLACEHOLDER,
        'checkpoint_path': str(checkpoint_path),
        'onnx_path': str(onnx_path),
        'input_size': input_size,
        'num_classes': num_classes,
        'precision': precision,
        'class_names': ['happy', 'sad', 'neutral'] if num_classes == 3 else (['happy', 'sad'] if num_classes == 2 else None),
        'normalization': {
            'mean': [0.485, 0.456, 0.406],
            'std': [0.229, 0.224, 0.225],
        },
        'storage_path': MODEL_STORAGE_PATH,
    }
    
    metadata_path = output_dir / f"{model_name}_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Generate TensorRT conversion script for Jetson
    trt_script = f'''#!/bin/bash
# TensorRT conversion script for Jetson Xavier NX
# Run this ON THE JETSON device

ONNX_PATH="{model_name}.onnx"
ENGINE_PATH="{model_name}.engine"

/usr/src/tensorrt/bin/trtexec \\
    --onnx=$ONNX_PATH \\
    --saveEngine=$ENGINE_PATH \\
    --{'fp16' if precision == 'fp16' else 'fp32'} \\
    --workspace=2048 \\
    --minShapes=input:1x3x{input_size}x{input_size} \\
    --optShapes=input:1x3x{input_size}x{input_size} \\
    --maxShapes=input:8x3x{input_size}x{input_size}

echo "Engine saved to $ENGINE_PATH"
'''
    
    script_path = output_dir / f"convert_to_trt.sh"
    with open(script_path, 'w') as f:
        f.write(trt_script)
    
    logger.info(f"Export complete. Files in {output_dir}:")
    logger.info(f"  - {onnx_path.name}")
    logger.info(f"  - {metadata_path.name}")
    logger.info(f"  - {script_path.name}")
    
    return {
        'onnx': str(onnx_path),
        'metadata': str(metadata_path),
        'trt_script': str(script_path),
        'output_dir': str(output_dir),
    }


def export_efficientnet_for_deployment(
    checkpoint_path: str,
    output_dir: str,
    model_name: str = "emotion_efficientnet",
    precision: str = "fp16",
    input_size: int = 224,
    num_classes: int = 3,
) -> Dict[str, str]:
    """
    Complete export pipeline for EfficientNet-B0 emotion classifier deployment.
    
    Exports HSEmotion EfficientNet-B0 model to ONNX and generates deployment metadata.
    TensorRT conversion should be done on the target device (Jetson Xavier NX).
    
    Args:
        checkpoint_path: Path to trained EfficientNet checkpoint
        output_dir: Output directory for exported files
        model_name: Name for exported model
        precision: Target precision for TensorRT ("fp16" or "fp32")
        input_size: Input image size (default 224 for EfficientNet-B0)
        num_classes: Number of classes (3 for Phase 1: happy/sad/neutral)
    
    Returns:
        Dictionary of exported file paths and metadata
    """
    from .model_efficientnet import create_efficientnet_model
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load EfficientNet model from checkpoint
    logger.info(f"Loading EfficientNet model from {checkpoint_path}")
    
    # Create model architecture
    model = create_efficientnet_model(
        num_classes=num_classes,
        dropout_rate=0.3,
        pretrained=False,  # We'll load from checkpoint
        use_multi_task=False,
    )
    
    # Load checkpoint
    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
    
    # Handle different checkpoint formats
    if 'model_state_dict' in checkpoint:
        state_dict = checkpoint['model_state_dict']
    elif 'state_dict' in checkpoint:
        state_dict = checkpoint['state_dict']
    else:
        state_dict = checkpoint
    
    # Remove 'module.' prefix if present (from DataParallel)
    state_dict = {k.replace('module.', ''): v for k, v in state_dict.items()}
    
    model.load_state_dict(state_dict)
    model.eval()
    
    logger.info("EfficientNet model loaded successfully")
    
    # Export to ONNX
    onnx_path = output_dir / f"{model_name}.onnx"
    export_to_onnx(
        model, 
        str(onnx_path), 
        input_size=input_size,
        opset_version=17,  # TensorRT 8.6+ compatibility
        dynamic_batch=True,
    )
    
    # Generate deployment metadata specific to EfficientNet
    metadata = {
        'model_name': model_name,
        'model_type': 'efficientnet_b0_hsemotion',
        'model_placeholder': 'enet_b0_8_best_vgaf',
        'checkpoint_path': str(checkpoint_path),
        'onnx_path': str(onnx_path),
        'input_size': input_size,
        'num_classes': num_classes,
        'precision': precision,
        'class_names': ['happy', 'sad', 'neutral'] if num_classes == 3 else (
            ['happy', 'sad'] if num_classes == 2 else [
                'anger', 'contempt', 'disgust', 'fear',
                'happy', 'neutral', 'sad', 'surprise'
            ]
        ),
        'normalization': {
            'mean': [0.485, 0.456, 0.406],  # ImageNet normalization
            'std': [0.229, 0.224, 0.225],
        },
        'storage_path': '/media/rusty_admin/project_data/ml_models/efficientnet_b0',
        'performance_targets': {
            'jetson_xavier_nx': {
                'latency_p50_ms': 40,
                'latency_p95_ms': 80,
                'gpu_memory_gb': 0.8,
                'throughput_fps': 25,
            }
        },
        'gate_b_thresholds': {
            'max_latency_p50_ms': 120.0,
            'max_latency_p95_ms': 250.0,
            'max_gpu_memory_gb': 2.5,
            'min_f1_macro': 0.80 if num_classes == 2 else 0.75,
        }
    }
    
    metadata_path = output_dir / f"{model_name}_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Generate TensorRT conversion script optimized for EfficientNet-B0
    trt_script = f'''#!/bin/bash
# TensorRT conversion script for EfficientNet-B0 on Jetson Xavier NX
# Run this ON THE JETSON device
#
# Expected performance:
#   - Latency: ~40ms p50 (3x headroom vs 120ms budget)
#   - Memory: ~0.8GB GPU (3x headroom vs 2.5GB budget)

ONNX_PATH="{model_name}.onnx"
ENGINE_PATH="{model_name}.engine"

echo "Converting EfficientNet-B0 to TensorRT engine..."
echo "Target precision: {precision}"
echo "Input size: {input_size}x{input_size}"

/usr/src/tensorrt/bin/trtexec \\
    --onnx=$ONNX_PATH \\
    --saveEngine=$ENGINE_PATH \\
    --{'fp16' if precision == 'fp16' else 'fp32'} \\
    --workspace=2048 \\
    --minShapes=input:1x3x{input_size}x{input_size} \\
    --optShapes=input:4x3x{input_size}x{input_size} \\
    --maxShapes=input:8x3x{input_size}x{input_size} \\
    --avgRuns=100 \\
    --verbose

if [ $? -eq 0 ]; then
    echo "✓ TensorRT engine created successfully: $ENGINE_PATH"
    echo "✓ Ready for DeepStream integration"
    
    # Verify engine performance
    echo "Running performance validation..."
    /usr/src/tensorrt/bin/trtexec \\
        --loadEngine=$ENGINE_PATH \\
        --shapes=input:1x3x{input_size}x{input_size} \\
        --avgRuns=100 \\
        --duration=10
else
    echo "✗ TensorRT conversion failed"
    exit 1
fi
'''
    
    script_path = output_dir / f"convert_to_trt.sh"
    with open(script_path, 'w') as f:
        f.write(trt_script)
    
    # Make script executable (on Unix systems)
    try:
        import stat
        script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)
    except:
        pass  # Windows doesn't need this
    
    # Generate DeepStream config template
    deepstream_config = f'''[application]
enable-perf-measurement=1
perf-measurement-interval-sec=5

[tiled-display]
enable=0

[source0]
enable=1
type=3
uri=file:///opt/reachy/test_videos/emotion_test.mp4
num-sources=1
gpu-id=0

[sink0]
enable=1
type=2
sync=0
gpu-id=0

[osd]
enable=1
gpu-id=0
border-width=2

[streammux]
gpu-id=0
batch-size=1
batched-push-timeout=40000
width={input_size}
height={input_size}
enable-padding=0
nvbuf-memory-type=0

[primary-gie]
enable=1
gpu-id=0
model-engine-file={model_name}.engine
batch-size=1
bbox-border-color0=1;0;0;1
bbox-border-color1=0;1;1;1
interval=0
gie-unique-id=1
nvbuf-memory-type=0
config-file-path=emotion_inference.txt
'''
    
    deepstream_path = output_dir / f"deepstream_config.txt"
    with open(deepstream_path, 'w') as f:
        f.write(deepstream_config)
    
    logger.info(f"EfficientNet export complete. Files in {output_dir}:")
    logger.info(f"  - {onnx_path.name} (ONNX model)")
    logger.info(f"  - {metadata_path.name} (deployment metadata)")
    logger.info(f"  - {script_path.name} (TensorRT conversion script)")
    logger.info(f"  - {deepstream_path.name} (DeepStream config template)")
    
    return {
        'onnx': str(onnx_path),
        'metadata': str(metadata_path),
        'trt_script': str(script_path),
        'deepstream_config': str(deepstream_path),
        'output_dir': str(output_dir),
        'model_type': 'efficientnet_b0_hsemotion',
        'performance_targets': metadata['performance_targets'],
    }


def verify_onnx_inference(
    onnx_path: str,
    test_input: Optional[torch.Tensor] = None,
    input_size: int = 224,
) -> Dict[str, any]:
    """
    Verify ONNX model with test inference.
    
    Args:
        onnx_path: Path to ONNX model
        test_input: Optional test input tensor
        input_size: Input size if generating test input
    
    Returns:
        Inference results
    """
    try:
        import onnxruntime as ort
    except ImportError:
        logger.error("onnxruntime not available")
        return {'error': 'onnxruntime not installed'}
    
    # Create session
    session = ort.InferenceSession(onnx_path)
    
    # Get input/output info
    input_info = session.get_inputs()[0]
    output_info = session.get_outputs()[0]
    
    logger.info(f"Input: {input_info.name}, shape: {input_info.shape}")
    logger.info(f"Output: {output_info.name}, shape: {output_info.shape}")
    
    # Create test input if not provided
    if test_input is None:
        import numpy as np
        test_input = np.random.randn(1, 3, input_size, input_size).astype(np.float32)
    elif isinstance(test_input, torch.Tensor):
        test_input = test_input.numpy()
    
    # Run inference
    outputs = session.run(None, {input_info.name: test_input})
    
    result = {
        'input_shape': list(test_input.shape),
        'output_shape': list(outputs[0].shape),
        'output_sample': outputs[0][0].tolist(),
    }
    
    logger.info(f"ONNX inference successful: output shape {outputs[0].shape}")
    
    return result
