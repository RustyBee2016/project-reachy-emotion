# Week 8 Tutorial: Documentation, Hardening & Beta Release

**Project**: Reachy Emotion Recognition  
**Duration**: 5 days  
**Prerequisites**: Weeks 1-7 complete, all tests passing

---

## Overview

This final week focuses on documentation completion, security hardening, and preparing the Beta Release.

### Weekly Goals
- [ ] Update all documentation (README, runbooks, API docs)
- [ ] Security hardening (JWT enforcement, rate limiting)
- [ ] Error handling review across all components
- [ ] Create operator runbooks for common scenarios
- [ ] Final regression testing
- [ ] Tag Beta Release (v0.08.5-beta)

---

## Day 1: Documentation Update

### Step 1.1: Update Main README

Update `README.md` with current project status:

```markdown
# Reachy Emotion Recognition

[![Version](https://img.shields.io/badge/version-0.08.5--beta-blue)]()
[![Tests](https://img.shields.io/badge/tests-passing-green)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

## Overview

Reachy Emotion Recognition is a privacy-preserving emotion classification system
for the Reachy Mini companion robot. It uses EfficientNet-B0 fine-tuned on AffectNet
and RAF-DB datasets to classify emotions from video in real-time.

## Features

- **Real-time emotion detection** on Jetson Xavier NX
- **Privacy-first architecture** - all processing on-device
- **Continuous improvement loop** - synthetic video generation and labeling
- **LLM integration** - emotion-aware responses via LM Studio
- **Gesture control** - emotion-to-gesture mapping for robot interaction

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Jetson NX     │────▶│   Ubuntu 2      │────▶│   Ubuntu 1      │
│   (Inference)   │     │   (Gateway)     │     │   (Training)    │
│   DeepStream    │     │   FastAPI       │     │   Media Mover   │
│   TensorRT      │     │   Streamlit     │     │   PostgreSQL    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Quick Start

### Prerequisites

- Ubuntu 20.04 LTS
- Python 3.8+
- NVIDIA GPU (for training)
- Jetson Xavier NX with JetPack 5.x (for inference)

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/reachy-emotion.git
cd reachy-emotion

# Install dependencies
pip install -r requirements-phase1.txt
pip install -r requirements-phase2.txt

# Set up database
psql -f alembic/versions/001_phase1_schema.sql

# Start services
./start_media_api.sh
./start_gateway.sh
```

### Running the Web UI

```bash
cd apps/web
streamlit run landing_page.py
```

## Documentation

- [API Reference](docs/API_ENDPOINT_REFERENCE.md)
- [Deployment Guide](docs/JETSON_DEPLOYMENT_GUIDE.md)
- [Observability Guide](docs/OBSERVABILITY_GUIDE.md)
- [Web UI Guide](docs/WEB_UI_GUIDE.md)
- [n8n Integration](docs/N8N_WEBHOOK_INTEGRATION.md)

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run E2E tests
python tests/e2e/run_e2e_test.py

# Run performance benchmarks
python tests/e2e/benchmark_performance.py
```

## Quality Gates

### Gate A (Offline Validation)
- Macro F1 ≥ 0.84
- Balanced Accuracy ≥ 0.85
- ECE ≤ 0.08

### Gate B (Robot Deployment)
- FPS ≥ 25
- Latency p50 ≤ 120ms
- GPU Memory ≤ 2.5GB

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.
```

### Step 1.2: Create API Documentation

Create `docs/API_REFERENCE.md`:

```markdown
# API Reference

## Base URLs

| Service | URL | Description |
|---------|-----|-------------|
| Gateway | `https://10.0.4.140:8000` | Main API gateway |
| Media Mover | `https://10.0.4.130:8083` | File operations |
| n8n | `http://10.0.4.130:5678` | Workflow automation |

## Authentication

All protected endpoints require Bearer token authentication:

```
Authorization: Bearer <token>
```

Tokens are issued via the `/auth/token` endpoint.

## Endpoints

### Videos

#### List Videos
```
GET /api/videos/list
```

Query Parameters:
- `split` (string): Filter by split (temp, dataset_all, train, test)
- `limit` (int): Maximum results (default: 50)
- `offset` (int): Pagination offset
- `label` (string): Filter by label

Response:
```json
{
  "items": [
    {
      "video_id": "uuid",
      "file_path": "videos/temp/clip.mp4",
      "split": "temp",
      "label": null,
      "duration_sec": 3.5,
      "created_at": "2025-01-28T10:00:00Z"
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

#### Get Video
```
GET /api/videos/{video_id}
```

Response:
```json
{
  "video_id": "uuid",
  "file_path": "videos/temp/clip.mp4",
  "split": "temp",
  "label": null,
  "duration_sec": 3.5,
  "fps": 30,
  "width": 640,
  "height": 480,
  "sha256": "abc123...",
  "created_at": "2025-01-28T10:00:00Z"
}
```

#### Update Label
```
PATCH /api/videos/{video_id}/label
```

Request:
```json
{
  "new_label": "happy"
}
```

### Promotion

#### Stage to Dataset
```
POST /api/v1/promote/stage
```

Request:
```json
{
  "video_ids": ["uuid1", "uuid2"],
  "label": "happy",
  "dry_run": false,
  "idempotency_key": "unique-key"
}
```

#### Sample for Training
```
POST /api/v1/promote/sample
```

Request:
```json
{
  "run_id": "training-run-001",
  "target_split": "train",
  "sample_fraction": 0.7,
  "strategy": "stratified",
  "seed": 42,
  "dry_run": false
}
```

### Webhooks

#### Trigger Ingest
```
POST /webhooks/ingest
```

Request:
```json
{
  "file_path": "/videos/temp/clip.mp4",
  "source": "web_ui"
}
```

#### Trigger Label
```
POST /webhooks/label
```

Request:
```json
{
  "video_id": "uuid",
  "label": "happy",
  "user_id": "user123"
}
```

#### Trigger Promote
```
POST /webhooks/promote
```

Request:
```json
{
  "video_id": "uuid",
  "target_split": "dataset_all",
  "dry_run": false
}
```

### LLM

#### Generate Response
```
POST /api/llm/generate
```

Request:
```json
{
  "emotion": "happy",
  "confidence": 0.85,
  "context": "User greeting"
}
```

Response:
```json
{
  "text": "Hello! It's wonderful to see you in such good spirits!",
  "gesture": "WAVE",
  "model": "llama-3.1-8b"
}
```

### Health & Metrics

#### Health Check
```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "0.08.5-beta",
  "uptime_seconds": 3600
}
```

#### Prometheus Metrics
```
GET /metrics
```

Returns Prometheus-formatted metrics.

## Error Responses

All errors follow this format:

```json
{
  "error": "error_code",
  "message": "Human-readable message",
  "correlation_id": "uuid",
  "fields": {}
}
```

Common error codes:
- `validation_error` (422)
- `not_found` (404)
- `unauthorized` (401)
- `rate_limited` (429)
- `internal_error` (500)
```

### Step 1.3: Create Operator Runbooks

Create `docs/runbooks/COMMON_OPERATIONS.md`:

```markdown
# Common Operations Runbook

## Service Management

### Start All Services

```bash
# Ubuntu 1
sudo systemctl start fastapi-media
sudo systemctl start n8n

# Ubuntu 2
sudo systemctl start reachy-gateway

# Jetson
sudo systemctl start reachy-emotion
```

### Stop All Services

```bash
# Reverse order
ssh reachy@10.0.4.150 "sudo systemctl stop reachy-emotion"
sudo systemctl stop reachy-gateway
ssh admin@10.0.4.130 "sudo systemctl stop fastapi-media n8n"
```

### Check Service Status

```bash
# Quick health check
curl http://10.0.4.130:8083/health
curl http://10.0.4.140:8000/health
ssh reachy@10.0.4.150 "systemctl is-active reachy-emotion"
```

## Database Operations

### Backup Database

```bash
pg_dump -h 10.0.4.130 -U reachy_dev reachy_emotion > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
psql -h 10.0.4.130 -U reachy_dev reachy_emotion < backup_20250128.sql
```

### Check Dataset Stats

```sql
SELECT split, label, COUNT(*) 
FROM video 
GROUP BY split, label 
ORDER BY split, label;
```

## Model Operations

### Deploy New Model

1. Export ONNX from training:
   ```bash
   python trainer/train_efficientnet.py --export-only --checkpoint best_model.pt
   ```

2. Transfer to Jetson:
   ```bash
   scp model.onnx reachy@10.0.4.150:/opt/reachy/models/onnx/
   ```

3. Build TensorRT engine:
   ```bash
   ssh reachy@10.0.4.150 "python3 /opt/reachy/build_engine.py --onnx /opt/reachy/models/onnx/model.onnx"
   ```

4. Validate Gate B:
   ```bash
   ssh reachy@10.0.4.150 "python3 /opt/reachy/gate_b_validator.py --engine /opt/reachy/models/engines/emotion_efficientnet.engine"
   ```

5. Restart DeepStream:
   ```bash
   ssh reachy@10.0.4.150 "sudo systemctl restart reachy-emotion"
   ```

### Rollback Model

```bash
ssh reachy@10.0.4.150 "python3 /opt/reachy/rollback.py --latest"
```

## Troubleshooting

### Service Won't Start

1. Check logs:
   ```bash
   journalctl -u fastapi-media -n 100
   ```

2. Check port availability:
   ```bash
   netstat -tlnp | grep 8083
   ```

3. Check dependencies:
   ```bash
   systemctl status postgresql
   ```

### High Latency

1. Check system load:
   ```bash
   top -bn1 | head -20
   ```

2. Check GPU utilization (Jetson):
   ```bash
   tegrastats
   ```

3. Check network:
   ```bash
   ping -c 5 10.0.4.130
   ```

### Database Connection Issues

1. Check PostgreSQL status:
   ```bash
   systemctl status postgresql
   ```

2. Check connections:
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   ```

3. Check credentials:
   ```bash
   psql -h 10.0.4.130 -U reachy_dev -d reachy_emotion -c "SELECT 1"
   ```

## Monitoring

### View Prometheus Metrics

```bash
curl http://10.0.4.130:9090/api/v1/query?query=up
```

### Check Error Rates

```bash
curl 'http://10.0.4.130:9090/api/v1/query?query=rate(reachy_ingest_total{status="error"}[5m])'
```

### View Grafana Dashboards

Open: http://10.0.4.130:3000

Default credentials: admin/admin
```

### Checkpoint: Day 1 Complete
- [ ] README updated
- [ ] API reference created
- [ ] Operator runbooks created

---

## Day 2: Security Hardening

### Step 2.1: Implement JWT Authentication

Create `apps/api/auth/jwt_handler.py`:

```python
"""
JWT Authentication Handler

Implements token-based authentication for API endpoints.
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import logging

logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

security = HTTPBearer()


def create_token(
    user_id: str,
    roles: list = None,
    expires_delta: timedelta = None
) -> str:
    """
    Create a JWT token.
    
    Args:
        user_id: User identifier
        roles: List of user roles
        expires_delta: Token expiration time
    
    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=JWT_EXPIRATION_HOURS)
    
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        "sub": user_id,
        "roles": roles or [],
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return token


def decode_token(token: str) -> Dict:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Token payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict:
    """
    FastAPI dependency to get current authenticated user.
    
    Args:
        credentials: HTTP Bearer credentials
    
    Returns:
        User payload from token
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    return {
        "user_id": payload.get("sub"),
        "roles": payload.get("roles", []),
    }


def require_role(required_role: str):
    """
    Dependency factory for role-based access control.
    
    Args:
        required_role: Role required to access endpoint
    
    Returns:
        Dependency function
    """
    async def role_checker(user: Dict = Depends(get_current_user)):
        if required_role not in user.get("roles", []):
            raise HTTPException(
                status_code=403,
                detail=f"Role '{required_role}' required"
            )
        return user
    
    return role_checker


# Pre-defined role dependencies
require_admin = require_role("admin")
require_operator = require_role("operator")
require_viewer = require_role("viewer")
```

### Step 2.2: Add Rate Limiting

Create `apps/api/middleware/rate_limit.py`:

```python
"""
Rate Limiting Middleware

Implements request rate limiting to prevent abuse.
"""

import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_buckets: Dict[str, list] = defaultdict(list)
        self.hour_buckets: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, client_id: str) -> Tuple[bool, str]:
        """
        Check if request is allowed for client.
        
        Args:
            client_id: Client identifier (IP or user ID)
        
        Returns:
            Tuple of (allowed, reason)
        """
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600
        
        # Clean old entries
        self.minute_buckets[client_id] = [
            t for t in self.minute_buckets[client_id] if t > minute_ago
        ]
        self.hour_buckets[client_id] = [
            t for t in self.hour_buckets[client_id] if t > hour_ago
        ]
        
        # Check limits
        if len(self.minute_buckets[client_id]) >= self.requests_per_minute:
            return False, "Rate limit exceeded (per minute)"
        
        if len(self.hour_buckets[client_id]) >= self.requests_per_hour:
            return False, "Rate limit exceeded (per hour)"
        
        # Record request
        self.minute_buckets[client_id].append(now)
        self.hour_buckets[client_id].append(now)
        
        return True, ""


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        exclude_paths: list = None
    ):
        super().__init__(app)
        self.limiter = RateLimiter(requests_per_minute, requests_per_hour)
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Get client identifier
        client_id = self.get_client_id(request)
        
        # Check rate limit
        allowed, reason = self.limiter.is_allowed(client_id)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_id}: {reason}")
            raise HTTPException(
                status_code=429,
                detail=reason,
                headers={"Retry-After": "60"}
            )
        
        return await call_next(request)
    
    def get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        # Try to get user ID from auth header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from ..auth.jwt_handler import decode_token
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                return f"user:{payload.get('sub', 'unknown')}"
            except:
                pass
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        return f"ip:{request.client.host}"
```

### Step 2.3: Add Security Headers

Create `apps/api/middleware/security_headers.py`:

```python
"""
Security Headers Middleware

Adds security headers to all responses.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses."""
    
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Remove server header
        if "server" in response.headers:
            del response.headers["server"]
        
        return response
```

### Step 2.4: Apply Security Middleware

Update `apps/api/main.py`:

```python
from .middleware.rate_limit import RateLimitMiddleware
from .middleware.security_headers import SecurityHeadersMiddleware

# Add middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,
    requests_per_hour=1000,
    exclude_paths=["/health", "/metrics", "/docs", "/openapi.json"]
)
```

### Checkpoint: Day 2 Complete
- [ ] JWT authentication implemented
- [ ] Rate limiting added
- [ ] Security headers configured
- [ ] Middleware applied

---

## Day 3: Error Handling Review

### Step 3.1: Create Global Exception Handler

Create `apps/api/exceptions.py`:

```python
"""
Global Exception Handlers

Provides consistent error responses across the API.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback
import uuid

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "internal_error",
        status_code: int = 500,
        details: dict = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    """Resource not found."""
    
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} not found: {resource_id}",
            error_code="not_found",
            status_code=404,
            details={"resource": resource, "id": resource_id}
        )


class ValidationError(AppException):
    """Validation error."""
    
    def __init__(self, message: str, fields: dict = None):
        super().__init__(
            message=message,
            error_code="validation_error",
            status_code=422,
            details={"fields": fields or {}}
        )


class AuthenticationError(AppException):
    """Authentication failed."""
    
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code="unauthorized",
            status_code=401
        )


class AuthorizationError(AppException):
    """Authorization failed."""
    
    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message=message,
            error_code="forbidden",
            status_code=403
        )


def setup_exception_handlers(app: FastAPI):
    """Configure exception handlers for the app."""
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        correlation_id = str(uuid.uuid4())
        
        logger.error(
            f"AppException: {exc.error_code} - {exc.message}",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "details": exc.details,
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "correlation_id": correlation_id,
                "details": exc.details,
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        correlation_id = str(uuid.uuid4())
        
        # Extract field errors
        fields = {}
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            fields[field] = error["msg"]
        
        logger.warning(
            f"Validation error: {fields}",
            extra={"correlation_id": correlation_id, "path": request.url.path}
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "Request validation failed",
                "correlation_id": correlation_id,
                "fields": fields,
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        correlation_id = str(uuid.uuid4())
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": exc.detail,
                "correlation_id": correlation_id,
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        correlation_id = str(uuid.uuid4())
        
        logger.exception(
            f"Unhandled exception: {exc}",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "traceback": traceback.format_exc(),
            }
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
                "correlation_id": correlation_id,
            }
        )
```

### Step 3.2: Apply Exception Handlers

Update `apps/api/main.py`:

```python
from .exceptions import setup_exception_handlers

# After app creation
setup_exception_handlers(app)
```

### Step 3.3: Review Error Handling in Routers

Audit each router for proper error handling:

```python
# Example pattern for routers
from ..exceptions import NotFoundError, ValidationError

@router.get("/{video_id}")
async def get_video(video_id: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.video_id == video_id).first()
    
    if not video:
        raise NotFoundError("Video", video_id)
    
    return video
```

### Checkpoint: Day 3 Complete
- [ ] Global exception handlers created
- [ ] Consistent error format implemented
- [ ] All routers reviewed
- [ ] Correlation IDs added

---

## Day 4: Final Regression Testing

### Step 4.1: Create Regression Test Suite

Create `tests/regression/run_regression.py`:

```python
#!/usr/bin/env python3
"""
Regression Test Suite

Runs all tests to verify system stability before release.
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_test_suite(name: str, command: list) -> dict:
    """Run a test suite and return results."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Running: {name}")
    logger.info("=" * 60)
    
    start_time = datetime.now()
    
    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )
    
    duration = (datetime.now() - start_time).total_seconds()
    
    return {
        "name": name,
        "passed": result.returncode == 0,
        "duration_seconds": duration,
        "stdout": result.stdout[-2000:] if result.stdout else "",
        "stderr": result.stderr[-1000:] if result.stderr else "",
    }


def main():
    logger.info("=" * 60)
    logger.info("REGRESSION TEST SUITE")
    logger.info(f"Started: {datetime.now().isoformat()}")
    logger.info("=" * 60)
    
    test_suites = [
        ("Unit Tests", ["pytest", "tests/", "-v", "--ignore=tests/e2e", "--ignore=tests/regression", "-x"]),
        ("API Tests", ["pytest", "tests/apps/api/", "-v"]),
        ("Integration Tests", ["pytest", "tests/test_integration_full.py", "-v"]),
        ("E2E Tests", ["python", "tests/e2e/run_e2e_test.py"]),
        ("Performance Benchmarks", ["python", "tests/e2e/benchmark_performance.py"]),
    ]
    
    results = []
    
    for name, command in test_suites:
        result = run_test_suite(name, command)
        results.append(result)
        
        status = "✅ PASSED" if result["passed"] else "❌ FAILED"
        logger.info(f"{status} ({result['duration_seconds']:.1f}s)")
        
        if not result["passed"]:
            logger.error(f"Errors:\n{result['stderr']}")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("REGRESSION TEST SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    
    for result in results:
        status = "✅" if result["passed"] else "❌"
        logger.info(f"  {status} {result['name']} ({result['duration_seconds']:.1f}s)")
    
    logger.info(f"\nTotal: {passed}/{total} passed")
    
    all_passed = passed == total
    
    # Save results
    output_path = Path("outputs/regression") / f"regression_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "all_passed": all_passed,
            "results": results,
        }, f, indent=2)
    
    logger.info(f"\nResults saved to: {output_path}")
    
    if all_passed:
        logger.info("\n✅ ALL REGRESSION TESTS PASSED - Ready for release!")
    else:
        logger.error("\n❌ REGRESSION TESTS FAILED - Fix issues before release")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
```

### Step 4.2: Run Regression Tests

```bash
python tests/regression/run_regression.py
```

### Step 4.3: Fix Any Failures

Address any test failures before proceeding to release.

### Checkpoint: Day 4 Complete
- [ ] Regression test suite created
- [ ] All tests executed
- [ ] Failures addressed
- [ ] Results documented

---

## Day 5: Beta Release

### Step 5.1: Create Release Checklist

Create `RELEASE_CHECKLIST.md`:

```markdown
# Release Checklist - v0.08.5-beta

## Pre-Release

- [ ] All regression tests passing
- [ ] Documentation updated
- [ ] Security review complete
- [ ] Performance benchmarks meet SLA
- [ ] Gate A validation passing
- [ ] Gate B validation passing

## Code Quality

- [ ] No critical security vulnerabilities
- [ ] No deprecated dependencies
- [ ] Code coverage > 80%
- [ ] Linting passes

## Documentation

- [ ] README updated
- [ ] API reference complete
- [ ] Operator runbooks created
- [ ] CHANGELOG updated

## Infrastructure

- [ ] Database migrations tested
- [ ] Backup procedures verified
- [ ] Rollback procedures documented
- [ ] Monitoring dashboards configured

## Release Steps

1. [ ] Create release branch
2. [ ] Update version numbers
3. [ ] Generate CHANGELOG
4. [ ] Create release tag
5. [ ] Build release artifacts
6. [ ] Deploy to staging
7. [ ] Smoke test staging
8. [ ] Deploy to production
9. [ ] Verify production health
10. [ ] Announce release

## Post-Release

- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Gather user feedback
- [ ] Plan next iteration
```

### Step 5.2: Update Version Numbers

Update version in key files:

```bash
# Update pyproject.toml
sed -i 's/version = ".*"/version = "0.08.5-beta"/' pyproject.toml

# Update memory-bank/requirements.md
sed -i 's/Version: .*/Version: 0.08.5-beta/' memory-bank/requirements.md
```

### Step 5.3: Create CHANGELOG

Create `CHANGELOG.md`:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [0.08.5-beta] - 2025-01-28

### Added
- Complete statistical analysis toolkit (Phase 1)
  - Quality gate metrics with ECE/Brier calibration
  - Stuart-Maxwell test for model comparison
  - Per-class paired t-tests with BH correction
  - Bootstrap confidence intervals
- Training pipeline integration
  - Gate A validation in training workflow
  - Post-training statistical analysis
  - MLflow integration for stats logging
- n8n workflow automation
  - All 10 agents implemented and tested
  - Webhook integration with FastAPI gateway
- Jetson deployment automation
  - TensorRT engine build script
  - Gate B validation
  - Automatic rollback on failure
- Observability
  - Prometheus metrics endpoints
  - Grafana dashboards
  - Alert rules for key metrics
- Security hardening
  - JWT authentication
  - Rate limiting
  - Security headers

### Changed
- Updated EfficientNet-B0 model architecture for 2-class (happy/sad) classification
- Improved error handling with consistent error format
- Enhanced documentation with tutorials and runbooks

### Fixed
- JSON serialization of NumPy types in stats scripts
- Database connection handling in high-load scenarios
- WebSocket reconnection logic in Jetson client

### Security
- Added rate limiting to prevent abuse
- Implemented JWT token authentication
- Added security headers to all responses

## [0.08.4.2] - 2025-10-16

### Added
- Initial agentic AI system integration
- Enhanced privacy controls
- Deployment gates (Gate A, Gate B, Gate C)

## [0.08.3.3] - 2025-10-06

### Added
- TAO container/image version pinning
- Workspace mounts and environment documentation
- Canonical storage root on Ubuntu 1
```

### Step 5.4: Create Release Tag

```bash
# Ensure all changes are committed
git add -A
git commit -m "Prepare v0.08.5-beta release"

# Create annotated tag
git tag -a v0.08.5-beta -m "Beta release v0.08.5

Features:
- Complete statistical analysis toolkit
- Training pipeline integration
- n8n workflow automation
- Jetson deployment automation
- Observability and monitoring
- Security hardening

See CHANGELOG.md for details."

# Push tag
git push origin v0.08.5-beta
```

### Step 5.5: Final Verification

```bash
# Verify all services
curl http://10.0.4.130:8083/health
curl http://10.0.4.140:8000/health

# Check version
curl http://10.0.4.140:8000/health | jq '.version'

# Run smoke test
python tests/e2e/run_e2e_test.py --test-id release_smoke_test
```

### Checkpoint: Day 5 Complete
- [ ] Release checklist completed
- [ ] Version numbers updated
- [ ] CHANGELOG created
- [ ] Release tag created
- [ ] Final verification passed

---

## Week 8 Deliverables Summary

| Deliverable | Status | Location |
|-------------|--------|----------|
| Updated README | ✅ | `README.md` |
| API Reference | ✅ | `docs/API_REFERENCE.md` |
| Operator Runbooks | ✅ | `docs/runbooks/` |
| JWT Authentication | ✅ | `apps/api/auth/jwt_handler.py` |
| Rate Limiting | ✅ | `apps/api/middleware/rate_limit.py` |
| Exception Handlers | ✅ | `apps/api/exceptions.py` |
| Regression Tests | ✅ | `tests/regression/` |
| CHANGELOG | ✅ | `CHANGELOG.md` |
| Release Tag | ✅ | `v0.08.5-beta` |

---

## 8-Week Implementation Complete! 🎉

Congratulations, Russ! You have completed the 8-week implementation plan for the Reachy Emotion Recognition project.

### Summary of Achievements

| Week | Focus | Key Deliverables |
|------|-------|------------------|
| 1 | Statistical Analysis | ECE/Brier metrics, orchestrator, MLflow integration |
| 2 | Training Pipeline | Pre-trained weights, Gate A validation, post-training analysis |
| 3 | n8n Workflows | Ingest, Labeling, Promotion agents tested, webhooks |
| 4 | Web UI & Reconciler | Dataset overview, training dashboard, dry-run mode |
| 5 | Jetson Deployment | Engine build, Gate B validation, rollback mechanism |
| 6 | Privacy & Observability | Privacy agent, Prometheus metrics, stress testing |
| 7 | E2E Testing | Full pipeline test, LLM integration, performance benchmarks |
| 8 | Release | Documentation, security hardening, Beta release |

### Next Steps

1. **Monitor Beta** - Watch error rates and performance in production
2. **Gather Feedback** - Collect user feedback for improvements
3. **Plan v0.09** - Define features for next major version
4. **Production Release** - Target May 2026 for production release

Good luck with the Beta release! 🚀
