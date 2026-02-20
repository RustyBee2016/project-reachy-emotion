# Week 3 Tutorial: n8n Workflow Testing

**Project**: Reachy Emotion Recognition  
**Duration**: 5 days  
**Prerequisites**: n8n running on Ubuntu 1, FastAPI services operational

---

## Overview

This week focuses on testing the first four n8n agent workflows end-to-end and wiring webhook endpoints to the FastAPI gateway.

### Weekly Goals
- [ ] Test Ingest Agent workflow E2E
- [ ] Test Labeling Agent workflow E2E
- [ ] Test Promotion Agent workflow E2E
- [ ] Wire webhook endpoints to FastAPI gateway

---

## Day 1: n8n Environment Setup & Ingest Agent

### Step 1.1: Verify n8n Environment

Connect to Ubuntu 1 and verify n8n is running:

```bash
# SSH to Ubuntu 1
ssh user@10.0.4.130

# Check n8n status
docker ps | grep n8n

# View n8n logs
docker logs n8n-container --tail 100

# Access n8n UI
# Open browser: http://10.0.4.130:5678
```

### Step 1.2: Import Ingest Agent Workflow

1. Open n8n UI at `http://10.0.4.130:5678`
2. Go to **Workflows** → **Import from File**
3. Select `n8n/workflows/ml-agentic-ai_v.2/01_ingest_agent.json`
4. Review the workflow nodes

### Step 1.3: Understand Ingest Agent Flow

The Ingest Agent performs:
1. **Trigger**: Webhook receives new video notification
2. **Validate**: Check file exists and is valid video
3. **Compute Hash**: Calculate SHA256 checksum
4. **Extract Metadata**: Use ffprobe for duration, fps, resolution
5. **Generate Thumbnail**: Create JPG thumbnail
6. **Register in DB**: Insert record into PostgreSQL
7. **Emit Event**: Publish `ingest.completed` event

### Step 1.4: Configure Ingest Agent Credentials

Set up required credentials in n8n:

1. **PostgreSQL Connection**:
   - Host: `10.0.4.130`
   - Port: `5432`
   - Database: `reachy_emotion`
   - User: `reachy_dev`
   - Password: (from Vault)

2. **HTTP Request** (for Media Mover):
   - Base URL: `https://10.0.4.130/api/media`
   - Auth: Bearer token

### Step 1.5: Create Test Video for Ingest

```bash
# On Ubuntu 1, create a test video
cd /media/project_data/reachy_emotion/videos/temp

# Create a simple test video (5 seconds, solid color)
ffmpeg -f lavfi -i color=c=blue:s=640x480:d=5 -c:v libx264 test_ingest_001.mp4

# Verify file exists
ls -la test_ingest_001.mp4
```

### Step 1.6: Test Ingest Agent Manually

1. In n8n, open the Ingest Agent workflow
2. Click **Execute Workflow** (manual trigger)
3. Provide test input:
   ```json
   {
     "file_path": "/media/project_data/reachy_emotion/videos/temp/test_ingest_001.mp4",
     "source": "manual_test"
   }
   ```
4. Monitor execution in n8n UI
5. Verify:
   - [ ] SHA256 computed correctly
   - [ ] Metadata extracted (duration, fps, resolution)
   - [ ] Thumbnail generated in `/videos/thumbs/`
   - [ ] Record inserted in PostgreSQL
   - [ ] `ingest.completed` event emitted

### Step 1.7: Verify Database Record

```bash
# Connect to PostgreSQL
psql -h 10.0.4.130 -U reachy_dev -d reachy_emotion

# Check video table
SELECT video_id, file_path, split, sha256, duration_sec, fps 
FROM video 
WHERE file_path LIKE '%test_ingest%';
```

### Step 1.8: Troubleshooting Ingest Agent

Common issues and fixes:

| Issue | Cause | Fix |
|-------|-------|-----|
| File not found | Path mismatch | Verify absolute path |
| ffprobe error | FFmpeg not installed | `apt install ffmpeg` |
| DB connection failed | Credentials wrong | Check n8n credentials |
| Thumbnail not created | Permissions | Check `/videos/thumbs/` permissions |

### Checkpoint: Day 1 Complete
- [ ] n8n environment verified
- [ ] Ingest Agent imported
- [ ] Test video created
- [ ] Ingest Agent tested successfully
- [ ] Database record verified

---

## Day 2: Labeling Agent Testing

### Step 2.1: Import Labeling Agent Workflow

1. Import `n8n/workflows/ml-agentic-ai_v.2/02_labeling_agent.json`
2. Review workflow nodes

### Step 2.2: Understand Labeling Agent Flow

The Labeling Agent performs:
1. **Trigger**: Webhook receives label request from UI
2. **Validate Label**: Check label is valid (`happy`, `sad`, etc.)
3. **Check Split Rules**: Enforce label policy (train=labeled, test=unlabeled)
4. **Update Database**: Set label in video record
5. **Update Counters**: Increment per-class counts
6. **Check Balance**: Verify 50/50 class balance
7. **Emit Event**: Publish `labeling.completed` event

### Step 2.3: Configure Labeling Agent

Verify credentials are set (same as Ingest Agent).

### Step 2.4: Test Labeling Agent

1. First, ensure a video exists in `temp` split (from Day 1)
2. Execute Labeling Agent with:
   ```json
   {
     "video_id": "<video_id_from_day1>",
     "label": "happy",
     "user_id": "test_user"
   }
   ```
3. Verify:
   - [ ] Label updated in database
   - [ ] Per-class counter incremented
   - [ ] Balance status reported
   - [ ] `labeling.completed` event emitted

### Step 2.5: Test Label Validation

Test invalid label handling:

```json
{
  "video_id": "<video_id>",
  "label": "invalid_emotion",
  "user_id": "test_user"
}
```

Expected: Workflow should fail with validation error.

### Step 2.6: Test Split Label Policy

Test that test split rejects labels:

1. Manually move a video to test split in DB
2. Try to label it
3. Expected: Workflow should reject with policy violation

### Step 2.7: Verify Database Updates

```sql
-- Check label was applied
SELECT video_id, label, split, updated_at 
FROM video 
WHERE video_id = '<video_id>';

-- Check promotion log
SELECT * FROM promotion_log 
WHERE video_id = '<video_id>' 
ORDER BY created_at DESC LIMIT 5;
```

### Checkpoint: Day 2 Complete
- [ ] Labeling Agent imported
- [ ] Valid label test passed
- [ ] Invalid label rejected
- [ ] Split policy enforced
- [ ] Database updates verified

---

## Day 3: Promotion Agent Testing

### Step 3.1: Import Promotion Agent Workflow

1. Import `n8n/workflows/ml-agentic-ai_v.2/03_promotion_agent.json`
2. Review workflow nodes

### Step 3.2: Understand Promotion Agent Flow

The Promotion Agent performs:
1. **Trigger**: Webhook receives promotion request
2. **Validate Request**: Check video exists, label valid
3. **Check Balance**: Verify class balance before promotion
4. **Dry Run** (optional): Preview promotion without changes
5. **Move File**: Call Media Mover to move file
6. **Update Database**: Update split field transactionally
7. **Log Promotion**: Record in promotion_log table
8. **Rebuild Manifest**: Trigger manifest rebuild
9. **Emit Event**: Publish `promotion.completed` event

### Step 3.3: Test Dry Run Mode

Test promotion without making changes:

```json
{
  "video_id": "<video_id>",
  "target_split": "dataset_all",
  "dry_run": true
}
```

Verify:
- [ ] Response shows what would happen
- [ ] No file moved
- [ ] No database changes

### Step 3.4: Test Actual Promotion

Promote a labeled video from temp to dataset_all:

```json
{
  "video_id": "<video_id>",
  "target_split": "dataset_all",
  "dry_run": false,
  "idempotency_key": "test-promo-001"
}
```

Verify:
- [ ] File moved to `/videos/dataset_all/`
- [ ] Database split updated
- [ ] Promotion logged
- [ ] Manifest rebuilt

### Step 3.5: Verify File System Changes

```bash
# Check file moved
ls -la /media/project_data/reachy_emotion/videos/dataset_all/

# Check original location empty
ls -la /media/project_data/reachy_emotion/videos/temp/test_ingest_001.mp4
# Should not exist
```

### Step 3.6: Test Idempotency

Re-run the same promotion with same idempotency key:

```json
{
  "video_id": "<video_id>",
  "target_split": "dataset_all",
  "dry_run": false,
  "idempotency_key": "test-promo-001"
}
```

Expected: Should return success without re-processing.

### Step 3.7: Test Balance Enforcement

Try to promote when class is imbalanced:

1. Promote several "happy" videos
2. Try to promote another "happy" when ratio exceeds threshold
3. Expected: Warning or rejection based on configuration

### Checkpoint: Day 3 Complete
- [ ] Promotion Agent imported
- [ ] Dry run tested
- [ ] Actual promotion tested
- [ ] File system changes verified
- [ ] Idempotency tested
- [ ] Balance enforcement tested

---

## Day 4: Webhook Endpoints Integration

### Step 4.1: Create Webhook Router

Create `apps/api/routers/webhooks.py`:

```python
"""
Webhook endpoints for n8n agent integration.

These endpoints receive events from the web UI and trigger
corresponding n8n workflows.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Optional
import httpx
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# n8n webhook URLs (configure via environment)
N8N_BASE_URL = "http://10.0.4.130:5678/webhook"
N8N_INGEST_WEBHOOK = f"{N8N_BASE_URL}/ingest"
N8N_LABEL_WEBHOOK = f"{N8N_BASE_URL}/label"
N8N_PROMOTE_WEBHOOK = f"{N8N_BASE_URL}/promote"


class IngestRequest(BaseModel):
    """Request to ingest a new video."""
    file_path: str = Field(..., description="Absolute path to video file")
    source: str = Field(default="web_ui", description="Source of the video")
    correlation_id: Optional[str] = Field(default=None)


class LabelRequest(BaseModel):
    """Request to label a video."""
    video_id: str = Field(..., description="Video UUID")
    label: str = Field(..., description="Emotion label")
    user_id: Optional[str] = Field(default="anonymous")
    correlation_id: Optional[str] = Field(default=None)


class PromoteRequest(BaseModel):
    """Request to promote a video to a different split."""
    video_id: str = Field(..., description="Video UUID")
    target_split: str = Field(..., description="Target split (dataset_all, train, test)")
    dry_run: bool = Field(default=False)
    idempotency_key: Optional[str] = Field(default=None)
    correlation_id: Optional[str] = Field(default=None)


class WebhookResponse(BaseModel):
    """Response from webhook trigger."""
    success: bool
    message: str
    correlation_id: str
    workflow_execution_id: Optional[str] = None


async def trigger_n8n_webhook(
    webhook_url: str,
    payload: dict,
    timeout: float = 30.0
) -> dict:
    """
    Trigger an n8n webhook and return the response.
    
    Args:
        webhook_url: n8n webhook URL
        payload: Request payload
        timeout: Request timeout in seconds
    
    Returns:
        Response from n8n
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                webhook_url,
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(504, "n8n webhook timeout")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, f"n8n error: {e.response.text}")
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            raise HTTPException(500, f"Webhook failed: {str(e)}")


@router.post("/ingest", response_model=WebhookResponse)
async def trigger_ingest(request: IngestRequest):
    """
    Trigger the Ingest Agent workflow.
    
    This endpoint is called when a new video is uploaded or generated.
    """
    correlation_id = request.correlation_id or str(uuid.uuid4())
    
    payload = {
        "file_path": request.file_path,
        "source": request.source,
        "correlation_id": correlation_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    logger.info(f"Triggering ingest workflow: {correlation_id}")
    
    result = await trigger_n8n_webhook(N8N_INGEST_WEBHOOK, payload)
    
    return WebhookResponse(
        success=True,
        message="Ingest workflow triggered",
        correlation_id=correlation_id,
        workflow_execution_id=result.get("executionId"),
    )


@router.post("/label", response_model=WebhookResponse)
async def trigger_label(request: LabelRequest):
    """
    Trigger the Labeling Agent workflow.
    
    This endpoint is called when a user labels a video in the UI.
    """
    correlation_id = request.correlation_id or str(uuid.uuid4())
    
    # Validate label
    valid_labels = ["anger", "contempt", "disgust", "fear", 
                    "happiness", "neutral", "sadness", "surprise"]
    if request.label.lower() not in valid_labels:
        raise HTTPException(422, f"Invalid label. Must be one of: {valid_labels}")
    
    payload = {
        "video_id": request.video_id,
        "label": request.label.lower(),
        "user_id": request.user_id,
        "correlation_id": correlation_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    logger.info(f"Triggering label workflow: {correlation_id}")
    
    result = await trigger_n8n_webhook(N8N_LABEL_WEBHOOK, payload)
    
    return WebhookResponse(
        success=True,
        message="Label workflow triggered",
        correlation_id=correlation_id,
        workflow_execution_id=result.get("executionId"),
    )


@router.post("/promote", response_model=WebhookResponse)
async def trigger_promote(request: PromoteRequest):
    """
    Trigger the Promotion Agent workflow.
    
    This endpoint is called when a user accepts a video for the dataset.
    """
    correlation_id = request.correlation_id or str(uuid.uuid4())
    idempotency_key = request.idempotency_key or str(uuid.uuid4())
    
    # Validate target split
    valid_splits = ["dataset_all", "train", "test"]
    if request.target_split not in valid_splits:
        raise HTTPException(422, f"Invalid split. Must be one of: {valid_splits}")
    
    payload = {
        "video_id": request.video_id,
        "target_split": request.target_split,
        "dry_run": request.dry_run,
        "idempotency_key": idempotency_key,
        "correlation_id": correlation_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    logger.info(f"Triggering promote workflow: {correlation_id}")
    
    result = await trigger_n8n_webhook(N8N_PROMOTE_WEBHOOK, payload)
    
    return WebhookResponse(
        success=True,
        message="Promote workflow triggered",
        correlation_id=correlation_id,
        workflow_execution_id=result.get("executionId"),
    )


@router.get("/health")
async def webhook_health():
    """Check webhook endpoint health and n8n connectivity."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://10.0.4.130:5678/healthz",
                timeout=5.0
            )
            n8n_healthy = response.status_code == 200
    except Exception:
        n8n_healthy = False
    
    return {
        "webhooks_healthy": True,
        "n8n_reachable": n8n_healthy,
    }
```

### Step 4.2: Register Webhook Router

Update `apps/api/main.py` to include the webhook router:

```python
from .routers import webhooks

# Add to router includes
app.include_router(webhooks.router)
```

### Step 4.3: Configure n8n Webhook Triggers

For each workflow, update the trigger node to use webhook:

1. Open workflow in n8n
2. Edit the trigger node
3. Set to **Webhook** trigger
4. Configure path (e.g., `/ingest`, `/label`, `/promote`)
5. Set HTTP method to **POST**
6. Save workflow

### Step 4.4: Test Webhook Integration

```bash
# Test ingest webhook
curl -X POST http://10.0.4.140:8000/webhooks/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/media/project_data/reachy_emotion/videos/temp/test_video.mp4",
    "source": "curl_test"
  }'

# Test label webhook
curl -X POST http://10.0.4.140:8000/webhooks/label \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "<video_id>",
    "label": "happy"
  }'

# Test promote webhook
curl -X POST http://10.0.4.140:8000/webhooks/promote \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "<video_id>",
    "target_split": "dataset_all",
    "dry_run": true
  }'
```

### Step 4.5: Verify End-to-End Flow

1. Upload a video via web UI
2. Verify ingest webhook triggered
3. Label the video in UI
4. Verify label webhook triggered
5. Accept video for dataset
6. Verify promote webhook triggered
7. Check n8n execution history

### Checkpoint: Day 4 Complete
- [ ] Webhook router created
- [ ] Router registered in FastAPI
- [ ] n8n webhooks configured
- [ ] All three webhooks tested
- [ ] E2E flow verified

---

## Day 5: Error Handling & Documentation

### Step 5.1: Add Retry Logic to Webhooks

Update webhook router with retry logic:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True
)
async def trigger_n8n_webhook_with_retry(
    webhook_url: str,
    payload: dict,
    timeout: float = 30.0
) -> dict:
    """Trigger webhook with automatic retry on failure."""
    return await trigger_n8n_webhook(webhook_url, payload, timeout)
```

### Step 5.2: Add Error Logging

Create error tracking for failed workflows:

```python
async def log_webhook_error(
    webhook_type: str,
    correlation_id: str,
    error: Exception,
    payload: dict
):
    """Log webhook errors for debugging."""
    logger.error(
        f"Webhook failed: type={webhook_type}, "
        f"correlation_id={correlation_id}, "
        f"error={str(error)}"
    )
    
    # Optionally store in database for later review
    # await db.execute(
    #     "INSERT INTO webhook_errors (...) VALUES (...)",
    #     ...
    # )
```

### Step 5.3: Create Webhook Tests

Create `tests/test_webhooks.py`:

```python
"""Tests for webhook endpoints."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_ingest_webhook_valid():
    """Test ingest webhook with valid input."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("routers.webhooks.trigger_n8n_webhook") as mock:
            mock.return_value = {"executionId": "test-123"}
            
            response = await client.post(
                "/webhooks/ingest",
                json={
                    "file_path": "/videos/temp/test.mp4",
                    "source": "test"
                }
            )
            
            assert response.status_code == 200
            assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_label_webhook_invalid_label():
    """Test label webhook rejects invalid labels."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/webhooks/label",
            json={
                "video_id": "test-uuid",
                "label": "invalid_emotion"
            }
        )
        
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_promote_webhook_dry_run():
    """Test promote webhook dry run mode."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("routers.webhooks.trigger_n8n_webhook") as mock:
            mock.return_value = {"executionId": "test-456", "dry_run": True}
            
            response = await client.post(
                "/webhooks/promote",
                json={
                    "video_id": "test-uuid",
                    "target_split": "dataset_all",
                    "dry_run": True
                }
            )
            
            assert response.status_code == 200
```

### Step 5.4: Run Tests

```bash
pytest tests/test_webhooks.py -v
```

### Step 5.5: Update Documentation

Create `docs/N8N_WEBHOOK_INTEGRATION.md` documenting:
- Webhook endpoints
- n8n workflow configuration
- Error handling
- Troubleshooting guide

### Checkpoint: Day 5 Complete
- [ ] Retry logic added
- [ ] Error logging implemented
- [ ] Tests created and passing
- [ ] Documentation updated

---

## Week 3 Deliverables Summary

| Deliverable | Status | Location |
|-------------|--------|----------|
| Ingest Agent tested | ✅ | n8n workflow |
| Labeling Agent tested | ✅ | n8n workflow |
| Promotion Agent tested | ✅ | n8n workflow |
| Webhook router | ✅ | `apps/api/routers/webhooks.py` |
| Webhook tests | ✅ | `tests/test_webhooks.py` |
| Integration docs | ✅ | `docs/N8N_WEBHOOK_INTEGRATION.md` |

---

## Next Steps

Proceed to [Week 4: Web UI Enhancement & Reconciler](WEEK_04_WEB_UI_RECONCILER.md).
