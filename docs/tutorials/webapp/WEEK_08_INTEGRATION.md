# Week 8: Integration & Production Readiness

**Duration**: ~6 hours  
**Goal**: Complete integration testing and prepare for production deployment  
**Prerequisites**: Weeks 1-7 completed, all tests passing

---

## Day 1: Final Integration Testing (2 hours)

### 1.1 Integration Test Checklist

Before production release, verify all components work together:

```
┌─────────────────────────────────────────────────────────────────┐
│                 Integration Test Matrix                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Component A          Component B          Test Status          │
│  ─────────────        ─────────────        ───────────          │
│  Streamlit UI    ───▶  Gateway        [  ] Connectivity        │
│  Gateway         ───▶  Media Mover    [  ] Proxy working       │
│  Media Mover     ───▶  PostgreSQL     [  ] DB operations       │
│  Media Mover     ───▶  File Storage   [  ] File I/O            │
│  Training Page   ───▶  MLflow         [  ] Metrics fetch       │
│  Deploy Page     ───▶  Jetson         [  ] Status check        │
│  WebSocket       ───▶  Real-time      [  ] Event delivery      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Run Full Integration Test Suite

```bash
# Set environment for integration tests
export REACHY_API_BASE=http://10.0.4.130:8083
export REACHY_GATEWAY_BASE=http://10.0.4.140:8000
export INTEGRATION_TEST=true

# Run integration tests
pytest tests/ -v -m "integration" --tb=short

# Run E2E tests
pytest tests/test_e2e_complete.py -v

# Run with all tests including slow ones
pytest tests/ -v --run-slow
```

### 1.3 Manual Integration Verification

Perform these manual checks:

#### UI → API Flow
```bash
# 1. Start Streamlit
streamlit run apps/web/main_app.py

# 2. Open browser to http://localhost:8501

# 3. Navigate to each page and verify:
#    - Home: Can upload video
#    - Generate: Form displays correctly
#    - Label: Videos list loads
#    - Train: Dataset stats display
#    - Deploy: Jetson status shows
#    - Video Management: Batch operations work
```

#### API Endpoint Verification
```bash
# Health check
curl -s http://10.0.4.130:8083/api/v1/health | jq .

# List videos
curl -s "http://10.0.4.130:8083/api/v1/media/list?split=temp&limit=5" | jq .

# Check manifest
curl -s http://10.0.4.130:8083/manifest/status | jq .
```

### Checkpoint 8.1
- [ ] All integration tests pass
- [ ] Manual verification completed
- [ ] No critical bugs identified

---

## Day 2: Documentation & Code Review (2 hours)

### 2.1 Code Documentation

Ensure all new code has proper docstrings:

```python
# Example of required documentation

def promote_video(
    video_id: str,
    dest_split: str,
    label: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Promote a video from temp to training or test split.
    
    This function moves a video file from the temp staging area to
    the designated split directory and updates the database record
    with the new location and optional label.
    
    Args:
        video_id: Unique identifier of the video to promote.
        dest_split: Target split ('train', 'test', or 'dataset_all').
        label: Emotion label to assign (required for 'train' split).
        dry_run: If True, validate without executing the move.
    
    Returns:
        Dictionary containing:
            - status: 'success' or 'dry_run'
            - video_id: The promoted video ID
            - from_split: Original split ('temp')
            - to_split: Destination split
            - file_path_before: Original file path
            - file_path_after: New file path
    
    Raises:
        ValueError: If label is missing for train split promotion.
        FileNotFoundError: If video file doesn't exist.
        HTTPError: If API call fails.
    
    Example:
        >>> result = promote_video('vid-123', 'train', label='happy')
        >>> print(result['status'])
        'success'
    """
```

### 2.2 Update README

Update `apps/web/README.md`:

```markdown
# Reachy Emotion Web Application

## Overview

Streamlit-based web interface for the Reachy Emotion Recognition system.

## Features

- **Video Upload**: Upload videos for emotion labeling
- **Video Generation**: Generate synthetic training videos via Luma AI
- **Labeling Interface**: Browse and label videos with emotions
- **Training Dashboard**: Monitor training jobs and Gate A validation
- **Deployment Controls**: Manage Jetson edge deployments
- **Batch Operations**: Bulk video management operations

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.template .env
# Edit .env with your settings

# 3. Run the application
streamlit run main_app.py
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REACHY_API_BASE` | Media Mover API URL | `http://localhost:8083` |
| `REACHY_GATEWAY_BASE` | Gateway URL | `http://localhost:8000` |
| `REACHY_API_TOKEN` | Authentication token | (empty) |
| `LUMAAI_API_KEY` | Luma AI API key | (empty) |

## Pages

1. **Home** (`00_Home.py`) - Main video workflow
2. **Generate** (`01_Generate.py`) - Video generation interface
3. **Label** (`02_Label.py`) - Video labeling with dry-run promotion
4. **Train** (`03_Train.py`) - Training dashboard with Gate A validation
5. **Deploy** (`04_Deploy.py`) - Jetson deployment management
6. **Video Management** (`05_Video_Management.py`) - Batch operations

## Architecture

```
apps/web/
├── main_app.py          # Application entry point
├── api_client.py        # HTTP client for API calls
├── session_manager.py   # Streamlit session state
├── websocket_client.py  # Real-time event handling
├── pages/               # Multi-page application
└── components/          # Reusable UI components
```

## Testing

```bash
pytest tests/test_web_ui.py -v
pytest tests/apps/test_streamlit_pages.py -v
```

## Contributing

1. Follow existing code style (Black, flake8)
2. Add tests for new features
3. Update documentation as needed
```

### 2.3 API Documentation

Verify OpenAPI docs are complete:

```bash
# Start API server
uvicorn apps.api.app.main:app --port 8083

# Access Swagger UI
# Open http://localhost:8083/docs

# Verify all endpoints have:
# - Summary descriptions
# - Parameter documentation
# - Response schemas
# - Example values
```

### Checkpoint 8.2
- [ ] All functions have docstrings
- [ ] README updated
- [ ] OpenAPI docs complete

---

## Day 3: Security & Production Prep (2 hours)

### 3.1 Security Checklist

```
┌─────────────────────────────────────────────────────────────────┐
│                    Security Checklist                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [  ] No hardcoded credentials in code                         │
│  [  ] API tokens loaded from environment only                  │
│  [  ] .env files in .gitignore                                 │
│  [  ] CORS configured for production origins                   │
│  [  ] Input validation on all endpoints                        │
│  [  ] File upload size limits enforced                         │
│  [  ] SQL injection prevented (parameterized queries)          │
│  [  ] XSS prevention (no raw HTML from user input)             │
│  [  ] Rate limiting configured (if applicable)                 │
│  [  ] HTTPS enforced in production                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Security Scan

```bash
# Install security scanning tools
pip install bandit safety

# Run bandit security scan
bandit -r apps/ -ll

# Check for vulnerable dependencies
safety check -r requirements-phase1.txt
safety check -r requirements-phase2.txt
```

### 3.3 Environment Configuration for Production

Create `apps/web/.env.production`:

```ini
# Production environment configuration

# API Configuration - Use internal network addresses
REACHY_API_BASE=http://10.0.4.130:8083
REACHY_GATEWAY_BASE=http://10.0.4.140:8000

# Authentication
REACHY_API_TOKEN=${REACHY_API_TOKEN}

# Feature flags
ENABLE_DEBUG_MODE=false
ENABLE_DEV_TOOLS=false

# Logging
LOG_LEVEL=INFO

# Rate limiting
RATE_LIMIT_PER_MINUTE=60
```

### 3.4 Production Startup Script

Create `scripts/start_webapp.sh`:

```bash
#!/bin/bash
# Production startup script for Reachy Web Application

set -e

# Load production environment
export $(grep -v '^#' apps/web/.env.production | xargs)

# Verify required variables
if [ -z "$REACHY_API_BASE" ]; then
    echo "ERROR: REACHY_API_BASE not set"
    exit 1
fi

# Check API connectivity
echo "Checking API connectivity..."
curl -sf "${REACHY_API_BASE}/api/v1/health" > /dev/null || {
    echo "ERROR: Cannot reach API at ${REACHY_API_BASE}"
    exit 1
}

echo "API is reachable. Starting Streamlit..."

# Start Streamlit with production settings
streamlit run apps/web/main_app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection true \
    --browser.gatherUsageStats false \
    --logger.level info
```

### 3.5 Systemd Service File

Create `systemd/reachy-webapp.service`:

```ini
[Unit]
Description=Reachy Emotion Web Application
After=network.target

[Service]
Type=simple
User=reachy
Group=reachy
WorkingDirectory=/opt/reachy-emotion
Environment="PATH=/opt/reachy-emotion/venv/bin"
EnvironmentFile=/opt/reachy-emotion/apps/web/.env.production
ExecStart=/opt/reachy-emotion/venv/bin/streamlit run apps/web/main_app.py --server.port 8501 --server.headless true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Checkpoint 8.3
- [ ] Security checklist completed
- [ ] No critical vulnerabilities found
- [ ] Production environment configured
- [ ] Startup scripts created

---

## Final Verification

### Complete System Test

```bash
# 1. Start all services (on respective hosts)

# Ubuntu 1: Media Mover API
uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8083

# Ubuntu 2: Gateway
uvicorn apps.gateway.main:app --host 0.0.0.0 --port 8000

# Ubuntu 2: Web UI
streamlit run apps/web/main_app.py --server.port 8501

# 2. Run smoke tests
pytest tests/test_e2e_complete.py -v -k "smoke"

# 3. Verify all pages load
curl -s http://localhost:8501 | grep -q "Streamlit"
echo "Web UI: OK"
```

### Performance Baseline

```bash
# Measure API response times
for endpoint in "/api/v1/health" "/api/v1/media/list?split=temp&limit=10"; do
    echo "Testing $endpoint"
    curl -w "Time: %{time_total}s\n" -s -o /dev/null "http://10.0.4.130:8083$endpoint"
done
```

---

## Week 8 Deliverables Checklist

- [ ] All integration tests pass
- [ ] Manual testing completed on all pages
- [ ] Code documentation complete
- [ ] README files updated
- [ ] Security scan passed
- [ ] Production configuration created
- [ ] Startup scripts ready
- [ ] Systemd service file created
- [ ] Performance baseline documented

---

## Handoff Documentation

Create `docs/WEBAPP_HANDOFF.md`:

```markdown
# Web Application Handoff Document

## Project Status: COMPLETE ✓

### Implemented Features
- ✓ Home page with video upload and classification
- ✓ Generate page with prompt builder and templates
- ✓ Label page with dry-run promotion
- ✓ Train page with Gate A validation
- ✓ Deploy page with Gate B monitoring
- ✓ Video Management with batch operations

### Test Coverage
- Unit tests: XX%
- Integration tests: Pass
- E2E tests: Pass

### Known Limitations
1. Batch delete requires manual confirmation
2. Real-time WebSocket requires gateway connection
3. MLflow integration requires MLflow server running

### Operational Notes
- API must be running on 10.0.4.130:8083
- Gateway must be running on 10.0.4.140:8000
- Database must be accessible on 10.0.4.130:5432

### Support Contacts
- Technical Lead: [Name]
- DevOps: [Name]
- Documentation: docs/tutorials/webapp/
```

---

## Congratulations! 🎉

You have completed the 8-week Web Application Development Tutorial Series.

### Skills Acquired
- FastAPI backend development
- Streamlit frontend development
- API client design with retry logic
- Session state management
- Gate A/B validation implementation
- Comprehensive testing practices
- Production deployment preparation

### Next Steps
1. Review `docs/tutorials/` for n8n workflow tutorials
2. Explore `trainer/` for ML pipeline details
3. Study `jetson/` for edge deployment specifics

### Continuing Education
- FastAPI official documentation
- Streamlit component gallery
- MLflow tracking tutorials
- Kubernetes deployment for scaling

---

*Thank you for completing the tutorial series!*
