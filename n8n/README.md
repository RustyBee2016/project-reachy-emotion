# Reachy Agentic AI Workflows - Download & Deployment Guide

## Overview

This directory contains **9 production-ready n8n workflows** that implement the complete agentic AI orchestration system for Reachy_Local_08.4.2. Each workflow is a JSON file that can be directly imported into n8n.

---

## What's Included

### Documentation
- **AGENTIC_SYSTEM_OVERVIEW.md** — Comprehensive architecture guide explaining Claude Sonnet 4.5 + n8n MCP integration
- **AGENT_SUMMARIES.md** — Detailed purpose and benefits for each of the 9 agents
- **README.md** — This file (deployment instructions)

### Workflow Files (Ready for Download)

All files are located in `/home/rusty_admin/projects/reachy_08.4.2/n8n/workflows/`:

1. **01_ingest_agent.json** — Video ingestion with hashing and metadata extraction
2. **02_labeling_agent.json** — Human-in-the-loop labeling with class balance tracking
3. **03_promotion_agent.json** — Safe video promotion with dry-run and approval gates
4. **04_reconciler_agent.json** — Filesystem ↔ database drift detection and reporting
5. **05_training_orchestrator.json** — TAO training with MLflow tracking and Gate A validation
6. **06_evaluation_agent.json** — Test set evaluation with Gate B validation
7. **07_deployment_agent.json** — Gradual rollout (shadow → canary → production)
8. **08_privacy_agent.json** — TTL enforcement and GDPR compliance
9. **09_observability_agent.json** — Metrics aggregation and SLA monitoring

---

## Quick Start

### 1. Download Workflows

**Option A: From File Explorer**
Navigate to:
```
/home/rusty_admin/projects/reachy_08.4.2/n8n/workflows/
```

Select all 9 JSON files and copy to your n8n instance.

**Option B: Command Line**
```bash
# Create archive
cd /home/rusty_admin/projects/reachy_08.4.2/n8n
tar -czf reachy_workflows.tar.gz workflows/*.json

# Copy to n8n host (if different machine)
scp reachy_workflows.tar.gz user@n8n-host:/tmp/
ssh user@n8n-host "cd /tmp && tar -xzf reachy_workflows.tar.gz"
```

### 2. Install n8n (if not already installed)

```bash
# Via npm
npm install -g n8n

# Via Docker
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n

# Via Docker Compose (recommended for production)
# See: https://docs.n8n.io/hosting/installation/docker/
```

### 3. Set Environment Variables

Create `/home/node/.n8n/.env` (or set in Docker Compose):

```bash
# n8n Configuration
N8N_METRICS=true
GENERIC_TIMEZONE=America/New_York
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=<SECURE_PASSWORD>

# Project-Specific
MEDIA_MOVER_BASE_URL=http://10.0.4.130:8081/api
GATEWAY_BASE_URL=http://10.0.4.140:8000
MLFLOW_URL=http://10.0.4.130:5000
MLFLOW_EXPERIMENT_ID=0
INGEST_TOKEN=<SECURE_RANDOM_TOKEN>
```

### 4. Import Workflows

**Via n8n UI:**
1. Open n8n: `http://localhost:5678` (or your n8n URL)
2. Go to **Workflows** → **Import from File**
3. Select each JSON file (or import all at once)
4. Click **Import**

**Via CLI:**
```bash
n8n import:workflow --input=/path/to/01_ingest_agent.json
n8n import:workflow --input=/path/to/02_labeling_agent.json
# ... repeat for all 9 files
```

### 5. Configure Credentials

In n8n UI, go to **Credentials** and create:

#### PostgreSQL
- **Name**: PostgreSQL - reachy_local
- **Host**: localhost (or 10.0.4.130)
- **Database**: reachy_local
- **User**: reachy_app
- **Password**: reachy_app

#### HTTP Header Auth (Media Mover)
- **Name**: Media Mover Auth
- **Name**: Authorization
- **Value**: Bearer <YOUR_MEDIA_MOVER_TOKEN>

#### SSH Password (Ubuntu 1)
- **Name**: SSH Ubuntu1
- **Host**: 10.0.4.130
- **Port**: 22
- **Username**: rusty_admin
- **Password/Key**: <YOUR_SSH_CREDENTIALS>

#### SSH Password (Jetson)
- **Name**: SSH Jetson
- **Host**: 10.0.4.150
- **Port**: 22
- **Username**: jetson
- **Password/Key**: <YOUR_SSH_CREDENTIALS>

### 6. Activate Workflows

For each imported workflow:
1. Open the workflow
2. Verify all nodes show green checkmarks (no configuration errors)
3. Click **Active** toggle in top-right
4. Verify webhook URLs are generated

### 7. Test Webhooks

```bash
# Test Ingest Agent
curl -X POST http://localhost:5678/webhook/video_gen_hook \
  -H "X-INGEST-KEY: ${INGEST_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "source_url": "https://example.com/test.mp4",
    "label": "happy",
    "meta": {"generator": "test"}
  }'

# Test Labeling Agent
curl -X POST http://localhost:5678/webhook/label \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "550e8400-e29b-41d4-a716-446655440000",
    "label": "happy",
    "action": "label_only",
    "rater_id": "test_user"
  }'

# Test Reconciler Agent (manual trigger)
curl -X GET http://localhost:5678/webhook/reconciler/audit
```

---

## Database Setup

### Required Tables

Run these SQL scripts on your PostgreSQL database:

```sql
-- Label events (audit trail)
CREATE TABLE IF NOT EXISTS label_event (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID NOT NULL REFERENCES video(video_id) ON DELETE CASCADE,
  label TEXT NOT NULL,
  action TEXT NOT NULL,
  rater_id TEXT,
  notes TEXT,
  idempotency_key TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (video_id, idempotency_key)
);

-- Reconciler reports
CREATE TABLE IF NOT EXISTS reconcile_report (
  report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  total_fs INT,
  total_db INT,
  orphans_count INT,
  missing_count INT,
  mismatch_count INT,
  report_json JSONB
);

-- Deployment logs
CREATE TABLE IF NOT EXISTS deployment_log (
  deployment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  engine_path TEXT NOT NULL,
  target_stage TEXT NOT NULL,
  deployed_at TIMESTAMPTZ DEFAULT NOW(),
  status TEXT DEFAULT 'success'
);

-- Audit logs (privacy/GDPR)
CREATE TABLE IF NOT EXISTS audit_log (
  log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  action TEXT NOT NULL,
  video_id UUID,
  reason TEXT,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Observability samples
CREATE TABLE IF NOT EXISTS obs_samples (
  sample_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts TIMESTAMPTZ NOT NULL,
  src TEXT NOT NULL,
  metric TEXT NOT NULL,
  value DOUBLE PRECISION,
  correlation_id TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_label_event_video ON label_event(video_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_obs_samples_ts ON obs_samples(ts DESC, src, metric);
CREATE INDEX IF NOT EXISTS idx_audit_log_video ON audit_log(video_id, timestamp DESC);
```

---

## Monitoring & Troubleshooting

### Check Workflow Status

```bash
# List active workflows
curl -u admin:password http://localhost:5678/api/v1/workflows?active=true

# View recent executions
curl -u admin:password http://localhost:5678/api/v1/executions?limit=10
```

### View Logs

```bash
# Docker logs
docker logs n8n -f

# Systemd logs (if using systemd)
journalctl -u n8n -f
```

### Common Issues

#### Webhook Not Found (404)
- Verify workflow is **Active**
- Check webhook path matches the one generated by n8n
- Restart n8n if needed

#### Authentication Errors
- Verify `INGEST_TOKEN` matches in both n8n env and calling code
- Check PostgreSQL credentials are correct
- Test SSH connections manually: `ssh rusty_admin@10.0.4.130`

#### Metrics Not Appearing
- Verify `N8N_METRICS=true` in environment
- Check `/metrics` endpoint: `curl http://localhost:5678/metrics`
- Ensure Observability Agent (09) is active

#### Training Orchestrator Hangs
- Check TAO is installed on Ubuntu 1
- Verify SSH connection to Ubuntu 1 works
- Check `/workspace/experiments/<run_id>/train.log` for TAO errors
- Increase Wait node timeout if training takes > 5 min per poll

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     n8n Orchestration Layer                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Agent 1  │ │ Agent 2  │ │ Agent 3  │ │ Agent 4  │      │
│  │  Ingest  │ │ Labeling │ │Promotion │ │Reconciler│      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│       ↓            ↓            ↓            ↓             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ Agent 5  │ │ Agent 6  │ │ Agent 7  │ │ Agent 8  │      │
│  │ Training │ │Evaluation│ │Deployment│ │ Privacy  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│       ↓                                        ↑           │
│  ┌──────────────────────────────────────────────┐         │
│  │         Agent 9: Observability               │         │
│  └──────────────────────────────────────────────┘         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
          ↓                     ↓                   ↓
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Ubuntu 1      │  │   Ubuntu 2      │  │   Jetson        │
│   Model Host    │  │   App Gateway   │  │   Edge Runtime  │
│                 │  │                 │  │                 │
│ • Media Mover   │  │ • FastAPI       │  │ • DeepStream    │
│ • PostgreSQL    │  │ • Streamlit     │  │ • TensorRT      │
│ • MLflow        │  │ • Nginx         │  │                 │
│ • TAO Training  │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Next Steps

1. **Review AGENTIC_SYSTEM_OVERVIEW.md** for architecture details
2. **Review AGENT_SUMMARIES.md** for each agent's purpose and benefits
3. **Import all workflows** to n8n
4. **Configure credentials** and environment variables
5. **Run test webhooks** to verify connectivity
6. **Check Agent 9 metrics** to confirm observability is working
7. **Trigger Agent 4 manually** to establish baseline reconciliation
8. **Review execution logs** for any errors

---

## Support & Documentation

- **n8n Documentation**: https://docs.n8n.io
- **n8n Community**: https://community.n8n.io
- **Project Requirements**: `/memory-bank/requirements_08.4.2.md`
- **Agent Specifications**: `/AGENTS_08.4.2.md`
- **Implementation Guide**: `/docs/gpt/Implementation_Phase4_Orchestration_Opus_4.1.md`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-07 | Initial release of 9 agent workflows |

---

**Maintainer**: Russell Bray (rustybee255@gmail.com)  
**License**: TBD  
**Status**: Ready for Production Deployment
