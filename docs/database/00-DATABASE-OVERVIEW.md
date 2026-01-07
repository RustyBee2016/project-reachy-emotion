# Reachy Emotion Detection - PostgreSQL Database Overview

## Introduction

This document provides a comprehensive overview of the PostgreSQL database system for the Reachy Emotion Detection project. The database serves as the central metadata repository for video clips, training runs, model deployments, and system auditing.

**Important**: The database does NOT store actual video files. Video files (MP4s) are stored on the filesystem (typically at `/mnt/videos` or configured path). The database stores *metadata* about these files - where they are located, what emotion they're labeled with, which training runs used them, etc.

## What This Database Does

Think of this database as the "brain's memory" for the Reachy robot emotion recognition system:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     REACHY EMOTION SYSTEM                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │ Jetson Edge  │────▶│  PostgreSQL  │────▶│    TAO/ML    │        │
│  │  (Camera)    │     │  (Metadata)  │     │  (Training)  │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│         │                    │                    │                 │
│         ▼                    ▼                    ▼                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │ Temp Videos  │────▶│ Labeled Data │────▶│Trained Model │        │
│  │   (files)    │     │   (DB rows)  │     │   (.engine)  │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

The database tracks:
- **Video metadata**: File locations, sizes, hashes, dimensions, durations
- **Emotion labels**: What emotion each video represents (happy, sad, angry, etc.)
- **Data splits**: Whether a video is temporary, in the training set, or test set
- **Training runs**: Each model training attempt with its configuration and results
- **Audit trails**: Who labeled what, when, and why
- **Deployments**: Model deployments to Jetson edge devices
- **System metrics**: Performance telemetry for monitoring

## System Architecture

The database integrates with a three-node Ubuntu system:

```
┌─────────────────────────────────────────────────────────────────────┐
│  UBUNTU 1 (10.0.4.130) - Primary Storage & Database                  │
│  ├── PostgreSQL Server (port 5432)                                   │
│  ├── Video files (/media/project_data/reachy_emotion/videos/)        │
│  ├── Media Mover API (FastAPI on port 8081)                          │
│  └── Nginx (static file serving)                                     │
├─────────────────────────────────────────────────────────────────────┤
│  UBUNTU 2 (10.0.4.140) - API Gateway & Automation                    │
│  ├── Gateway API (FastAPI on port 8080)                              │
│  ├── n8n Automation (webhooks, workflows)                            │
│  └── Web UI (Streamlit)                                              │
├─────────────────────────────────────────────────────────────────────┤
│  JETSON (Edge Device) - Real-time Inference                          │
│  ├── TensorRT Engine (.engine model)                                 │
│  ├── DeepStream Pipeline                                             │
│  └── Emotion event streaming to Gateway                              │
└─────────────────────────────────────────────────────────────────────┘
```

## Database Design Philosophy

### Three-Phase Schema

The database schema was designed in three phases, each building on the previous:

| Phase | SQL File | Purpose |
|-------|----------|---------|
| 1 | `001_phase1_schema.sql` | Core tables (video, training_run, user_session) |
| 2 | `002_stored_procedures.sql` | Business logic functions |
| 3 | `003_missing_tables.sql` | Agent support tables (audit, deployment, metrics) |

### Key Design Decisions

1. **Idempotency**: Critical operations use idempotency keys to prevent duplicate processing
2. **No raw video storage**: Only metadata; actual MP4s live on filesystem
3. **Soft deletes**: `deleted_at` column for GDPR compliance
4. **JSONB flexibility**: `metadata`, `metrics`, `config` fields for extensible data
5. **Reproducible training**: Every run stores `seed` and `dataset_hash` for reproducibility

## File Reference

### SQL Schema Files
| File | Path | Description |
|------|------|-------------|
| Phase 1 Schema | `alembic/versions/001_phase1_schema.sql` | Core tables (193 lines) |
| Stored Procedures | `alembic/versions/002_stored_procedures.sql` | Business logic (362 lines) |
| Agent Tables | `alembic/versions/003_missing_tables.sql` | Support tables (297 lines) |

### Python ORM Files
| File | Path | Description |
|------|------|-------------|
| Models | `apps/api/app/db/models.py` | SQLAlchemy ORM models (304 lines) |
| Enums | `apps/api/app/db/enums.py` | Python enum definitions (44 lines) |
| Session | `apps/api/app/db/session.py` | Database session management (38 lines) |
| Base | `apps/api/app/db/base.py` | SQLAlchemy base class (28 lines) |

### Alembic Migration Files
| File | Path | Description |
|------|------|-------------|
| Alembic Config | `apps/api/app/db/alembic/env.py` | Migration environment |
| Initial Migration | `apps/api/app/db/alembic/versions/202510280000_initial_schema.py` | Programmatic schema |

### Scripts
| File | Path | Description |
|------|------|-------------|
| Bootstrap Script | `misc/code/bootstrap_reachy_db_and_media.sh` | Full database + media setup |

### Configuration
| File | Path | Description |
|------|------|-------------|
| App Settings | `apps/api/app/settings.py` | Database URL and paths |
| Config | `apps/api/app/config.py` | Extended configuration |

## Quick Start

### Check Database Status

```bash
# Test PostgreSQL connectivity
psql -h localhost -U postgres -c "SELECT version();"

# If running, list tables
psql -d reachy_local -c "\dt"
```

### Expected Tables (12 total)

```
video              - Video metadata registry
training_run       - Training job tracking
training_selection - Video-to-run assignments
promotion_log      - Split change audit trail
user_session       - User activity tracking
generation_request - Synthetic video requests
emotion_event      - Real-time detections (streaming)
label_event        - Labeling action audit
deployment_log     - Model deployment tracking
audit_log          - Privacy/GDPR compliance
obs_samples        - System metrics
reconcile_report   - Filesystem consistency
```

## Documentation Index

| Document | Description |
|----------|-------------|
| [01-DATABASE-CONCEPTS.md](01-DATABASE-CONCEPTS.md) | Database fundamentals for beginners |
| [02-SCHEMA-REFERENCE.md](02-SCHEMA-REFERENCE.md) | Complete table and column reference |
| [03-STORED-PROCEDURES.md](03-STORED-PROCEDURES.md) | Business logic functions |
| [04-PYTHON-ORM-MODELS.md](04-PYTHON-ORM-MODELS.md) | SQLAlchemy model documentation |
| [05-API-INTEGRATION.md](05-API-INTEGRATION.md) | How APIs interact with the database |
| [06-MIGRATIONS.md](06-MIGRATIONS.md) | Schema migration system |
| [07-KNOWN-ISSUES.md](07-KNOWN-ISSUES.md) | Current issues and workarounds |
| [08-SETUP-GUIDE.md](08-SETUP-GUIDE.md) | Installation and setup instructions |

## Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Schema Design | Complete | All 12 tables defined |
| Stored Procedures | Complete | 5 core functions |
| Python ORM Models | Partial | Some model-schema mismatches exist |
| Alembic Migrations | Complete | Both SQL and Python formats |
| PostgreSQL Server | Not Running | Requires initialization |

**Operational Readiness**: ~70% (requires fixes before production deployment - see [07-KNOWN-ISSUES.md](07-KNOWN-ISSUES.md))

## Next Steps

If you're new to this codebase:
1. Read [01-DATABASE-CONCEPTS.md](01-DATABASE-CONCEPTS.md) to understand database fundamentals
2. Review [02-SCHEMA-REFERENCE.md](02-SCHEMA-REFERENCE.md) to see all tables
3. Follow [08-SETUP-GUIDE.md](08-SETUP-GUIDE.md) to set up your development environment
4. Check [07-KNOWN-ISSUES.md](07-KNOWN-ISSUES.md) before making changes
