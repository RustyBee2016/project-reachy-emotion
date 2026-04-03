"""Dataset control router — creates validation and test datasets for training runs.

Provides endpoints to create AffectNet validation and test datasets with a
common run_ID, ensuring consistency across the training pipeline.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..config import AppConfig, get_config

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dataset-control"])


def _project_root() -> Path:
    """Resolve the project root (four levels up from this file)."""
    return Path(__file__).resolve().parents[4]


class CreateValidationDatasetRequest(BaseModel):
    """Request to create validation dataset from AffectNet."""
    
    run_id: str = Field(..., description="Run identifier (e.g., run_0300)")
    samples_per_class: int = Field(500, description="Samples per emotion class", ge=1, le=10000)
    min_confidence: float = Field(0.6, description="Minimum soft-label confidence", ge=0.0, le=1.0)
    max_subset: int = Field(1, description="Maximum subset difficulty (0=easy, 1=challenging, 2=difficult)", ge=0, le=2)
    seed: int = Field(42, description="Random seed for reproducibility")


class CreateTestDatasetRequest(BaseModel):
    """Request to create test dataset from AffectNet."""
    
    run_id: str = Field(..., description="Run identifier (e.g., run_0300)")
    samples_per_class: int = Field(250, description="Samples per emotion class", ge=1, le=10000)
    source: str = Field("validation", description="Source dataset (validation or no_human)")
    seed: int = Field(142, description="Random seed for reproducibility")


class DatasetCreationResponse(BaseModel):
    """Response from dataset creation."""
    
    run_id: str
    split: str
    total_samples: int
    samples_per_class: Dict[str, int]
    output_path: str
    manifest_path: Optional[str] = None
    ground_truth_path: Optional[str] = None
    status: str


@router.post("/api/v1/datasets/validation/create", response_model=DatasetCreationResponse)
async def create_validation_dataset(
    request: CreateValidationDatasetRequest,
    config: AppConfig = Depends(get_config),
) -> DatasetCreationResponse:
    """
    Create validation dataset from AffectNet validation_set.
    
    This endpoint:
    - Samples images from AffectNet validation_set
    - Filters for 3 classes (neutral=0, happy=1, sad=2)
    - Copies to /videos/validation/run/<run_id>/
    - Creates database records with split='validation', label=<emotion>
    - Creates manifest with labels
    
    The validation dataset is used during training for early stopping and
    hyperparameter tuning.
    """
    logger.info(f"Creating validation dataset for run_id={request.run_id}")
    
    project_root = _project_root()
    python_exe = sys.executable
    
    # Build command
    cmd = [
        python_exe,
        "-m", "trainer.ingest_affectnet",
        "validation-run",
        "--run-id", request.run_id,
        "--samples-per-class", str(request.samples_per_class),
        "--min-confidence", str(request.min_confidence),
        "--max-subset", str(request.max_subset),
        "--seed", str(request.seed),
    ]
    
    try:
        # Run synchronously (validation dataset creation is relatively fast)
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=True,
            timeout=600,  # 10 minute timeout
        )
        
        logger.info(f"Validation dataset created successfully for {request.run_id}")
        logger.debug(f"Command output: {result.stdout}")
        
        # Construct response
        validation_path = config.videos_root / "validation" / "run" / request.run_id
        manifest_path = config.manifests_path / f"{request.run_id}_valid_ds_labeled.jsonl"
        
        return DatasetCreationResponse(
            run_id=request.run_id,
            split="validation",
            total_samples=request.samples_per_class * 3,  # 3 classes
            samples_per_class={
                "happy": request.samples_per_class,
                "sad": request.samples_per_class,
                "neutral": request.samples_per_class,
            },
            output_path=str(validation_path),
            manifest_path=str(manifest_path) if manifest_path.exists() else None,
            status="completed",
        )
        
    except subprocess.TimeoutExpired:
        logger.error(f"Validation dataset creation timed out for {request.run_id}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Validation dataset creation timed out after 10 minutes",
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Validation dataset creation failed: {e.stderr}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation dataset creation failed: {e.stderr}",
        )


@router.post("/api/v1/datasets/test/create", response_model=DatasetCreationResponse)
async def create_test_dataset(
    request: CreateTestDatasetRequest,
    config: AppConfig = Depends(get_config),
) -> DatasetCreationResponse:
    """
    Create test dataset from AffectNet validation_set.
    
    This endpoint:
    - Samples images from AffectNet validation_set (different from validation dataset)
    - Filters for 3 classes (neutral=0, happy=1, sad=2)
    - Copies to /videos/test/run/<run_id>/ with UNLABELED filenames
    - Creates database records with split='test', label=NULL
    - Creates separate ground truth manifest (not in database)
    
    The test dataset is used for final unbiased evaluation after training.
    """
    logger.info(f"Creating test dataset for run_id={request.run_id}")
    
    project_root = _project_root()
    python_exe = sys.executable
    
    # Build command
    cmd = [
        python_exe,
        "-m", "trainer.manage_test_datasets",
        "create",
        "--run-id", request.run_id,
        "--samples-per-class", str(request.samples_per_class),
        "--source", request.source,
        "--seed", str(request.seed),
    ]
    
    try:
        # Run synchronously (test dataset creation is relatively fast)
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=True,
            timeout=600,  # 10 minute timeout
        )
        
        logger.info(f"Test dataset created successfully for {request.run_id}")
        logger.debug(f"Command output: {result.stdout}")
        
        # Construct response
        test_path = config.test_path / request.run_id
        ground_truth_path = config.manifests_path / f"{request.run_id}_test_labels.jsonl"
        
        return DatasetCreationResponse(
            run_id=request.run_id,
            split="test",
            total_samples=request.samples_per_class * 3,  # 3 classes
            samples_per_class={
                "happy": request.samples_per_class,
                "sad": request.samples_per_class,
                "neutral": request.samples_per_class,
            },
            output_path=str(test_path),
            ground_truth_path=str(ground_truth_path) if ground_truth_path.exists() else None,
            status="completed",
        )
        
    except subprocess.TimeoutExpired:
        logger.error(f"Test dataset creation timed out for {request.run_id}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Test dataset creation timed out after 10 minutes",
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Test dataset creation failed: {e.stderr}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test dataset creation failed: {e.stderr}",
        )
