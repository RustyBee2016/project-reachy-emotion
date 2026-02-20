# Week 3: FastAPI Backend Development

**Duration**: ~6 hours  
**Goal**: Understand and extend the FastAPI backend API  
**Prerequisites**: Weeks 1-2 completed, basic REST API knowledge

---

## Day 1: FastAPI Fundamentals (2 hours)

### 1.1 Understanding the API Structure

The Media Mover API follows a layered architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                     Routers (Endpoints)                     │
│  health.py │ media_v1.py │ promote.py │ ingest.py │ ...    │
├─────────────────────────────────────────────────────────────┤
│                     Services (Business Logic)               │
│  promote_service.py │ thumbnail_watcher.py │ video_query   │
├─────────────────────────────────────────────────────────────┤
│                     Schemas (Data Models)                   │
│  video.py │ promote.py │ responses.py │ dialogue.py        │
├─────────────────────────────────────────────────────────────┤
│                     Database (SQLAlchemy)                   │
│  db/models.py │ db/session.py │ repositories/              │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Reading the Main Application

Open `apps/api/app/main.py`:

```python
# Key sections to understand:

# 1. Application factory pattern
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = load_and_validate_config(check_port=False)
    
    app = FastAPI(
        title="Reachy Media Mover",
        version="0.08.4.3",
        root_path=config.api_root_path,
        lifespan=lifespan
    )
    # ...

# 2. Router registration
app.include_router(health.router)
app.include_router(media_v1.router)
app.include_router(promote.router)
# ...

# 3. Lifespan management (startup/shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup logic
    config = load_and_validate_config(check_port=False)
    # ...
    yield
    # Shutdown logic
```

### 1.3 Router Patterns

Examine `apps/api/app/routers/health.py`:

```python
# apps/api/app/routers/health.py

from fastapi import APIRouter, status
from ..schemas.responses import HealthResponse

router = APIRouter(prefix="/api/v1", tags=["health"])

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Return health status of the API."""
    return HealthResponse(
        status="ok",
        version="0.08.4.3",
        # ...
    )
```

**Key concepts:**
- `APIRouter` groups related endpoints
- `prefix` sets URL base path
- `tags` organize OpenAPI documentation
- `response_model` validates output

### 1.4 Exercise: Explore Existing Endpoints

Run the API locally and explore the auto-generated docs:

```bash
# Start the API
cd d:\projects\reachy_emotion
python -m uvicorn apps.api.app.main:app --reload --port 8083

# Open in browser: http://localhost:8083/docs
```

List all endpoints you find in the Swagger UI.

### Checkpoint 3.1
- [ ] Understand router pattern with `APIRouter`
- [ ] Know how endpoints are registered in `main.py`
- [ ] Can access Swagger docs at `/docs`

---

## Day 2: Pydantic Schemas (2 hours)

### 2.1 Understanding Schemas

Schemas define the shape of request and response data. Open `apps/api/app/schemas/video.py`:

```python
# apps/api/app/schemas/video.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class VideoMetadata(BaseModel):
    """Schema for video metadata."""
    
    video_id: str = Field(..., description="Unique video identifier")
    file_path: str = Field(..., description="Path to video file")
    split: str = Field(..., description="Dataset split (temp, train, test)")
    label: Optional[str] = Field(None, description="Emotion label")
    size_bytes: Optional[int] = Field(None, description="File size in bytes")
    duration_sec: Optional[float] = Field(None, description="Video duration")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True  # Enable ORM mode
```

### 2.2 Request vs Response Schemas

Open `apps/api/app/schemas/promote.py`:

```python
# apps/api/app/schemas/promote.py

class PromoteRequest(BaseModel):
    """Request schema for video promotion."""
    
    video_id: str = Field(..., description="Video to promote")
    dest_split: str = Field(..., description="Destination split")
    label: Optional[str] = Field(None, description="Emotion label")
    dry_run: bool = Field(False, description="Simulate without executing")

class PromoteResponse(BaseModel):
    """Response schema for promotion result."""
    
    status: str
    video_id: str
    from_split: str
    to_split: str
    label: Optional[str] = None
    file_path_before: Optional[str] = None
    file_path_after: Optional[str] = None
```

### 2.3 Validation with Pydantic

Pydantic automatically validates data:

```python
from pydantic import BaseModel, Field, validator
from typing import Literal

class PromoteRequest(BaseModel):
    video_id: str
    dest_split: Literal["train", "test", "dataset_all"]  # Restricts values
    label: Optional[str] = None
    
    @validator("label")
    def validate_label_for_train(cls, v, values):
        """Require label when promoting to train split."""
        if values.get("dest_split") == "train" and not v:
            raise ValueError("Label required for train split")
        return v
```

### 2.4 Exercise: Create a New Schema

Create a schema for training status:

```python
# apps/api/app/schemas/training.py (create this file)

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class TrainingStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TrainingMetrics(BaseModel):
    """Metrics from a training run."""
    accuracy: Optional[float] = Field(None, ge=0, le=1)
    f1_score: Optional[float] = Field(None, ge=0, le=1)
    loss: Optional[float] = Field(None, ge=0)
    epoch: int = Field(..., ge=0)

class TrainingRunResponse(BaseModel):
    """Response for training run status."""
    run_id: str
    status: TrainingStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    metrics: Optional[TrainingMetrics] = None
    model_path: Optional[str] = None
    error_message: Optional[str] = None

class TrainingRunListResponse(BaseModel):
    """List of training runs."""
    runs: List[TrainingRunResponse]
    total: int
```

### Checkpoint 3.2
- [ ] Understand Pydantic BaseModel
- [ ] Know difference between request and response schemas
- [ ] Can use Field for validation and documentation
- [ ] Created `training.py` schema file

---

## Day 3: Creating API Endpoints (2 hours)

### 3.1 Endpoint Best Practices

Follow these patterns when creating endpoints:

```python
# apps/api/app/routers/training.py (create this file)

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from ..schemas.training import (
    TrainingRunResponse,
    TrainingRunListResponse,
    TrainingStatus,
)

router = APIRouter(prefix="/api/v1/training", tags=["training"])


@router.get("/runs", response_model=TrainingRunListResponse)
async def list_training_runs(
    status: Optional[TrainingStatus] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List all training runs with optional filtering.
    
    Args:
        status: Filter by training status
        limit: Maximum results to return
        offset: Pagination offset
        
    Returns:
        List of training runs with pagination info
    """
    # TODO: Implement database query
    # For now, return mock data
    mock_runs = [
        TrainingRunResponse(
            run_id="run-001",
            status=TrainingStatus.COMPLETED,
            started_at="2026-01-01T10:00:00Z",
            completed_at="2026-01-01T12:00:00Z",
            model_path="/models/emotion_v1.pt",
        )
    ]
    
    return TrainingRunListResponse(
        runs=mock_runs,
        total=len(mock_runs)
    )


@router.get("/runs/{run_id}", response_model=TrainingRunResponse)
async def get_training_run(run_id: str):
    """
    Get details of a specific training run.
    
    Args:
        run_id: Unique identifier of the training run
        
    Returns:
        Training run details
        
    Raises:
        404: If run_id not found
    """
    # TODO: Query database
    # Mock for now
    if run_id == "run-001":
        return TrainingRunResponse(
            run_id=run_id,
            status=TrainingStatus.COMPLETED,
            started_at="2026-01-01T10:00:00Z",
        )
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Training run {run_id} not found"
    )


@router.post("/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_training(
    dataset_split: str = "train",
    epochs: int = 10,
    dry_run: bool = False,
):
    """
    Trigger a new training run.
    
    Args:
        dataset_split: Which dataset split to use
        epochs: Number of training epochs
        dry_run: If True, validate without starting
        
    Returns:
        Run ID and status
    """
    import uuid
    
    if dry_run:
        return {
            "status": "dry_run",
            "message": "Training would be triggered",
            "parameters": {
                "dataset_split": dataset_split,
                "epochs": epochs,
            }
        }
    
    # TODO: Actually trigger training via n8n or direct call
    run_id = str(uuid.uuid4())
    
    return {
        "status": "accepted",
        "run_id": run_id,
        "message": "Training job queued"
    }
```

### 3.2 Register the Router

Add the new router to `apps/api/app/main.py`:

```python
# In apps/api/app/main.py, add import:
from .routers import training

# In create_app(), add:
app.include_router(training.router)
```

### 3.3 Error Handling

Implement consistent error handling:

```python
from fastapi import HTTPException, status

# 404 - Not Found
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Resource not found"
)

# 400 - Bad Request
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Invalid parameters provided"
)

# 422 - Validation Error (automatic from Pydantic)

# 500 - Internal Server Error
raise HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail="An unexpected error occurred"
)
```

### 3.4 Testing Your Endpoint

```bash
# Start the API
python -m uvicorn apps.api.app.main:app --reload --port 8083

# Test list endpoint
curl http://localhost:8083/api/v1/training/runs

# Test specific run
curl http://localhost:8083/api/v1/training/runs/run-001

# Test trigger (dry run)
curl -X POST "http://localhost:8083/api/v1/training/trigger?dry_run=true"
```

### 3.5 Writing Unit Tests

Create `tests/apps/test_training_router.py`:

```python
# tests/apps/test_training_router.py

import pytest
from fastapi.testclient import TestClient
from apps.api.app.main import app

client = TestClient(app)


def test_list_training_runs():
    """Test listing training runs."""
    response = client.get("/api/v1/training/runs")
    assert response.status_code == 200
    data = response.json()
    assert "runs" in data
    assert "total" in data


def test_get_training_run_found():
    """Test getting existing training run."""
    response = client.get("/api/v1/training/runs/run-001")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == "run-001"


def test_get_training_run_not_found():
    """Test 404 for non-existent run."""
    response = client.get("/api/v1/training/runs/nonexistent")
    assert response.status_code == 404


def test_trigger_training_dry_run():
    """Test dry run training trigger."""
    response = client.post("/api/v1/training/trigger?dry_run=true")
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "dry_run"
```

Run tests:

```bash
pytest tests/apps/test_training_router.py -v
```

### Checkpoint 3.3
- [ ] Created training schema file
- [ ] Created training router with 3 endpoints
- [ ] Registered router in main.py
- [ ] Tested endpoints with curl
- [ ] Written and passed unit tests

---

## API Design Guidelines

### URL Conventions

```
GET    /api/v1/{resource}           # List
GET    /api/v1/{resource}/{id}      # Get one
POST   /api/v1/{resource}           # Create
PUT    /api/v1/{resource}/{id}      # Update
DELETE /api/v1/{resource}/{id}      # Delete
POST   /api/v1/{resource}/{action}  # Custom action
```

### Response Envelope

Use consistent response format:

```python
# apps/api/app/schemas/responses.py

class APIResponse(BaseModel):
    """Standard API response envelope."""
    status: str = "success"
    data: Optional[Any] = None
    message: Optional[str] = None
    errors: Optional[List[str]] = None

# Usage:
@router.get("/items", response_model=APIResponse)
async def list_items():
    items = [...]
    return APIResponse(
        status="success",
        data={"items": items, "total": len(items)}
    )
```

### Pagination

```python
class PaginatedResponse(BaseModel):
    items: List[Any]
    pagination: PaginationInfo

class PaginationInfo(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool
```

---

## Week 3 Deliverables Checklist

- [ ] Understand FastAPI router patterns
- [ ] Created `apps/api/app/schemas/training.py`
- [ ] Created `apps/api/app/routers/training.py`
- [ ] Registered new router in `main.py`
- [ ] Endpoints accessible via Swagger UI
- [ ] Written passing unit tests

---

## Next Steps

Proceed to [Week 4: Streamlit Frontend Development](WEEK_04_STREAMLIT_FRONTEND.md) to learn:
- Streamlit page structure
- Session state management
- Calling the API from the frontend
- Building interactive UI components
