# Week 2: Environment Setup & Configuration

**Duration**: ~6 hours  
**Goal**: Set up a fully functional local development environment  
**Prerequisites**: Week 1 completed, Python 3.10+ installed

---

## Day 1: Python Environment Setup (2 hours)

### 1.1 Create Virtual Environment

```bash
# Navigate to project root
cd d:\projects\reachy_emotion

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
# source venv/bin/activate

# Verify Python version
python --version
# Expected: Python 3.10.x or higher
```

### 1.2 Install Dependencies

The project uses two requirement files for different phases:

```bash
# Install Phase 1 dependencies (core)
pip install -r requirements-phase1.txt

# Install Phase 2 dependencies (ML/advanced features)
pip install -r requirements-phase2.txt

# Install development dependencies
pip install pytest pytest-cov pytest-asyncio black flake8
```

**Key packages installed:**

| Package | Purpose | Version |
|---------|---------|---------|
| fastapi | REST API framework | ≥0.100.0 |
| uvicorn | ASGI server | ≥0.23.0 |
| streamlit | Web UI framework | ≥1.28.0 |
| httpx | Async HTTP client | ≥0.24.0 |
| pydantic | Data validation | ≥2.0.0 |
| sqlalchemy | Database ORM | ≥2.0.0 |
| python-dotenv | Environment variables | ≥1.0.0 |

### 1.3 Verify Installation

```bash
# Test Streamlit
streamlit --version
# Expected: Streamlit, version 1.28.x

# Test FastAPI
python -c "import fastapi; print(fastapi.__version__)"
# Expected: 0.100.x or higher

# Test pytest
pytest --version
# Expected: pytest 7.x.x
```

### Checkpoint 2.1
- [ ] Virtual environment created and activated
- [ ] All dependencies installed without errors
- [ ] Version checks pass for Streamlit, FastAPI, pytest

---

## Day 2: Environment Configuration (2 hours)

### 2.1 Understanding Configuration Files

The application uses environment variables for configuration. Template files are provided:

```
apps/web/.env.template      # Web UI configuration
apps/api/.env.template      # Media Mover API configuration
apps/gateway/.env.template  # Gateway configuration
```

### 2.2 Configure Web UI

```bash
# Navigate to web app directory
cd apps/web

# Copy template to create your .env
copy .env.template .env
```

Open `apps/web/.env` and configure:

```ini
# apps/web/.env

# API Configuration
# Media Mover API on Ubuntu 1
REACHY_API_BASE=http://10.0.4.130:8083

# Gateway on Ubuntu 2 (or localhost for local dev)
REACHY_GATEWAY_BASE=http://10.0.4.140:8000

# Authentication (optional for development)
REACHY_API_TOKEN=

# Luma AI Configuration (for video generation)
LUMAAI_API_KEY=

# n8n Webhook Configuration
N8N_HOST=10.0.4.130
N8N_PORT=5678
N8N_WEBHOOK_PATH=webhook/video_gen_hook
N8N_INGEST_TOKEN=
```

### 2.3 Understanding Environment Variables

Each variable controls a specific aspect:

| Variable | Purpose | Default |
|----------|---------|---------|
| `REACHY_API_BASE` | Media Mover API URL | `http://localhost:8083` |
| `REACHY_GATEWAY_BASE` | Gateway proxy URL | `http://localhost:8000` |
| `REACHY_API_TOKEN` | Bearer token for auth | (empty) |
| `LUMAAI_API_KEY` | Luma AI video generation | (empty) |
| `N8N_HOST` | n8n server address | `10.0.4.130` |

### 2.4 Local Development Configuration

For **local development without network access** to Ubuntu servers:

```ini
# apps/web/.env (local development)

REACHY_API_BASE=http://localhost:8083
REACHY_GATEWAY_BASE=http://localhost:8000
REACHY_API_TOKEN=dev-token-12345
```

This requires running the API locally (covered in Week 3).

### Checkpoint 2.2
- [ ] `.env` file created in `apps/web/`
- [ ] Environment variables configured for your environment
- [ ] Understand difference between API_BASE and GATEWAY_BASE

---

## Day 3: Running the Application (2 hours)

### 3.1 Running Streamlit Locally

```bash
# Ensure you're in project root with venv activated
cd d:\projects\reachy_emotion

# Run Streamlit
streamlit run apps/web/main_app.py

# Expected output:
#   You can now view your Streamlit app in your browser.
#   Local URL: http://localhost:8501
#   Network URL: http://192.168.x.x:8501
```

Open `http://localhost:8501` in your browser.

### 3.2 Exploring the UI

With the app running, explore each page:

1. **Home** (`00_Home.py`)
   - Video upload section
   - Video generation section
   - Classification section

2. **Generate** (`01_Generate.py`)
   - Minimal placeholder UI

3. **Label** (`02_Label.py`)
   - Video listing with filters
   - Promotion dry-run functionality

4. **Train** (`03_Train.py`)
   - Placeholder with manifest rebuild button

5. **Deploy** (`04_Deploy.py`)
   - Stub page (needs implementation)

6. **Video Management** (`05_Video_Management.py`)
   - Batch selection and operations

### 3.3 Testing API Connectivity

If the API is accessible, test connectivity:

```bash
# Test Media Mover health endpoint
curl http://10.0.4.130:8083/api/v1/health

# Expected response:
# {"status":"ok","version":"0.08.4.3",...}

# Test Gateway health
curl http://10.0.4.140:8000/health

# Expected response:
# {"status":"healthy",...}
```

If APIs are not accessible, you'll see error messages in the Streamlit UI. This is expected for local development without network access.

### 3.4 Running with Mock Data (Optional)

For development without API access, you can create a mock API client:

```python
# apps/web/api_client_mock.py (create this file)

def list_videos(split: str, limit: int = 50, offset: int = 0):
    """Mock video listing for offline development."""
    return {
        "items": [
            {
                "video_id": "mock-001",
                "file_path": f"videos/{split}/sample_001.mp4",
                "label": "happy" if split == "train" else None,
                "size_bytes": 1024000,
                "mtime": "2026-01-01T12:00:00Z"
            },
            {
                "video_id": "mock-002",
                "file_path": f"videos/{split}/sample_002.mp4",
                "label": "sad" if split == "train" else None,
                "size_bytes": 2048000,
                "mtime": "2026-01-02T12:00:00Z"
            }
        ],
        "total": 2,
        "limit": limit,
        "offset": offset,
        "has_more": False
    }

def upload_video(file_name, file_bytes, upload_for_training, correlation_id):
    """Mock video upload."""
    return {
        "video_id": f"mock-{correlation_id[:8]}",
        "file_path": f"videos/temp/{file_name}",
        "status": "success"
    }

def promote(video_id, dest_split, label=None, dry_run=False, **kwargs):
    """Mock video promotion."""
    return {
        "status": "success" if not dry_run else "dry_run",
        "video_id": video_id,
        "from_split": "temp",
        "to_split": dest_split,
        "label": label
    }
```

### Checkpoint 2.3
- [ ] Streamlit app runs locally without errors
- [ ] Can navigate between all pages
- [ ] Understand which features require API connectivity
- [ ] (Optional) Created mock API client for offline development

---

## IDE Configuration

### VS Code Setup

Create `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/venv/Scripts/python.exe",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "editor.formatOnSave": true,
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter"
    }
}
```

Create `.vscode/launch.json` for debugging:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Streamlit",
            "type": "python",
            "request": "launch",
            "module": "streamlit",
            "args": ["run", "apps/web/main_app.py"],
            "cwd": "${workspaceFolder}"
        },
        {
            "name": "FastAPI (Media Mover)",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": ["apps.api.app.main:app", "--reload", "--port", "8083"],
            "cwd": "${workspaceFolder}"
        },
        {
            "name": "Gateway",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": ["apps.gateway.main:app", "--reload", "--port", "8000"],
            "cwd": "${workspaceFolder}"
        },
        {
            "name": "pytest",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["-v"],
            "cwd": "${workspaceFolder}"
        }
    ]
}
```

### PyCharm Setup

1. **Set Project Interpreter**: `File > Settings > Project > Python Interpreter`
   - Select the `venv` Python interpreter

2. **Configure Run Configurations**:
   - Streamlit: Script path = `streamlit`, Parameters = `run apps/web/main_app.py`
   - FastAPI: Module = `uvicorn`, Parameters = `apps.api.app.main:app --reload`

---

## Troubleshooting Common Issues

### Issue: ModuleNotFoundError

```
ModuleNotFoundError: No module named 'apps'
```

**Solution**: Ensure you're running from project root and PYTHONPATH is set:

```bash
# Windows
set PYTHONPATH=%cd%
streamlit run apps/web/main_app.py

# Linux/Mac
export PYTHONPATH=$(pwd)
streamlit run apps/web/main_app.py
```

### Issue: Connection Refused

```
requests.exceptions.ConnectionError: Connection refused
```

**Solution**: The API server is not running or not accessible. Options:
1. Connect to network with access to 10.0.4.x
2. Run API locally (Week 3)
3. Use mock API client

### Issue: Port Already in Use

```
OSError: [Errno 48] Address already in use
```

**Solution**: Kill existing process or use different port:

```bash
# Find process using port 8501
netstat -ano | findstr :8501

# Kill the process
taskkill /PID <pid> /F

# Or run on different port
streamlit run apps/web/main_app.py --server.port 8502
```

### Issue: Import Errors in IDE

**Solution**: Configure the Python interpreter path in your IDE to use the project's `venv`.

---

## Week 2 Deliverables Checklist

- [ ] Virtual environment created and activated
- [ ] All dependencies installed successfully
- [ ] `.env` file configured for development
- [ ] Streamlit app runs locally
- [ ] IDE configured for debugging
- [ ] Understand troubleshooting steps

---

## Verification Commands

Run these commands to verify your setup:

```bash
# 1. Verify venv is active
python -c "import sys; print(sys.prefix)"
# Should show path to your venv

# 2. Verify key packages
python -c "import streamlit, fastapi, pydantic; print('OK')"
# Should print: OK

# 3. Verify .env is loaded
python -c "from dotenv import load_dotenv; load_dotenv('apps/web/.env'); import os; print(os.getenv('REACHY_API_BASE', 'NOT SET'))"
# Should print your configured URL

# 4. Run Streamlit
streamlit run apps/web/main_app.py --server.headless true
# Should start without errors
```

---

## Next Steps

Proceed to [Week 3: FastAPI Backend Development](WEEK_03_FASTAPI_BACKEND.md) to learn how to:
- Create new API endpoints
- Understand router patterns
- Work with Pydantic schemas
- Connect to the database
