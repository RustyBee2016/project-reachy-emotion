# Web Application Development Tutorial Series

**Project**: Reachy Emotion Recognition  
**Team**: Web Application Development  
**Version**: 0.08.5  
**Duration**: 8 weeks (~48 hours)  
**Last Updated**: 2026-02-01

---

## Overview

This tutorial series provides step-by-step guidance for junior developers to understand, build, test, and extend the Reachy Emotion Recognition web application. The application consists of:

1. **FastAPI Backend** — RESTful API for media management, promotion, and ML pipeline integration
2. **Streamlit Frontend** — Interactive web UI for video labeling, training monitoring, and deployment control
3. **Gateway Service** — API proxy layer connecting frontend to backend services

---

## Application Status Analysis

### Fully Implemented Components ✅
| Component | Location | Status |
|-----------|----------|--------|
| Landing Page | `apps/web/landing_page.py` | Complete |
| Home Page | `apps/web/pages/00_Home.py` | Complete |
| Label Page | `apps/web/pages/02_Label.py` | Working |
| Video Management | `apps/web/pages/05_Video_Management.py` | Complete |
| API Client | `apps/web/api_client.py` | Complete |
| Session Manager | `apps/web/session_manager.py` | Complete |
| Media Mover API | `apps/api/app/main.py` | Complete |
| Gateway | `apps/gateway/main.py` | Complete |
| Promote Service | `apps/api/app/services/promote_service.py` | Complete |

### Components Requiring Development ⚠️
| Component | Location | Status | Week |
|-----------|----------|--------|------|
| Generate Page | `apps/web/pages/01_Generate.py` | Placeholder | Week 4 |
| Train Page | `apps/web/pages/03_Train.py` | Placeholder | Week 5 |
| Deploy Page | `apps/web/pages/04_Deploy.py` | Stub | Week 6 |
| Batch Delete | `05_Video_Management.py` | TODO | Week 4 |
| Batch Relabel | `05_Video_Management.py` | TODO | Week 4 |

---

## Weekly Tutorial Schedule

| Week | Focus Area | Hours | Key Deliverable |
|------|------------|-------|-----------------|
| 1 | [Project Overview & Architecture](WEEK_01_PROJECT_OVERVIEW.md) | 6 | Architecture understood |
| 2 | [Environment Setup & Configuration](WEEK_02_ENVIRONMENT_SETUP.md) | 6 | Dev environment running |
| 3 | [FastAPI Backend Development](WEEK_03_FASTAPI_BACKEND.md) | 6 | API endpoints tested |
| 4 | [Streamlit Frontend Development](WEEK_04_STREAMLIT_FRONTEND.md) | 6 | UI pages functional |
| 5 | [Training Dashboard Implementation](WEEK_05_TRAINING_DASHBOARD.md) | 6 | Training UI complete |
| 6 | [Deployment Controls & Monitoring](WEEK_06_DEPLOYMENT_CONTROLS.md) | 6 | Deploy UI complete |
| 7 | [Testing & Quality Assurance](WEEK_07_TESTING_QA.md) | 6 | 80%+ test coverage |
| 8 | [Integration & Production Readiness](WEEK_08_INTEGRATION.md) | 6 | App production-ready |

**Total**: ~48 hours over 8 weeks

---

## Prerequisites

### Technical Skills
- [ ] Python 3.10+ proficiency
- [ ] Basic understanding of HTTP/REST APIs
- [ ] Familiarity with HTML/CSS concepts
- [ ] Git version control basics

### Software Requirements
- [ ] Python 3.10+ installed
- [ ] PostgreSQL 16+ client tools
- [ ] Git
- [ ] VS Code or PyCharm (recommended)
- [ ] Postman or curl for API testing

### Environment Access
- [ ] Project repository cloned
- [ ] VPN access to development network (10.0.4.x)
- [ ] Database credentials for `reachy_dev` role

---

## Project Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Ubuntu 2 (10.0.4.140)                    │
│  ┌─────────────────┐    ┌─────────────────────────────────────┐ │
│  │   Streamlit UI  │───▶│        Gateway (Port 8000)          │ │
│  │   (Port 8501)   │    │   - Proxy to Media Mover            │ │
│  └─────────────────┘    │   - WebSocket connections           │ │
│                         └──────────────┬──────────────────────┘ │
└────────────────────────────────────────┼────────────────────────┘
                                         │
                    ┌────────────────────▼────────────────────────┐
                    │              Ubuntu 1 (10.0.4.130)          │
                    │  ┌─────────────────────────────────────────┐│
                    │  │    Media Mover API (Port 8083)          ││
                    │  │    - Video CRUD operations              ││
                    │  │    - Promotion service                  ││
                    │  │    - Thumbnail generation               ││
                    │  └─────────────────────────────────────────┘│
                    │  ┌─────────────────────────────────────────┐│
                    │  │    PostgreSQL (Port 5432)               ││
                    │  │    - Video metadata                     ││
                    │  │    - Labels and splits                  ││
                    │  │    - Promotion logs                     ││
                    │  └─────────────────────────────────────────┘│
                    │  ┌─────────────────────────────────────────┐│
                    │  │    File Storage (/media/project_data)   ││
                    │  │    - videos/temp/, train/, test/        ││
                    │  │    - thumbs/                            ││
                    │  └─────────────────────────────────────────┘│
                    └─────────────────────────────────────────────┘
```

---

## Directory Structure

```
apps/
├── api/                          # FastAPI Media Mover
│   ├── app/
│   │   ├── main.py              # Application entry point
│   │   ├── config.py            # Configuration management
│   │   ├── routers/             # API route handlers
│   │   │   ├── health.py        # Health check endpoints
│   │   │   ├── media_v1.py      # Media CRUD v1 API
│   │   │   ├── promote.py       # Promotion endpoints
│   │   │   ├── ingest.py        # File upload/ingest
│   │   │   └── dialogue.py      # LLM dialogue endpoints
│   │   ├── services/            # Business logic layer
│   │   │   ├── promote_service.py
│   │   │   └── thumbnail_watcher.py
│   │   └── schemas/             # Pydantic models
│   └── routers/                 # Legacy routers
│
├── gateway/                      # API Gateway for Ubuntu 2
│   ├── main.py                  # Gateway entry point
│   └── config.py                # Gateway configuration
│
└── web/                          # Streamlit Frontend
    ├── main_app.py              # Streamlit entry point
    ├── landing_page.py          # Full-featured landing page
    ├── api_client.py            # API client library
    ├── api_client_v2.py         # Enhanced API client
    ├── session_manager.py       # Session state management
    ├── websocket_client.py      # Real-time events
    ├── pages/                   # Streamlit pages
    │   ├── 00_Home.py           # Main video workflow
    │   ├── 01_Generate.py       # Video generation (placeholder)
    │   ├── 02_Label.py          # Labeling interface
    │   ├── 03_Train.py          # Training dashboard (placeholder)
    │   ├── 04_Deploy.py         # Deployment controls (stub)
    │   └── 05_Video_Management.py # Batch operations
    └── components/              # Reusable UI components
        ├── stats_panel.py
        └── video_player.py
```

---

## Quick Start

```bash
# 1. Clone and navigate to project
cd d:\projects\reachy_emotion

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements-phase1.txt
pip install -r requirements-phase2.txt

# 4. Configure environment
copy apps\web\.env.template apps\web\.env
# Edit .env with your settings

# 5. Run Streamlit app locally
streamlit run apps/web/main_app.py
```

---

## Learning Objectives

### By End of Week 2
- [ ] Understand the three-tier architecture (UI → Gateway → API)
- [ ] Set up local development environment
- [ ] Successfully run Streamlit app connecting to remote APIs

### By End of Week 4
- [ ] Create FastAPI endpoints with proper schemas
- [ ] Build Streamlit pages with session state management
- [ ] Implement form validation and error handling

### By End of Week 6
- [ ] Complete Training Dashboard implementation
- [ ] Complete Deployment Controls implementation
- [ ] Integrate WebSocket for real-time updates

### By End of Week 8
- [ ] Achieve 80%+ test coverage
- [ ] Pass all integration tests
- [ ] Document all new features

---

## Support Resources

| Resource | Location |
|----------|----------|
| API Reference | `docs/API_ENDPOINT_REFERENCE.md` |
| Database Schema | `docs/database/` |
| n8n Workflows | `docs/tutorials/MODULE_*` |
| Project Requirements | `memory-bank/requirements.md` |
| Agent Specifications | `AGENTS.md` |

---

## Assessment Checkpoints

Each week includes verification checkpoints. Mark items complete as you progress:

### Week 1-2 Checkpoint
```bash
# Verify API connectivity
curl http://10.0.4.130:8083/api/v1/health
# Expected: {"status": "ok", ...}

# Verify Streamlit runs
streamlit run apps/web/main_app.py
# Expected: App opens in browser at localhost:8501
```

### Week 3-4 Checkpoint
```bash
# Run API tests
pytest tests/test_v1_endpoints.py -v

# Run web UI tests
pytest tests/test_web_ui.py -v
```

### Week 5-6 Checkpoint
```bash
# Verify Training page functional
# Navigate to http://localhost:8501/Train
# Expected: Training dashboard with metrics display

# Verify Deploy page functional
# Navigate to http://localhost:8501/Deploy
# Expected: Deployment controls with engine status
```

### Week 7-8 Checkpoint
```bash
# Run full test suite
pytest tests/ -v --cov=apps --cov-report=html

# Expected: 80%+ coverage
```

---

*Begin with [Week 1: Project Overview & Architecture](WEEK_01_PROJECT_OVERVIEW.md)*
