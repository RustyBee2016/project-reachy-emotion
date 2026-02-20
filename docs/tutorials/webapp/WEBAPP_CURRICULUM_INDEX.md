# Web Application Development Curriculum

**Project**: Reachy Emotion Recognition  
**Target Audience**: Junior Web Developers  
**Total Duration**: 8 weeks (~48 hours)  
**Last Updated**: 2026-02-01

---

## Curriculum Overview

This curriculum trains junior developers to build, test, and deploy the Reachy Emotion web application stack consisting of:

- **FastAPI Backend** (Media Mover API)
- **Streamlit Frontend** (Web UI)
- **API Gateway** (Proxy layer)

---

## Learning Path

```
Week 1          Week 2          Week 3          Week 4
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ Project │───▶│ Environ │───▶│ FastAPI │───▶│Streamlit│
│Overview │    │  Setup  │    │ Backend │    │Frontend │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
                                                  │
    ┌─────────────────────────────────────────────┘
    │
    ▼
Week 5          Week 6          Week 7          Week 8
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│Training │───▶│ Deploy  │───▶│ Testing │───▶│ Integr. │
│Dashboard│    │Controls │    │   QA    │    │  Prod   │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

---

## Weekly Modules

### Foundation Phase (Weeks 1-2)

| Week | Module | Duration | Key Skills |
|------|--------|----------|------------|
| 1 | [Project Overview & Architecture](WEEK_01_PROJECT_OVERVIEW.md) | 6 hours | System architecture, codebase navigation, data flow tracing |
| 2 | [Environment Setup & Configuration](WEEK_02_ENVIRONMENT_SETUP.md) | 6 hours | Virtual environments, dependency management, IDE configuration |

**Foundation Phase Outcomes:**
- Understand three-tier architecture (UI → Gateway → API)
- Navigate project codebase confidently
- Run Streamlit app locally
- Configure environment variables

---

### Development Phase (Weeks 3-4)

| Week | Module | Duration | Key Skills |
|------|--------|----------|------------|
| 3 | [FastAPI Backend Development](WEEK_03_FASTAPI_BACKEND.md) | 6 hours | Routers, Pydantic schemas, endpoint design, unit testing |
| 4 | [Streamlit Frontend Development](WEEK_04_STREAMLIT_FRONTEND.md) | 6 hours | Page structure, session state, API integration, UI components |

**Development Phase Outcomes:**
- Create FastAPI endpoints with proper validation
- Build Streamlit pages with state management
- Integrate frontend with backend APIs
- Implement form handling and error display

---

### Feature Implementation Phase (Weeks 5-6)

| Week | Module | Duration | Key Skills |
|------|--------|----------|------------|
| 5 | [Training Dashboard Implementation](WEEK_05_TRAINING_DASHBOARD.md) | 6 hours | Gate A validation, MLflow integration, metrics visualization |
| 6 | [Deployment Controls & Monitoring](WEEK_06_DEPLOYMENT_CONTROLS.md) | 6 hours | Gate B validation, Jetson status, deployment staging |

**Feature Phase Outcomes:**
- Build complete Training Dashboard with Gate A checks
- Implement Deployment page with staged rollout controls
- Display real-time metrics and validation status
- Integrate with external services (MLflow, Jetson)

---

### Quality & Production Phase (Weeks 7-8)

| Week | Module | Duration | Key Skills |
|------|--------|----------|------------|
| 7 | [Testing & Quality Assurance](WEEK_07_TESTING_QA.md) | 6 hours | pytest, mocking, coverage, integration tests |
| 8 | [Integration & Production Readiness](WEEK_08_INTEGRATION.md) | 6 hours | Security review, documentation, deployment scripts |

**Quality Phase Outcomes:**
- Achieve 80%+ test coverage
- Complete security checklist
- Prepare production deployment configuration
- Document all components

---

## Skills Matrix

| Skill | Introduced | Practiced | Mastered |
|-------|------------|-----------|----------|
| FastAPI routing | Week 3 | Week 5-6 | Week 7 |
| Pydantic schemas | Week 3 | Week 4-6 | Week 7 |
| Streamlit pages | Week 4 | Week 5-6 | Week 7 |
| Session state | Week 4 | Week 5-6 | Week 7 |
| API client design | Week 4 | Week 5-6 | Week 7 |
| Unit testing | Week 3 | Week 7 | Week 8 |
| Integration testing | Week 7 | Week 8 | Week 8 |
| Documentation | Week 1 | Week 8 | Week 8 |

---

## Prerequisites

### Required Knowledge
- Python 3.10+ fundamentals
- Basic HTTP/REST concepts
- Git version control basics
- Command line proficiency

### Recommended Background
- Previous web development experience
- Database basics (SQL)
- Understanding of async/await

---

## Assessment Checkpoints

### Week 2 Checkpoint
```bash
# Verify environment is set up correctly
python -c "import streamlit, fastapi; print('OK')"
streamlit run apps/web/main_app.py --server.headless true
```

### Week 4 Checkpoint
```bash
# Verify frontend development skills
pytest tests/apps/test_streamlit_pages.py -v
```

### Week 6 Checkpoint
```bash
# Verify feature implementation
# Navigate to Train and Deploy pages - verify functionality
```

### Week 8 Checkpoint
```bash
# Final verification
pytest tests/ --cov=apps --cov-fail-under=80
```

---

## Resources

### Internal Documentation
- `docs/API_ENDPOINT_REFERENCE.md` - Complete API reference
- `docs/database/` - Database schema and tutorials
- `memory-bank/requirements.md` - Project requirements
- `AGENTS.md` - Agent specifications and Gate requirements

### External Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [pytest Documentation](https://docs.pytest.io/)

---

## Tutorial Files

```
docs/tutorials/webapp/
├── WEBAPP_TUTORIAL_INDEX.md      # Main entry point
├── WEBAPP_CURRICULUM_INDEX.md    # This file
├── WEEK_01_PROJECT_OVERVIEW.md   # Week 1 tutorial
├── WEEK_02_ENVIRONMENT_SETUP.md  # Week 2 tutorial
├── WEEK_03_FASTAPI_BACKEND.md    # Week 3 tutorial
├── WEEK_04_STREAMLIT_FRONTEND.md # Week 4 tutorial
├── WEEK_05_TRAINING_DASHBOARD.md # Week 5 tutorial
├── WEEK_06_DEPLOYMENT_CONTROLS.md# Week 6 tutorial
├── WEEK_07_TESTING_QA.md         # Week 7 tutorial
└── WEEK_08_INTEGRATION.md        # Week 8 tutorial
```

---

## Getting Started

1. Begin with [Week 1: Project Overview](WEEK_01_PROJECT_OVERVIEW.md)
2. Work through each week sequentially
3. Complete all checkpoints before proceeding
4. Ask questions when stuck - don't skip concepts

---

*This curriculum is designed to be completed at a pace of ~6 hours per week. Adjust timing as needed based on prior experience.*
