# Week 1: Project Overview & Architecture

**Duration**: ~6 hours  
**Goal**: Understand the complete web application architecture and codebase structure  
**Prerequisites**: Basic Python knowledge, familiarity with web concepts

---

## Day 1: Understanding the Reachy Emotion System (2 hours)

### 1.1 Project Purpose

The Reachy Emotion Recognition system enables a humanoid robot (Reachy Mini) to:
1. **Detect emotions** from video frames using deep learning
2. **Respond appropriately** with gestures and LLM-generated dialogue
3. **Learn continuously** through human-labeled training data

The web application you'll be working on serves as the **human-in-the-loop interface** for:
- Uploading and generating training videos
- Labeling emotions (happy, sad, neutral)
- Monitoring training progress
- Controlling model deployment to the robot

### 1.2 System Components Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         REACHY EMOTION SYSTEM                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────┐│
│   │  Web UI     │───▶│   Gateway   │───▶│     Media Mover API         ││
│   │ (Streamlit) │    │  (FastAPI)  │    │       (FastAPI)             ││
│   │             │    │             │    │                             ││
│   │ • Upload    │    │ • Proxy     │    │ • CRUD videos               ││
│   │ • Label     │    │ • WebSocket │    │ • Promote splits            ││
│   │ • Train     │    │ • Auth      │    │ • Generate thumbnails       ││
│   │ • Deploy    │    │             │    │ • Trigger workflows         ││
│   └─────────────┘    └─────────────┘    └─────────────────────────────┘│
│         │                                          │                    │
│         │                                          ▼                    │
│         │            ┌─────────────────────────────────────────────────┐│
│         │            │              PostgreSQL Database                ││
│         │            │  • videos table (metadata, labels)              ││
│         │            │  • promotion_logs table                         ││
│         │            │  • training_runs table                          ││
│         │            └─────────────────────────────────────────────────┘│
│         │                                          │                    │
│         ▼                                          ▼                    │
│   ┌─────────────┐                    ┌─────────────────────────────────┐│
│   │    n8n      │                    │      File Storage               ││
│   │  Workflows  │                    │  /media/project_data/           ││
│   │             │                    │    ├── videos/temp/             ││
│   │ • Ingest    │                    │    ├── videos/train/            ││
│   │ • Labeling  │                    │    ├── videos/test/             ││
│   │ • Training  │                    │    └── thumbs/                  ││
│   └─────────────┘                    └─────────────────────────────────┘│
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Network Topology

| Node | IP Address | Services | Port(s) |
|------|------------|----------|---------|
| Ubuntu 1 | 10.0.4.130 | Media Mover API, PostgreSQL, n8n, MLflow | 8083, 5432, 5678, 5000 |
| Ubuntu 2 | 10.0.4.140 | Gateway, Streamlit UI, Nginx | 8000, 8501, 443 |
| Jetson NX | 10.0.4.150 | DeepStream Inference, TensorRT | 8554 |

### Checkpoint 1.1
Answer these questions before proceeding:

1. What is the primary purpose of the web application?
2. Which server hosts the PostgreSQL database?
3. What port does the Media Mover API listen on?

---

## Day 2: Exploring the Codebase (2 hours)

### 2.1 Directory Structure Deep Dive

Open the project in your IDE and explore the following directories:

```bash
# Navigate to project root
cd d:\projects\reachy_emotion

# List the apps directory
dir apps
```

**Key directories to understand:**

#### `apps/api/` — FastAPI Backend

```
apps/api/
├── app/
│   ├── main.py              # ⭐ Start here - creates FastAPI app
│   ├── config.py            # Environment configuration
│   ├── routers/             # API endpoint handlers
│   │   ├── health.py        # GET /api/v1/health
│   │   ├── media_v1.py      # GET/POST /api/v1/media/*
│   │   ├── promote.py       # POST /api/v1/promote/*
│   │   └── ingest.py        # POST /api/media/ingest
│   ├── services/            # Business logic
│   │   ├── promote_service.py   # Video promotion logic
│   │   └── thumbnail_watcher.py # Auto-generate thumbnails
│   └── schemas/             # Pydantic data models
│       ├── video.py         # Video metadata schema
│       └── promote.py       # Promotion request/response
└── routers/                 # Legacy endpoints (deprecated)
```

#### `apps/web/` — Streamlit Frontend

```
apps/web/
├── main_app.py              # ⭐ Streamlit entry point
├── landing_page.py          # Full-featured alternative entry
├── api_client.py            # ⭐ HTTP client for API calls
├── api_client_v2.py         # Enhanced client with typing
├── session_manager.py       # ⭐ Streamlit session state
├── websocket_client.py      # Real-time event handling
├── pages/                   # Multi-page app structure
│   ├── 00_Home.py           # ⭐ Main workflow page
│   ├── 01_Generate.py       # Video generation (placeholder)
│   ├── 02_Label.py          # Browse and label videos
│   ├── 03_Train.py          # Training dashboard (TODO)
│   ├── 04_Deploy.py         # Deployment controls (TODO)
│   └── 05_Video_Management.py # Batch operations
└── components/              # Reusable UI widgets
    ├── stats_panel.py
    └── video_player.py
```

#### `apps/gateway/` — API Gateway

```
apps/gateway/
├── main.py                  # ⭐ Gateway entry point
├── config.py                # Gateway configuration
└── README.md                # Gateway documentation
```

### 2.2 Reading the Code

**Exercise**: Open and read these files in order:

1. **`apps/api/app/main.py`** — Understand how FastAPI app is created
   ```python
   # Key concepts to identify:
   # - How routers are registered
   # - CORS middleware configuration
   # - Lifespan events (startup/shutdown)
   ```

2. **`apps/web/main_app.py`** — Understand Streamlit entry point
   ```python
   # Key concepts to identify:
   # - Page configuration
   # - Session state initialization
   # - Navigation structure
   ```

3. **`apps/web/api_client.py`** — Understand API communication
   ```python
   # Key concepts to identify:
   # - Base URL configuration
   # - Request headers (authentication)
   # - Retry logic for resilience
   ```

### 2.3 Code Reading Questions

After reading the code, answer:

1. In `apps/api/app/main.py`, what routers are registered with `app.include_router()`?
2. In `apps/web/api_client.py`, what environment variable sets the API base URL?
3. In `apps/web/main_app.py`, what pages are listed in the navigation description?

---

## Day 3: Understanding Data Flow (2 hours)

### 3.1 Video Upload Flow

When a user uploads a video, the following sequence occurs:

```
┌──────────────┐   POST /api/media/ingest   ┌──────────────┐
│   Browser    │ ─────────────────────────▶ │   Gateway    │
│  (Streamlit) │                            │  (Ubuntu 2)  │
└──────────────┘                            └──────┬───────┘
                                                   │
                                                   │ Proxy
                                                   ▼
                                            ┌──────────────┐
                                            │ Media Mover  │
                                            │  (Ubuntu 1)  │
                                            └──────┬───────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────────────────┐
                    │                              │                              │
                    ▼                              ▼                              ▼
            ┌──────────────┐              ┌──────────────┐              ┌──────────────┐
            │   Save to    │              │  Compute     │              │   Insert     │
            │   /temp/     │              │  SHA256      │              │   Database   │
            └──────────────┘              └──────────────┘              └──────────────┘
                    │
                    ▼
            ┌──────────────┐
            │  Generate    │
            │  Thumbnail   │
            └──────────────┘
```

**Code path to trace:**

1. `apps/web/pages/00_Home.py` → `api_client.upload_video()`
2. `apps/web/api_client.py` → `upload_video()` function
3. `apps/gateway/main.py` → proxy to Media Mover
4. `apps/api/app/routers/ingest.py` → `ingest_video()` endpoint

### 3.2 Video Promotion Flow

When a user labels and promotes a video:

```
┌──────────────┐   POST /api/v1/promote/stage   ┌──────────────┐
│   Classify   │ ─────────────────────────────▶ │ Promote      │
│   Button     │                                │ Service      │
└──────────────┘                                └──────┬───────┘
                                                       │
                    ┌──────────────────────────────────┼──────────────────────────────┐
                    │                                  │                              │
                    ▼                                  ▼                              ▼
            ┌──────────────┐              ┌──────────────┐              ┌──────────────┐
            │  Move File   │              │  Update DB   │              │   Log        │
            │  temp → train│              │  label, split│              │   Promotion  │
            └──────────────┘              └──────────────┘              └──────────────┘
```

**Code path to trace:**

1. `apps/web/pages/00_Home.py` → `_promote_current_video()`
2. `apps/web/api_client.py` → `promote()` or `stage_to_dataset_all()`
3. `apps/api/app/routers/promote.py` → endpoint handler
4. `apps/api/app/services/promote_service.py` → business logic

### 3.3 Hands-On Exercise: Trace a Request

Using your IDE's search functionality, trace the `list_videos` function:

1. **Find the UI call**: Search for `list_videos` in `apps/web/pages/02_Label.py`
2. **Find the client function**: Open `apps/web/api_client.py`, find `list_videos()`
3. **Find the API endpoint**: Search for `/api/v1/media/list` in routers
4. **Find the database query**: Look in the router handler for query logic

Document the complete path from UI to database:

```
UI Component: ________________
API Client Function: ________________
API Endpoint: ________________
Router Handler: ________________
Service/Query: ________________
```

---

## Day 3 Exercises

### Exercise 1.1: Draw the Architecture

Create your own diagram showing:
- The three main services (UI, Gateway, API)
- The database and file storage
- Network flow between them

### Exercise 1.2: Identify Component Status

Fill in this table by examining the code:

| Page | File | Status | What's Missing |
|------|------|--------|----------------|
| Home | `00_Home.py` | Complete | |
| Generate | `01_Generate.py` | | |
| Label | `02_Label.py` | | |
| Train | `03_Train.py` | | |
| Deploy | `04_Deploy.py` | | |
| Video Mgmt | `05_Video_Management.py` | | |

### Exercise 1.3: API Endpoint Inventory

Using `grep` or IDE search, list all API endpoints:

```bash
# Search for route decorators in routers
grep -r "@router" apps/api/app/routers/
```

Create a table of endpoints you find.

---

## Week 1 Deliverables Checklist

- [ ] Understood the three-tier architecture
- [ ] Explored all directories under `apps/`
- [ ] Read `main.py` files for API, Gateway, and Web
- [ ] Traced at least one complete request flow
- [ ] Identified which pages need implementation
- [ ] Created personal architecture diagram

---

## Self-Assessment

Rate your understanding (1-3):

| Topic | Rating |
|-------|--------|
| Project purpose and goals | |
| Three-tier architecture | |
| Directory structure | |
| API → Database flow | |
| UI → API flow | |
| What needs to be built | |

**1** = Need more study  
**2** = Understand basics  
**3** = Ready to implement

---

## Next Steps

If you scored mostly 2s and 3s, proceed to [Week 2: Environment Setup](WEEK_02_ENVIRONMENT_SETUP.md).

If you scored 1s on any topic, spend additional time:
- Re-read the relevant code files
- Ask questions to your mentor
- Review the API documentation in `docs/API_ENDPOINT_REFERENCE.md`
