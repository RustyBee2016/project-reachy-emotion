# Reachy Agentic AI System with Claude Sonnet 4.5 + n8n MCP

## Executive Summary

This document describes how we leverage **Claude Sonnet 4.5 Thinking Model** in conjunction with the **n8n MCP Server** to implement a sophisticated 9-agent orchestration system for the Reachy_Local_08.4.2 emotion recognition pipeline.

---

## System Architecture

### Technology Stack
- **AI Model**: Claude Sonnet 4.5 Thinking (advanced reasoning & planning)
- **Orchestration**: n8n workflow automation platform
- **Integration**: n8n MCP Server (Model Context Protocol)
- **Database**: PostgreSQL 16 (metadata only)
- **Storage**: Local filesystem with Nginx serving
- **Messaging**: Event-driven architecture with correlation IDs

### Network Topology
```
Ubuntu 1 (10.0.4.130)  — Model Host
├── LM Studio (Llama 3.1-8B)
├── Media Mover API (:8081)
├── PostgreSQL (:5432)
├── n8n (:5678)
└── Nginx (:80/:443)

Ubuntu 2 (10.0.4.140)  — App Gateway
├── FastAPI Gateway (:8000)
├── Streamlit Web UI (:8501)
└── Nginx Reverse Proxy

Jetson Xavier NX (10.0.4.150) — Edge Runtime
├── DeepStream 6.x
├── TensorRT Inference
└── WebSocket Client
```

---

## How Claude Sonnet 4.5 Powers the System

### 1. Deep Reasoning for Workflow Design
Claude Sonnet 4.5's **extended thinking capability** allows us to:
- Analyze complex state transitions across the 9-agent system
- Design robust error recovery paths
- Plan idempotency strategies for distributed operations
- Reason about race conditions in concurrent workflows

### 2. Context-Aware Decision Making
The model maintains deep context across:
- 465 lines of requirements (`requirements_08.4.2.md`)
- 212 lines of agent specifications (`AGENTS_08.4.2.md`)  
- Multiple implementation guides totaling 30K+ lines
- Real-time execution state during workflow runs

### 3. Adaptive Workflow Generation
For each agent, Claude:
1. **Analyzes** the agent's responsibility from documentation
2. **Designs** the optimal node graph (triggers → transforms → actions)
3. **Implements** error handling and retry logic
4. **Validates** against project constraints (privacy, idempotency, gates)
5. **Generates** production-ready n8n workflow JSON

---

## How n8n MCP Server Enables Integration

### MCP Tools Utilized

#### Discovery & Documentation
- `search_nodes`: Find appropriate n8n nodes for each workflow step
- `get_node_essentials`: Get concise configuration for webhook, HTTP, code nodes
- `get_node_documentation`: Reference examples and best practices

#### Validation
- `validate_workflow`: Pre-flight check before deployment
- `validate_workflow_connections`: Ensure proper node wiring
- `validate_workflow_expressions`: Check n8n expression syntax

#### Workflow Management
- `n8n_create_workflow`: Deploy workflows programmatically
- `n8n_update_partial_workflow`: Incremental updates without full rewrites
- `n8n_list_workflows`: Track deployed agents
- `n8n_get_execution`: Monitor running workflows

#### Template Discovery
- `search_templates`: Find community patterns for common tasks
- `get_template`: Import proven workflow structures

---

## The 9 Agentic AI Workflows

### Agent 1: Ingest Agent
**Purpose**: Receive video uploads/generations and register them atomically

**Benefit**: Ensures every video entering the system is hashed, validated, and tracked with full metadata before any processing begins

**Key Nodes**:
- Webhook trigger (`POST /video_gen_hook`)
- Authentication check (header token validation)
- Code node for payload normalization
- HTTP Request to Media Mover (`/api/media/pull`)
- Loop/Wait pattern for polling pull status
- PostgreSQL insert with deduplication

**Error Handling**: Responds with 4xx for bad requests; retries transient Media Mover failures; logs all events for audit

---

### Agent 2: Labeling Agent
**Purpose**: Process human labels from web UI and update database + Media Mover

**Benefit**: Maintains single source of truth for labels while enforcing class balance constraints (50/50 happy/sad)

**Key Nodes**:
- Webhook trigger (`POST /label`)
- JWT validation in Code node
- PostgreSQL fetch video row (existence check)
- PostgreSQL upsert to `label_event` + update `video.label`
- Switch node branching on action (label_only | promote_train | promote_test | discard)
- HTTP Request to Media Mover `/api/relabel` or `/api/promote`
- Respond to Webhook with updated state

**Integration**: Triggers Promotion Agent when action = `promote_*`

---

### Agent 3: Promotion/Curation Agent
**Purpose**: Safely move videos from temp → train/test with dry-run + human approval

**Benefit**: Prevents accidental data loss; enforces class balance; maintains manifests; enables rollback

**Key Nodes**:
- Webhook trigger (`POST /promotion/v1`)
- Code validation (video_id, label, target split)
- HTTP dry-run promotion (gets plan preview)
- Human approval gate (Slack/webhook)
- IF node checking approval status
- HTTP real promotion (atomic move + DB update)
- HTTP manifest rebuild
- Metrics emission to Observability Agent

**Idempotency**: SHA256-based idempotency keys prevent duplicate promotions even on retry

---

### Agent 4: Reconciler/Audit Agent
**Purpose**: Detect filesystem ↔ database drift and enforce consistency

**Benefit**: Catches orphaned files, missing files, split mismatches, and thumbnail gaps before they cause training failures

**Key Nodes**:
- Schedule Trigger (2:15 AM daily) + manual Webhook
- SSH to Ubuntu 1 to enumerate `/videos/{temp,train,test}`
- PostgreSQL SELECT to fetch all `video` rows
- Code node diffing FS vs DB (orphans, missing, mismatches)
- Split In Batches for safe iteration
- IF gate for `safe_fix` boolean
- PostgreSQL updates for benign fixes (e.g., split='missing' for deleted files)
- HTTP Request to rebuild manifests if gaps found
- Email/Slack summary report

**Safety**: Never deletes; only reports or marks drift; respects `safe_fix` flag

---

### Agent 5: Training Orchestrator
**Purpose**: Trigger TAO fine-tuning when dataset is ready; track in MLflow; validate Gate A

**Benefit**: Automates the train loop while enforcing quality gates (F1 ≥ 0.84, ECE ≤ 0.08); records lineage

**Key Nodes**:
- Webhook trigger (`POST /agent/training/start`)
- HTTP create MLflow run
- Execute Command to launch TAO training (detached, nohup)
- Wait node (5 min loop) until `summary.json` appears
- Code parse metrics (macro_f1, ece, brier, per-class F1)
- HTTP log params/metrics to MLflow
- IF node for Gate A thresholds
  - **Pass**: Execute TAO export → TensorRT build → log `.engine` artifact
  - **Fail**: Mark run failed, emit `training.failed` event
- Optional ZFS snapshot for reproducibility

**Performance**: Uses Wait node to offload state; doesn't block n8n workers for 2-4 hour training runs

---

### Agent 6: Evaluation Agent
**Purpose**: Run validation on test set once balanced; produce confusion matrix

**Benefit**: Ensures test set remains unlabeled (privacy); produces Gate B/C metrics for deployment decisions

**Key Nodes**:
- Webhook trigger (`POST /agent/evaluation/start`) or Schedule (post-training)
- PostgreSQL check: `min(happy_count_test, sad_count_test) ≥ TEST_MIN_PER_CLASS`
- Execute Command: Run DeepStream or TAO inference on `/videos/test/`
- Code: Parse predictions, compute confusion matrix, accuracy, F1
- HTTP log to MLflow
- IF Gate B check (on-device latency ≤ 250ms p95, F1 ≥ 0.80)
- Emit `evaluation.completed` with gate decision

**Key Constraint**: Never attaches labels to test videos internally

---

### Agent 7: Deployment Agent
**Purpose**: Promote TRT engines shadow → canary → rollout with approval gates

**Benefit**: Enables safe gradual rollout; supports instant rollback on regression

**Key Nodes**:
- Webhook trigger (`POST /agent/deployment/promote`)
- Code validation (engine_path, target_stage, metrics)
- IF stage check (shadow | canary | rollout)
  - **Shadow**: Copy `.engine` to Jetson shadow slot, no traffic routing
  - **Canary**: Route 10% traffic, monitor for 30 min
  - **Rollout**: Full traffic switch
- SSH to Jetson: `scp engine`, update DeepStream config, `systemctl restart reachy-emotion`
- Wait + HTTP poll Jetson `/healthz` endpoint
- Execute Command: `tegrastats` check (GPU temp, FPS)
- PostgreSQL log deployment metadata
- IF rollback_needed: restore prior engine
- Emit `deployment.completed` or `deployment.rolled_back`

**Approval**: Requires two-stage human approval (shadow→canary, canary→rollout) via Slack/webhook

---

### Agent 8: Privacy/Retention Agent
**Purpose**: Enforce TTLs, purge temp videos, support GDPR deletion

**Benefit**: Ensures compliance with data retention policies; prevents storage bloat; enables "right to be forgotten"

**Key Nodes**:
- Schedule Trigger (daily 03:00)
- PostgreSQL SELECT videos in `/videos/temp/` older than `TTL_DAYS_TEMP` (default 14)
- Split In Batches
- SSH to Ubuntu 1: `rm /videos/temp/{video_id}.mp4`
- PostgreSQL DELETE or UPDATE `split='purged'`
- HTTP Request to Media Mover manifest rebuild (remove purged from manifests)
- Emit `privacy.purged` event with count
- Manual Webhook for GDPR deletion requests (video_id specific)

**Audit**: All deletions logged to `audit_log` table with timestamp, reason, operator

---

### Agent 9: Observability/Telemetry Agent
**Purpose**: Aggregate metrics, detect SLA breaches, route alerts

**Benefit**: Provides real-time visibility into system health; prevents outages via proactive alerts

**Key Nodes**:
- **9A Metrics Collector**:
  - Cron (every 30s)
  - HTTP GET `/metrics` from n8n, Media Mover, Gateway (Prometheus format)
  - Code parse Prometheus text → extract `promote_total`, `promote_errors_total`, `queue_depth`, etc.
  - PostgreSQL INSERT to `obs_samples`
- **9B Error→Incident**:
  - Error Trigger (catches any workflow failure)
  - Code extract executionId, workflowId, error message
  - PostgreSQL INSERT to `incidents` table
  - HTTP POST to Slack/Email
- **9C SLO Watchdog**:
  - Cron (every 5 min)
  - PostgreSQL aggregate last 5 min metrics
  - Code evaluate thresholds (error rate < 1%, latency p95 ≤ 2s, queue depth < 100)
  - IF breach: HTTP POST to FastAPI `/pause_promotions`, Slack page
  - Emit `obs.snapshot` event

**Dashboards**: Metrics exported to Prometheus → Grafana for visualization

---

## Event Flow Example: End-to-End Video Processing

```
1. User uploads video via Web UI
   → Streamlit calls FastAPI Gateway
   → Gateway emits webhook to n8n

2. AGENT 1 (Ingest) triggered
   → Validates payload
   → Calls Media Mover /pull
   → Polls until hash + thumbnail ready
   → Inserts to DB (split='temp', label=null)
   → Emits ingest.completed

3. User labels video as "happy" in UI
   → UI calls FastAPI → n8n webhook

4. AGENT 2 (Labeling) triggered
   → Validates JWT
   → Updates label in DB
   → Calls Media Mover /relabel
   → User chooses "Promote to Train"
   → Emits label.completed

5. AGENT 3 (Promotion) triggered  
   → Runs dry-run promotion
   → Posts approval request to Slack
   → User approves
   → Executes atomic move temp → train
   → Updates DB split='train'
   → Calls AGENT 4 to rebuild manifests
   → Emits promotion.completed

6. (After 50/50 balance met) AGENT 5 (Training) auto-triggered
   → Creates MLflow run
   → Launches TAO training
   → Waits for completion
   → Validates Gate A metrics
   → Exports TRT engine
   → Emits training.completed

7. AGENT 6 (Evaluation) triggered
   → Runs inference on test set
   → Validates Gate B metrics
   → Emits evaluation.completed

8. AGENT 7 (Deployment) triggered (if Gate B passed)
   → Deploys to shadow slot
   → Waits for approval
   → Promotes to canary (10% traffic)
   → Monitors metrics for 30 min
   → Full rollout on final approval
   → Emits deployment.completed

Throughout: AGENT 9 (Observability) monitors each step, logs metrics, alerts on failures
Nightly: AGENT 4 (Reconciler) checks for drift, AGENT 8 (Privacy) purges old temp files
```

---

## How Claude + n8n MCP Work Together

### Development Workflow
1. **Claude analyzes** agent requirements from documentation
2. **Claude designs** optimal node graph with proper error handling
3. **Claude queries** n8n MCP for node configurations and examples
4. **Claude generates** complete workflow JSON
5. **MCP validates** workflow structure before deployment
6. **Claude iterates** based on validation feedback

### Runtime Intelligence
- Claude can be invoked within Code nodes for dynamic decision-making
- n8n workflows call Claude API for adaptive behavior (e.g., anomaly detection in Reconciler)
- MCP tools enable workflows to self-modify based on execution patterns

### Continuous Improvement Loop
```
Agent Execution → Metrics to Observability
                ↓
         MCP lists executions
                ↓
         Claude analyzes patterns
                ↓
       Suggests workflow optimizations
                ↓
   MCP applies partial updates
```

---

## Deployment Instructions

### 1. Prerequisites
```bash
# Install n8n
npm install -g n8n

# Set environment variables
export N8N_METRICS=true
export GENERIC_TIMEZONE=America/New_York
export N8N_BASIC_AUTH_ACTIVE=true
export N8N_BASIC_AUTH_USER=admin
export N8N_BASIC_AUTH_PASSWORD=<secure_password>
```

### 2. Import Workflows
```bash
# From n8n UI: Settings → Import from File
# Or via CLI:
n8n import:workflow --input=/path/to/01_ingest_agent.json
n8n import:workflow --input=/path/to/02_labeling_agent.json
# ... repeat for all 9 agents
```

### 3. Configure Credentials
- PostgreSQL connection to `reachy_local` database
- SSH key for Ubuntu 1 (rusty_admin@10.0.4.130)
- JWT signing keys for webhook authentication
- Slack/Email for notifications
- HTTP Basic Auth for Media Mover API

### 4. Activate Workflows
```bash
# Via UI or:
n8n workflow:activate --id=<workflow_id>
```

### 5. Test Webhooks
```bash
# Test Ingest Agent
curl -X POST http://localhost:5678/webhook/video_gen_hook \
  -H "X-INGEST-KEY: <token>" \
  -H "Content-Type: application/json" \
  -d '{"source_url": "https://example.com/test.mp4", "label": "happy"}'
```

---

## Security Considerations

1. **Authentication**:
   - All webhooks use JWT or header tokens
   - n8n UI protected with basic auth
   - Media Mover requires Bearer tokens

2. **Privacy**:
   - No raw video data passes through n8n
   - Only file paths and metadata handled
   - Labeling Agent respects test set unlabeled constraint

3. **Idempotency**:
   - All mutating operations use SHA256-based idempotency keys
   - Database constraints prevent duplicate writes
   - Promotion dry-runs protect against accidental moves

4. **Audit Trail**:
   - Every operation logs correlation_id
   - Observability Agent tracks all executions
   - PostgreSQL audit tables maintain full history

---

## Monitoring & Operations

### Healthchecks
```bash
# Check n8n
curl http://localhost:5678/healthz

# Check workflows active
n8n workflow:list --active=true

# View recent executions
curl http://localhost:5678/api/v1/executions?limit=10
```

### Metrics (Prometheus format)
- `n8n_active_executions`: Currently running workflows
- `n8n_workflow_errors_total`: Failed executions
- `media_mover_promote_total`: Promotion attempts
- `media_mover_promote_errors_total`: Promotion failures
- `gateway_ws_active`: Active WebSocket connections
- `gateway_queue_depth`: Pending events

### Troubleshooting
- **Agent not triggering**: Check webhook URL, auth token, n8n logs
- **Workflow stuck**: Check Wait node timeouts, Media Mover availability
- **Metrics missing**: Verify `N8N_METRICS=true`, Prometheus scraping config
- **Idempotency conflicts**: Check DB `label_event` table for duplicate keys

---

## Future Enhancements

1. **Advanced AI Integration**:
   - Code nodes calling Claude API for adaptive thresholds
   - Anomaly detection in Reconciler Agent
   - Automated workflow optimization

2. **Distributed Tracing**:
   - OpenTelemetry export from n8n
   - Jaeger UI for end-to-end trace visualization

3. **Multi-Tenancy**:
   - Per-user workflows with isolated credentials
   - Row-level security in PostgreSQL

4. **Workflow Versioning**:
   - Git-based workflow storage
   - CI/CD pipeline for workflow deployments
   - A/B testing for workflow changes

---

## References

- **Project Requirements**: `/memory-bank/requirements_08.4.2.md`
- **Agent Specifications**: `/AGENTS_08.4.2.md`
- **Implementation Guide**: `/docs/gpt/Implementation_Phase4_Orchestration_Opus_4.1.md`
- **n8n Documentation**: https://docs.n8n.io
- **n8n MCP Tools**: Use `mcp0_tools_documentation` for complete reference
- **Claude Sonnet 4.5**: Anthropic's advanced reasoning model

---

**Version**: 1.0.0  
**Last Updated**: 2025-11-07  
**Maintainer**: Russell Bray (rustybee255@gmail.com)
