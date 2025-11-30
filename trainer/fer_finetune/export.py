"""
Model export module for deployment.

Exports trained PyTorch models to:
- ONNX (intermediate format)
- TensorRT engine (for Jetson inference)

Model storage path: /media/rusty_admin/project_data/ml_models/resnet50
"""

import torch
from pathlib import Path
from typing import Optional, Dict, Tuple
import logging
import json

logger = logging.getLogger(__name__)

# Model storage constants
MODEL_STORAGE_PATH = "/media/rusty_admin/project_data/ml_models/resnet50"
MODEL_PLACEHOLDER = "resnet50-affectnet-raf-db"


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
            
            if calibration_data:
                # Would need to implement calibrator
                logger.warning("INT8 calibration not implemented, using FP16 fallback")
                config.set_flag(trt.BuilderFlag.FP16)
            else:
                logger.warning("No calibration data for INT8, using FP16 fallback")
                config.set_flag(trt.BuilderFlag.FP16)
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
    num_classes: int = 2,
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
        num_classes: Number of classes
    
    Returns:
        Dictionary of exported file paths
    """
    from .model import load_pretrained_model
    
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
        'class_names': ['happy', 'sad'] if num_classes == 2 else None,
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
