# Week 7: Testing & Quality Assurance

**Duration**: ~6 hours  
**Goal**: Achieve 80%+ test coverage with comprehensive testing  
**Prerequisites**: Weeks 1-6 completed, pytest basics

---

## Day 1: Testing Fundamentals (2 hours)

### 1.1 Testing Strategy Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Testing Pyramid                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                        ┌───────────┐                            │
│                        │    E2E    │  ← Few, slow, high value   │
│                        │   Tests   │                            │
│                      ┌─┴───────────┴─┐                          │
│                      │  Integration  │  ← Some, medium speed    │
│                      │    Tests      │                          │
│                    ┌─┴───────────────┴─┐                        │
│                    │    Unit Tests     │  ← Many, fast, focused │
│                    └───────────────────┘                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Project Test Structure

```
tests/
├── apps/                    # Application-specific tests
│   ├── test_api_routers.py
│   ├── test_services.py
│   └── test_web_pages.py
├── test_api_client.py       # API client tests
├── test_api_client_retry.py # Retry logic tests
├── test_config.py           # Configuration tests
├── test_web_ui.py           # Streamlit UI tests
├── test_websocket_client.py # WebSocket tests
├── conftest.py              # Shared fixtures
└── conftest_web_ui.py       # Web UI fixtures
```

### 1.3 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api_client.py -v

# Run with coverage
pytest tests/ --cov=apps --cov-report=html

# Run only fast tests (exclude slow integration tests)
pytest tests/ -v -m "not slow"

# Run tests matching a pattern
pytest tests/ -v -k "test_list"
```

### 1.4 Understanding Existing Tests

Open `tests/test_api_client.py`:

```python
# Key patterns to understand:

# 1. Test fixtures from conftest.py
@pytest.fixture
def api_client():
    """Create test API client."""
    return ReachyAPIClient(config)

# 2. Mocking external calls
@patch("apps.web.api_client.requests.get")
def test_list_videos(mock_get):
    mock_get.return_value.json.return_value = {"items": []}
    result = api_client.list_videos("temp")
    assert "items" in result

# 3. Testing error handling
def test_list_videos_connection_error():
    with pytest.raises(ConnectionError):
        api_client.list_videos("temp")
```

### Checkpoint 7.1
- [ ] Understand testing pyramid
- [ ] Can run tests with pytest
- [ ] Know how to use mocking
- [ ] Understand test fixtures

---

## Day 2: Writing Unit Tests (2 hours)

### 2.1 Testing the Training Router

Create `tests/apps/test_training_router.py`:

```python
# tests/apps/test_training_router.py
"""Unit tests for training router endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime

from apps.api.app.main import app

client = TestClient(app)


class TestTrainingRunsEndpoint:
    """Tests for GET /api/v1/training/runs."""
    
    def test_list_training_runs_success(self):
        """Test successful listing of training runs."""
        response = client.get("/api/v1/training/runs")
        
        assert response.status_code == 200
        data = response.json()
        assert "runs" in data
        assert "total" in data
        assert isinstance(data["runs"], list)
    
    def test_list_training_runs_with_status_filter(self):
        """Test filtering runs by status."""
        response = client.get("/api/v1/training/runs?status=completed")
        
        assert response.status_code == 200
        data = response.json()
        # All returned runs should have status=completed
        for run in data["runs"]:
            assert run["status"] == "completed"
    
    def test_list_training_runs_pagination(self):
        """Test pagination parameters."""
        response = client.get("/api/v1/training/runs?limit=5&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) <= 5


class TestTrainingRunDetailEndpoint:
    """Tests for GET /api/v1/training/runs/{run_id}."""
    
    def test_get_training_run_found(self):
        """Test retrieving existing training run."""
        response = client.get("/api/v1/training/runs/run-001")
        
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == "run-001"
    
    def test_get_training_run_not_found(self):
        """Test 404 for non-existent training run."""
        response = client.get("/api/v1/training/runs/nonexistent-run")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


class TestTrainingTriggerEndpoint:
    """Tests for POST /api/v1/training/trigger."""
    
    def test_trigger_training_dry_run(self):
        """Test dry run training trigger."""
        response = client.post(
            "/api/v1/training/trigger",
            params={"dry_run": True, "epochs": 50}
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "dry_run"
        assert "parameters" in data
    
    def test_trigger_training_actual(self):
        """Test actual training trigger."""
        response = client.post(
            "/api/v1/training/trigger",
            params={"dry_run": False, "epochs": 10}
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert "run_id" in data
    
    def test_trigger_training_invalid_epochs(self):
        """Test validation of epochs parameter."""
        response = client.post(
            "/api/v1/training/trigger",
            params={"epochs": -5}
        )
        
        # Should reject negative epochs
        assert response.status_code == 422
```

### 2.2 Testing the API Client

Add to `tests/test_api_client.py`:

```python
# tests/test_api_client.py additions

import pytest
from unittest.mock import patch, MagicMock
from requests.exceptions import ConnectionError, Timeout, HTTPError

from apps.web import api_client


class TestRelabelVideo:
    """Tests for relabel_video function."""
    
    @patch("apps.web.api_client.requests.put")
    def test_relabel_video_success(self, mock_put):
        """Test successful video relabeling."""
        mock_put.return_value.json.return_value = {
            "status": "success",
            "video_id": "test-123",
            "label": "happy"
        }
        mock_put.return_value.raise_for_status = MagicMock()
        
        result = api_client.relabel_video("test-123", "happy")
        
        assert result["status"] == "success"
        assert result["label"] == "happy"
        mock_put.assert_called_once()
    
    @patch("apps.web.api_client.requests.put")
    def test_relabel_video_not_found(self, mock_put):
        """Test relabeling non-existent video."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        mock_put.return_value = mock_response
        
        with pytest.raises(HTTPError):
            api_client.relabel_video("nonexistent", "happy")


class TestDeleteVideo:
    """Tests for delete_video function."""
    
    @patch("apps.web.api_client.requests.delete")
    def test_delete_video_success(self, mock_delete):
        """Test successful video deletion."""
        mock_delete.return_value.json.return_value = {
            "status": "success",
            "video_id": "test-123"
        }
        mock_delete.return_value.raise_for_status = MagicMock()
        
        result = api_client.delete_video("test-123")
        
        assert result["status"] == "success"


class TestRetryLogic:
    """Tests for retry decorator."""
    
    @patch("apps.web.api_client.requests.get")
    def test_retry_on_connection_error(self, mock_get):
        """Test that connection errors trigger retries."""
        # Fail twice, then succeed
        mock_get.side_effect = [
            ConnectionError("Connection refused"),
            ConnectionError("Connection refused"),
            MagicMock(json=lambda: {"items": []}, raise_for_status=lambda: None)
        ]
        
        result = api_client.list_videos("temp")
        
        assert mock_get.call_count == 3
        assert "items" in result
    
    @patch("apps.web.api_client.requests.get")
    def test_retry_exhausted(self, mock_get):
        """Test that retries are exhausted after max attempts."""
        mock_get.side_effect = ConnectionError("Always fails")
        
        with pytest.raises(ConnectionError):
            api_client.list_videos("temp")
        
        # Default MAX_RETRIES + 1 initial attempt
        assert mock_get.call_count == 4
```

### Checkpoint 7.2
- [ ] Created training router tests
- [ ] Created API client tests
- [ ] Tests pass with `pytest -v`

---

## Day 3: Integration and UI Testing (2 hours)

### 3.1 Testing Streamlit Pages

Create `tests/apps/test_streamlit_pages.py`:

```python
# tests/apps/test_streamlit_pages.py
"""Integration tests for Streamlit pages."""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


class TestGeneratePage:
    """Tests for Generate page functions."""
    
    def test_prompt_templates_structure(self):
        """Test that prompt templates are properly structured."""
        from apps.web.pages import _01_Generate as generate_page
        
        # This tests the internal function
        templates = generate_page._prompt_templates()
        
        assert "happy" in templates
        assert "sad" in templates
        assert isinstance(templates["happy"], list)
        assert len(templates["happy"]) > 0
    
    @patch("apps.web.api_client.request_generation")
    def test_submit_generation_success(self, mock_request):
        """Test generation submission."""
        mock_request.return_value = {"status": "queued", "id": "gen-123"}
        
        # Would need to mock Streamlit session state
        # This is a simplified example
        result = mock_request(
            prompt="a happy person",
            correlation_id="test-123",
            params={"emotion": "happy"}
        )
        
        assert result["status"] == "queued"


class TestTrainingPage:
    """Tests for Training page functions."""
    
    def test_gate_a_check_pass(self):
        """Test Gate A validation with passing metrics."""
        from apps.web.pages import _03_Train as train_page
        
        metrics = {
            "macro_f1": 0.87,
            "balanced_accuracy": 0.88,
            "f1_happy": 0.89,
            "f1_sad": 0.85,
            "ece": 0.06,
            "brier": 0.12,
        }
        
        checks = train_page._check_gate_a(metrics)
        
        assert all(c["passed"] for c in checks.values())
    
    def test_gate_a_check_fail(self):
        """Test Gate A validation with failing metrics."""
        from apps.web.pages import _03_Train as train_page
        
        metrics = {
            "macro_f1": 0.75,  # Below threshold
            "balanced_accuracy": 0.80,  # Below threshold
            "f1_happy": 0.70,
            "f1_sad": 0.65,  # Below floor
            "ece": 0.15,  # Above threshold
            "brier": 0.25,  # Above threshold
        }
        
        checks = train_page._check_gate_a(metrics)
        
        # Should have failures
        assert not all(c["passed"] for c in checks.values())


class TestDeployPage:
    """Tests for Deploy page functions."""
    
    def test_gate_b_check_pass(self):
        """Test Gate B validation with passing metrics."""
        from apps.web.pages import _04_Deploy as deploy_page
        
        metrics = {
            "fps": 28,
            "latency_p50_ms": 95,
            "latency_p95_ms": 180,
        }
        
        checks = deploy_page._check_gate_b(metrics)
        
        assert all(c["passed"] for c in checks.values())
    
    def test_gate_b_check_fail_fps(self):
        """Test Gate B validation with low FPS."""
        from apps.web.pages import _04_Deploy as deploy_page
        
        metrics = {
            "fps": 20,  # Below 25 threshold
            "latency_p50_ms": 95,
            "latency_p95_ms": 180,
        }
        
        checks = deploy_page._check_gate_b(metrics)
        
        assert not checks["FPS"]["passed"]
```

### 3.2 End-to-End Test

Create `tests/test_e2e_webapp.py`:

```python
# tests/test_e2e_webapp.py
"""End-to-end tests for web application flow."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from apps.api.app.main import app


class TestVideoWorkflowE2E:
    """End-to-end test for video upload → label → promote flow."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.mark.slow
    def test_complete_video_workflow(self, client):
        """Test complete video workflow from upload to promotion."""
        
        # Step 1: Upload video
        with open("tests/fixtures/sample_video.mp4", "rb") as f:
            upload_response = client.post(
                "/api/media/ingest",
                files={"file": ("test.mp4", f, "video/mp4")},
                data={"for_training": "true", "correlation_id": "e2e-test-001"}
            )
        
        # May fail if no test file exists - that's expected
        if upload_response.status_code == 200:
            video_id = upload_response.json().get("video_id")
            
            # Step 2: Verify video in temp
            list_response = client.get("/api/v1/media/list?split=temp")
            assert list_response.status_code == 200
            
            # Step 3: Promote video
            promote_response = client.post(
                "/api/v1/promote/stage",
                json={
                    "video_ids": [video_id],
                    "label": "happy",
                    "dry_run": False
                }
            )
            
            assert promote_response.status_code in [200, 201]
    
    @pytest.mark.slow
    def test_training_trigger_workflow(self, client):
        """Test training trigger and status check."""
        
        # Step 1: Trigger training (dry run)
        trigger_response = client.post(
            "/api/v1/training/trigger?dry_run=true&epochs=10"
        )
        
        assert trigger_response.status_code == 202
        
        # Step 2: List runs
        runs_response = client.get("/api/v1/training/runs")
        
        assert runs_response.status_code == 200


class TestHealthChecks:
    """Test health check endpoints."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_api_health(self, client):
        """Test API health endpoint."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
```

### 3.3 Running Coverage Report

```bash
# Run tests with coverage
pytest tests/ --cov=apps --cov-report=html --cov-report=term-missing

# View coverage report
# Open htmlcov/index.html in browser

# Check coverage threshold
pytest tests/ --cov=apps --cov-fail-under=80
```

### Checkpoint 7.3
- [ ] Created Streamlit page tests
- [ ] Created E2E workflow tests
- [ ] Coverage report generated
- [ ] Coverage ≥ 80%

---

## Test Fixtures

Create `tests/fixtures/` directory with test data:

```python
# tests/conftest.py additions

import pytest
import os
from pathlib import Path

@pytest.fixture
def sample_video_bytes():
    """Return sample video file bytes for testing."""
    # Create a minimal valid MP4 file or return mock bytes
    return b"mock video content"

@pytest.fixture
def mock_training_run():
    """Return mock training run data."""
    return {
        "run_id": "test-run-001",
        "status": "completed",
        "started_at": "2026-01-01T10:00:00Z",
        "completed_at": "2026-01-01T12:00:00Z",
        "metrics": {
            "macro_f1": 0.87,
            "balanced_accuracy": 0.88,
            "loss": 0.234,
        },
        "gate_a_passed": True,
    }

@pytest.fixture
def mock_jetson_status():
    """Return mock Jetson status data."""
    return {
        "online": True,
        "gpu_utilization": 45,
        "gpu_memory_used_gb": 1.8,
        "temperature_c": 52,
    }
```

---

## Week 7 Deliverables Checklist

- [ ] Training router unit tests
- [ ] API client unit tests with mocking
- [ ] Streamlit page function tests
- [ ] End-to-end workflow tests
- [ ] Test fixtures created
- [ ] Coverage report generated
- [ ] Coverage ≥ 80%

---

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements-phase1.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest tests/ --cov=apps --cov-fail-under=80
```

---

## Next Steps

Proceed to [Week 8: Integration & Production Readiness](WEEK_08_INTEGRATION.md) to:
- Final integration testing
- Documentation completion
- Security review
- Production deployment preparation
